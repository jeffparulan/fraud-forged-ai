"""
LLM vs rule-based validation logic.
Decides when to trust LLM scores vs fallback to rule-based scoring.
"""
import logging
from typing import Dict, Any, Optional, Callable

logger = logging.getLogger(__name__)


def get_risk_level(score: float) -> str:
    """Convert fraud score to risk level with consistent thresholds."""
    if score >= 85:
        return "critical"
    elif score >= 60:
        return "high"
    elif score >= 30:
        return "medium"
    return "low"


def validate_llm_result(
    *,
    hf_client,
    sector: str,
    data: Dict[str, Any],
    rag_context: str,
    enhanced_data: Dict[str, Any],
    calculate_fraud_score: Callable[[str, Dict, str], float],
) -> Dict[str, Any]:
    """
    Validate LLM result against rule-based score. Returns decision dict:
    - use_hf: bool
    - hf_result: dict | None (when use_hf)
    - rule_based_score: float
    - rule_based_risk: str
    - provider_label: str
    - decision_reason: "accepted" | "unavailable" | "rejected" | "no_client" | "error"
    """
    rule_based_score = calculate_fraud_score(sector, data, rag_context)
    rule_based_risk = get_risk_level(rule_based_score)
    logger.info(f"[Scoring] Rule-based score: {rule_based_score:.2f} ({rule_based_risk.upper()})")

    use_hf = False
    hf_result: Optional[Dict[str, Any]] = None
    provider_label = "LLM"
    decision_reason = "unavailable"

    if not hf_client:
        return {
            "use_hf": False,
            "hf_result": None,
            "rule_based_score": rule_based_score,
            "rule_based_risk": rule_based_risk,
            "provider_label": "LLM",
            "decision_reason": "no_client",
        }

    try:
        from app.llm.config import SECTOR_MODELS

        sector_config = SECTOR_MODELS.get(sector, {})
        # Two-stage sectors (medical) have no "primary" key; use stage1 for display.
        if sector_config.get("two_stage"):
            primary_cfg = sector_config.get("stage1", {})
        else:
            primary_cfg = sector_config.get("primary", {})
        primary_provider = primary_cfg.get("provider", "unknown")
        primary_model = primary_cfg.get("model", "unknown")
        provider_label = primary_provider.upper() if primary_provider != "hf" else "HF"

        logger.info(f"[LLM] Attempting {provider_label} inference for {sector} (model: {primary_model})")
        hf_result = hf_client.analyze_fraud(sector, enhanced_data, rag_context=rag_context)
        if not hf_result or hf_result.get("score_parsed") is False:
            logger.warning(
                f"[LLM] {provider_label} returned no usable score — using rule-based"
            )
            return {
                "use_hf": False,
                "hf_result": hf_result,
                "rule_based_score": rule_based_score,
                "rule_based_risk": rule_based_risk,
                "provider_label": provider_label,
                "decision_reason": "unavailable",
            }

        hf_score = hf_result["fraud_score"]
        hf_risk = hf_result.get("risk_level", "").lower()

        logger.info(
            f"[LLM] {provider_label} score: {hf_score:.2f} ({hf_risk.upper()}), "
            f"Rule-based: {rule_based_score:.2f} ({rule_based_risk.upper()})"
        )

        score_diff = abs(hf_score - rule_based_score)
        is_medical = sector == "medical"

        # Validation philosophy:
        # - Trust the LLM when both systems land in the same risk neighbourhood.
        # - Reject when there is a clear cross-risk-level reversal that almost always
        #   means the score was extracted incorrectly (e.g. parser grabbed a "22% price
        #   variance" instead of the actual fraud score) OR the model is hallucinating.
        # - Do NOT use a tight fixed-point threshold (e.g. diff > 20) — that throws
        #   away valid LLM nuance. Use risk-level crossings instead.
        if is_medical:
            # Medical two-stage: same risk-level crossing logic as non-medical, but
            # slightly more lenient on the upper bound because Stage 1 (clinical) +
            # Stage 2 (fraud) sometimes legitimately downgrade an alarming-looking
            # rule-based score (e.g. complex but legitimate surgery).
            #
            # 1. Rule-based CRITICAL (>=85) + LLM not even HIGH (<60)
            #    → Almost always means Stage 2 hit a parser default of 50 because
            #      its JSON output didn't match. Trust rule-based.
            # 2. Rule-based HIGH/CRITICAL (>=70) + LLM LOW (<35)
            #    → Cross-level reversal. Trust rule-based.
            # 3. Rule-based VERY LOW (<=15) + LLM CRITICAL (>=85)
            #    → Possible hallucination. Trust rule-based.
            if rule_based_score >= 85 and hf_score < 60:
                logger.warning(
                    f"[Validation] ❌ REJECTED {provider_label} (Medical): Rule-based CRITICAL "
                    f"({rule_based_score:.2f}) vs {provider_label} below HIGH ({hf_score:.2f}) — "
                    "likely Stage 2 parse failure (default 50), using rule-based"
                )
                use_hf = False
                decision_reason = "rejected"
            elif rule_based_score >= 70 and hf_score < 35:
                logger.warning(
                    f"[Validation] ❌ REJECTED {provider_label} (Medical): Rule-based HIGH/CRITICAL "
                    f"({rule_based_score:.2f}) vs {provider_label} LOW ({hf_score:.2f}) — "
                    "likely parse failure, using rule-based"
                )
                use_hf = False
                decision_reason = "rejected"
            elif rule_based_score <= 15 and hf_score >= 85:
                logger.warning(
                    f"[Validation] ❌ REJECTED {provider_label} (Medical): Rule-based VERY LOW "
                    f"({rule_based_score:.2f}) vs {provider_label} CRITICAL ({hf_score:.2f}) — "
                    "possible hallucination, using rule-based"
                )
                use_hf = False
                decision_reason = "rejected"
            else:
                use_hf = True
                decision_reason = "accepted"
                logger.info(
                    f"[Validation] ✅ ACCEPTED {provider_label} (Medical): two-stage score "
                    f"{hf_score:.2f} ({hf_risk.upper()}), rule-based baseline {rule_based_score:.2f} "
                    f"({rule_based_risk.upper()})"
                )
        else:
            # Non-medical: reject on cross-risk-level reversals.
            #
            # Rejection rules are based on risk-level crossings, not a fixed diff:
            #
            # 1. Rule-based CRITICAL (>=85) + LLM not even HIGH (<60)
            #    → Almost certainly a parsing failure or model calibration issue.
            #      When every heuristic flag fires (new supplier, missing docs, huge
            #      amount, quality issues), the LLM must at least reach HIGH (60+).
            #
            # 2. Rule-based HIGH/CRITICAL (>=70) + LLM MEDIUM or LOW (<40)
            #    → Significant cross-level reversal. Trust rule-based.
            #
            # 3. Rule-based very low (<=15) + LLM CRITICAL (>=85)
            #    → Possible hallucination. Trust rule-based.
            if rule_based_score >= 85 and hf_score < 60:
                logger.warning(
                    f"[Validation] ❌ REJECTED {provider_label}: Rule-based CRITICAL "
                    f"({rule_based_score:.2f}) vs {provider_label} below HIGH ({hf_score:.2f}) — "
                    "likely parse failure or miscalibration, using rule-based"
                )
                use_hf = False
                decision_reason = "rejected"
            elif rule_based_score >= 70 and hf_score < 40:
                logger.warning(
                    f"[Validation] ❌ REJECTED {provider_label}: Rule-based HIGH/CRITICAL "
                    f"({rule_based_score:.2f}) vs {provider_label} LOW ({hf_score:.2f}) — "
                    "likely parse failure, using rule-based"
                )
                use_hf = False
                decision_reason = "rejected"
            elif rule_based_score <= 15 and hf_score >= 85:
                logger.warning(
                    f"[Validation] ❌ REJECTED {provider_label}: Rule-based VERY LOW "
                    f"({rule_based_score:.2f}) vs {provider_label} CRITICAL ({hf_score:.2f}) — "
                    "possible hallucination"
                )
                use_hf = False
                decision_reason = "rejected"
            else:
                use_hf = True
                decision_reason = "accepted"
                logger.info(
                    f"[Validation] ✅ ACCEPTED {provider_label}: LLM score {hf_score:.2f} "
                    f"({hf_risk.upper()}), rule-based baseline {rule_based_score:.2f} "
                    f"({rule_based_risk.upper()}), diff {score_diff:.2f} pts"
                )

    except Exception as e:
        logger.error(f"[LLM] {provider_label} inference failed: {e}, using rule-based")
        use_hf = False
        decision_reason = "error"

    return {
        "use_hf": use_hf,
        "hf_result": hf_result,
        "rule_based_score": rule_based_score,
        "rule_based_risk": rule_based_risk,
        "provider_label": provider_label,
        "decision_reason": decision_reason,
    }
