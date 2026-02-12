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
    """
    rule_based_score = calculate_fraud_score(sector, data, rag_context)
    rule_based_risk = get_risk_level(rule_based_score)
    logger.info(f"[Scoring] Rule-based score: {rule_based_score:.2f} ({rule_based_risk.upper()})")

    use_hf = False
    hf_result: Optional[Dict[str, Any]] = None
    provider_label = "LLM"

    if not hf_client:
        return {
            "use_hf": False,
            "hf_result": None,
            "rule_based_score": rule_based_score,
            "rule_based_risk": rule_based_risk,
            "provider_label": "LLM",
        }

    try:
        from app.llm.config import SECTOR_MODELS

        sector_config = SECTOR_MODELS.get(sector, {})
        primary_provider = sector_config.get("primary", {}).get("provider", "unknown")
        primary_model = sector_config.get("primary", {}).get("model", "unknown")
        provider_label = primary_provider.upper() if primary_provider != "hf" else "HF"

        logger.info(f"[LLM] Attempting {provider_label} inference for {sector} (model: {primary_model})")
        hf_result = hf_client.analyze_fraud(sector, enhanced_data, rag_context=rag_context)
        hf_score = hf_result["fraud_score"]
        hf_risk = hf_result.get("risk_level", "").lower()

        logger.info(
            f"[LLM] {provider_label} score: {hf_score:.2f} ({hf_risk.upper()}), "
            f"Rule-based: {rule_based_score:.2f} ({rule_based_risk.upper()})"
        )

        score_diff = abs(hf_score - rule_based_score)
        is_medical = sector == "medical"

        if is_medical:
            if rule_based_score > 75 and hf_score < 25:
                logger.warning(
                    f"[Validation] ❌ REJECTED {provider_label} (Medical): Rule-based CRITICAL "
                    f"({rule_based_score:.2f}) vs {provider_label} LOW ({hf_score:.2f})"
                )
                use_hf = False
            else:
                use_hf = True
                logger.info(
                    f"[Validation] ✅ ACCEPTED {provider_label} (Medical): Trusting two-stage "
                    f"pipeline ({hf_score:.2f}) over rule-based ({rule_based_score:.2f})"
                )
        else:
            # Non-medical: apply validation rules
            if rule_based_score < 10 and hf_score > 85:
                logger.warning(
                    f"[Validation] ❌ REJECTED {provider_label}: Rule-based VERY LOW "
                    f"({rule_based_score:.2f}) vs {provider_label} CRITICAL ({hf_score:.2f})"
                )
                use_hf = False
            elif rule_based_score > 60 and hf_score < 30:
                logger.warning(
                    f"[Validation] ❌ REJECTED {provider_label}: Rule-based HIGH "
                    f"({rule_based_score:.2f}) vs {provider_label} LOW ({hf_score:.2f})"
                )
                use_hf = False
            elif rule_based_score < 10:
                use_hf = True
                logger.info(
                    f"[Validation] ✅ ACCEPTED {provider_label}: Both scores low "
                    f"({rule_based_score:.2f} vs {hf_score:.2f})"
                )
            elif rule_based_score < 30:
                if score_diff > 40:
                    logger.warning(
                        f"[Validation] ❌ REJECTED {provider_label}: Extreme discrepancy "
                        f"({score_diff:.2f} points) when rule-based is LOW"
                    )
                    use_hf = False
                else:
                    use_hf = True
                    logger.info(
                        f"[Validation] ✅ ACCEPTED {provider_label}: Discrepancy ({score_diff:.2f} points) "
                        "within tolerance"
                    )
            elif score_diff > 20:
                logger.warning(
                    f"[Validation] ❌ REJECTED {provider_label}: Large discrepancy "
                    f"({score_diff:.2f} points). Using rule-based."
                )
                use_hf = False
            elif score_diff > 15 and rule_based_risk != hf_risk:
                logger.warning(
                    f"[Validation] ❌ REJECTED {provider_label}: Risk level mismatch "
                    f"({rule_based_risk} vs {hf_risk}) with {score_diff:.2f} point difference"
                )
                use_hf = False
            else:
                use_hf = True
                logger.info(
                    f"[Validation] ✅ ACCEPTED {provider_label}: Scores close "
                    f"({score_diff:.2f} points), risk levels: {rule_based_risk} vs {hf_risk}"
                )

    except Exception as e:
        logger.error(f"[LLM] {provider_label} inference failed: {e}, using rule-based")
        use_hf = False

    return {
        "use_hf": use_hf,
        "hf_result": hf_result,
        "rule_based_score": rule_based_score,
        "rule_based_risk": rule_based_risk,
        "provider_label": provider_label,
    }
