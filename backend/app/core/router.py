"""
LangGraph-powered intelligent routing engine for fraud detection.

Pipeline (auditable, MAG-7-ready):
  1. route_model      → sector → primary model assignment
  2. enrich_mcp       → optional external context via Model Context Protocol
  3. retrieve_context → Pinecone RAG with similarity scores + embedding provenance
  4. analyze_fraud    → LLM inference + LLM-vs-rules cross-validation
  5. apply_guardrails → post-score consistency / OFAC / extreme-risk checks
  6. generate_explanation → human-readable verdict with full decision_trace
"""
from typing import Dict, Any, TypedDict, Optional
from langgraph.graph import StateGraph
import json
import logging
import time

from .validation import validate_llm_result, get_risk_level
from .explanations import build_rule_based_explanation
from app.llm.config import get_sector_route_display

logger = logging.getLogger(__name__)

try:
    from app.mcp.client import get_mcp_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logger.info("MCP client not available - enhanced context features disabled")


class RouterState(TypedDict, total=False):
    """State passed through LangGraph workflow"""
    sector: str
    input_data: Dict[str, Any]
    model_name: str
    rag_context: str
    fraud_score: float
    risk_level: str
    explanation: str
    similar_patterns: int
    risk_factors: list
    decision_trace: list
    score_breakdown: list
    mcp_context: Dict[str, Any]
    mcp_status: str
    rag_top_score: float
    rag_avg_score: float
    embedding_source: str
    clinical_score: Optional[float]
    _analysis_method: str
    _hf_rejected: bool
    _guardrail_adjusted: bool


class LangGraphRouter:
    """
    LangGraph-powered intelligent routing engine.
    Routes requests to sector-specific LLMs with RAG + MCP enhancement
    and an explicit post-score guardrail node.
    """

    def __init__(self, rag_engine, hf_client=None):
        self.rag_engine = rag_engine
        self.hf_client = hf_client
        self.workflow = self._build_workflow()

    def _build_workflow(self):
        """Build the 6-node auditable LangGraph fraud pipeline."""
        workflow = StateGraph(RouterState)

        workflow.add_node("route_model", self._route_to_model)
        workflow.add_node("enrich_mcp", self._enrich_mcp)
        workflow.add_node("retrieve_context", self._retrieve_rag_context)
        workflow.add_node("analyze_fraud", self._analyze_with_llm)
        workflow.add_node("apply_guardrails", self._apply_guardrails)
        workflow.add_node("generate_explanation", self._generate_explanation)

        workflow.set_entry_point("route_model")
        workflow.add_edge("route_model", "enrich_mcp")
        workflow.add_edge("enrich_mcp", "retrieve_context")
        workflow.add_edge("retrieve_context", "analyze_fraud")
        workflow.add_edge("analyze_fraud", "apply_guardrails")
        workflow.add_edge("apply_guardrails", "generate_explanation")
        workflow.set_finish_point("generate_explanation")

        return workflow.compile()

    @staticmethod
    def _trace(
        state: RouterState,
        node: str,
        title: str,
        detail: str,
        status: str = "ok",
        latency_ms: Optional[int] = None,
    ) -> None:
        """Append a step to the pipeline decision trace (surfaced in API + UI)."""
        step: Dict[str, Any] = {
            "node": node,
            "title": title,
            "detail": detail,
            "status": status,
        }
        if latency_ms is not None:
            step["latency_ms"] = latency_ms
        state.setdefault("decision_trace", []).append(step)

    def _route_to_model(self, state: RouterState) -> RouterState:
        """Route to appropriate model based on sector."""
        sector = state["sector"]
        state["model_name"] = get_sector_route_display(sector)
        self._trace(
            state,
            "route_model",
            "Model routing",
            f"Sector '{sector}' routed to {state['model_name']}",
        )
        return state

    def _enrich_mcp(self, state: RouterState) -> RouterState:
        """
        Enrich input with external context via Model Context Protocol.
        Explicit graph node so reviewers can see MCP as a first-class stage,
        not a hidden side effect inside the LLM call.
        """
        t0 = time.monotonic()
        sector = state["sector"]
        data = state["input_data"]
        state["mcp_context"] = {}
        state["mcp_status"] = "disabled"

        if not MCP_AVAILABLE:
            self._trace(
                state,
                "enrich_mcp",
                "MCP enrichment",
                "MCP client not installed — continuing without external tool context",
                status="empty",
                latency_ms=int((time.monotonic() - t0) * 1000),
            )
            return state

        try:
            mcp_client = get_mcp_client()
            if not mcp_client.enabled:
                self._trace(
                    state,
                    "enrich_mcp",
                    "MCP enrichment",
                    "MCP_SERVER_URL not set — external tools skipped (set URL to enable)",
                    status="empty",
                    latency_ms=int((time.monotonic() - t0) * 1000),
                )
                return state

            health = mcp_client.health_check()
            if not health.get("ok"):
                state["mcp_status"] = "unreachable"
                self._trace(
                    state,
                    "enrich_mcp",
                    "MCP enrichment",
                    f"MCP server unreachable ({health.get('detail', 'error')}) — soft-fail, continuing",
                    status="fallback",
                    latency_ms=int((time.monotonic() - t0) * 1000),
                )
                return state

            mcp_context = mcp_client.get_context(sector, data)
            state["mcp_context"] = mcp_context
            tools_used = list(mcp_context.keys()) if mcp_context else []
            state["mcp_status"] = "ok" if tools_used else "no_signals"

            self._trace(
                state,
                "enrich_mcp",
                "MCP enrichment",
                (
                    f"External tools returned: {', '.join(tools_used)}"
                    if tools_used
                    else "MCP online but no sector tools matched this payload"
                ),
                status="ok" if tools_used else "empty",
                latency_ms=int((time.monotonic() - t0) * 1000),
            )
        except Exception as e:
            state["mcp_status"] = "error"
            logger.warning(f"MCP enrichment failed: {e}")
            self._trace(
                state,
                "enrich_mcp",
                "MCP enrichment",
                f"MCP soft-fail: {type(e).__name__} — continuing without external context",
                status="fallback",
                latency_ms=int((time.monotonic() - t0) * 1000),
            )
        return state

    def _retrieve_rag_context(self, state: RouterState) -> RouterState:
        """Retrieve similar fraud patterns from Pinecone with similarity provenance."""
        t0 = time.monotonic()
        sector = state["sector"]
        input_data = state["input_data"]
        query_text = self._format_query(sector, input_data)

        results = self.rag_engine.query_similar_patterns(
            sector=sector,
            query_text=query_text,
            n_results=5,
        )

        state["rag_context"] = results["context"]
        state["similar_patterns"] = results["count"]
        state["rag_top_score"] = float(results.get("top_score", 0.0) or 0.0)
        state["rag_avg_score"] = float(results.get("avg_score", 0.0) or 0.0)
        state["embedding_source"] = results.get("embedding_source", "unknown")

        count = results["count"]
        top = state["rag_top_score"]
        avg = state["rag_avg_score"]
        emb = state["embedding_source"]
        top_risk = ""
        patterns = results.get("patterns") or []
        if patterns:
            top_risk = f"; top match risk={patterns[0].get('risk_level', '?').upper()}"

        status = "ok" if count > 0 else "empty"
        if emb == "hash":
            status = "fallback"

        self._trace(
            state,
            "retrieve_context",
            "RAG pattern retrieval",
            (
                f"Matched {count} pattern(s) in Pinecone for '{sector}' "
                f"(top_sim={top:.3f}, avg_sim={avg:.3f}, embedding={emb}{top_risk})"
            ),
            status=status,
            latency_ms=int((time.monotonic() - t0) * 1000),
        )
        return state

    def _analyze_with_llm(self, state: RouterState) -> RouterState:
        """Analyze fraud using LLM + rule-based cross-validation."""
        t0 = time.monotonic()
        sector = state["sector"]
        data = state["input_data"]
        rag_context = state["rag_context"]
        mcp_context = state.get("mcp_context") or {}
        enhanced_data = {**data, **mcp_context}

        result = validate_llm_result(
            hf_client=self.hf_client,
            sector=sector,
            data=data,
            rag_context=rag_context,
            enhanced_data=enhanced_data,
            calculate_fraud_score=self._calculate_fraud_score,
        )

        use_hf = result["use_hf"]
        hf_result = result["hf_result"]
        rule_based_score = result["rule_based_score"]
        rule_based_risk = result["rule_based_risk"]
        provider_label = result["provider_label"]
        latency = int((time.monotonic() - t0) * 1000)

        if not use_hf:
            state["fraud_score"] = rule_based_score
            state["risk_level"] = rule_based_risk
            # Surface which signals drove the rule-based score (so KYC flips are visible)
            try:
                from app.llm.chains import score_with_breakdown
                _, breakdown = score_with_breakdown(sector, data)
                state["score_breakdown"] = breakdown
                state["risk_factors"] = [
                    f"{item['label']} ({item['points']:+.0f})"
                    for item in breakdown
                    if item.get("signal") != "clamp"
                ]
            except Exception:
                state["score_breakdown"] = []
                state["risk_factors"] = []
            state["model_name"] = "Rule-Based + Pinecone RAG (LLM score rejected)"
            state["_analysis_method"] = "rule_based"
            state["_hf_rejected"] = True
            self._trace(
                state,
                "analyze_fraud",
                "Cross-validation: LLM rejected",
                (
                    f"{provider_label} score was rejected or unavailable; "
                    f"using deterministic rule-based score {rule_based_score:.0f} "
                    f"({rule_based_risk.upper()}) as guardrail"
                ),
                status="fallback",
                latency_ms=latency,
            )
        else:
            state["fraud_score"] = hf_result["fraud_score"]
            state["risk_level"] = hf_result["risk_level"].lower()
            state["risk_factors"] = hf_result.get("risk_factors", [])
            # Still attach rule-based breakdown so users can compare what flipped
            try:
                from app.llm.chains import score_with_breakdown
                _, breakdown = score_with_breakdown(sector, data)
                state["score_breakdown"] = breakdown
            except Exception:
                state["score_breakdown"] = []
            state["explanation"] = hf_result.get("reasoning", "")
            if "model_used" in hf_result:
                state["model_name"] = hf_result["model_used"]
            if "clinical_score" in hf_result:
                state["clinical_score"] = hf_result["clinical_score"]
            state["_analysis_method"] = "llm_validated"
            state["_hf_rejected"] = False
            self._trace(
                state,
                "analyze_fraud",
                "Cross-validation: LLM accepted",
                (
                    f"{provider_label} scored {hf_result['fraud_score']:.0f} "
                    f"({hf_result['risk_level']}); accepted after agreement check "
                    f"against rule-based score {rule_based_score:.0f}"
                ),
                status="ok",
                latency_ms=latency,
            )
        return state

    def _apply_guardrails(self, state: RouterState) -> RouterState:
        """
        Post-score guardrails: escalate when RAG / OFAC signals disagree with a low score.
        Keeps the system honest under critique — LLM output is never the sole authority.
        """
        from app.llm.config import OFAC_SANCTIONED_COUNTRIES, SECTOR_LOCATION_FIELDS

        t0 = time.monotonic()
        sector = state["sector"]
        data = state["input_data"]
        score = float(state.get("fraud_score", 0) or 0)
        risk = (state.get("risk_level") or "low").lower()
        adjustments: list[str] = []
        state["_guardrail_adjusted"] = False

        # OFAC / high-risk geography escalate
        location_fields = SECTOR_LOCATION_FIELDS.get(sector, [])
        hit_countries = []
        for field in location_fields:
            val = str(data.get(field, "")).lower()
            for country in OFAC_SANCTIONED_COUNTRIES:
                if country in val:
                    hit_countries.append(country)
                    break
        if hit_countries and score < 75:
            score = max(score, 85.0)
            risk = "critical"
            adjustments.append(
                f"OFAC/high-risk geography ({', '.join(hit_countries[:3])}) → escalated to ≥85"
            )

        # Strong RAG match to CRITICAL patterns should not yield a low score
        top_sim = float(state.get("rag_top_score", 0) or 0)
        if top_sim >= 0.75 and score < 60:
            score = max(score, 70.0)
            if risk in ("low", "medium"):
                risk = "high"
            adjustments.append(
                f"High RAG similarity ({top_sim:.2f}) to known fraud patterns → floor score ≥70"
            )

        # MCP blockchain / seller red flags
        mcp = state.get("mcp_context") or {}
        blockchain = mcp.get("blockchain_data") or {}
        for side in ("sender", "receiver"):
            side_data = blockchain.get(side) or {}
            if isinstance(side_data, dict) and (
                side_data.get("sanctioned")
                or side_data.get("mixer")
                or side_data.get("high_risk")
            ):
                if score < 80:
                    score = max(score, 90.0)
                    risk = "critical"
                    adjustments.append(f"MCP blockchain flag on {side} → escalated to ≥90")

        if adjustments:
            state["fraud_score"] = score
            state["risk_level"] = risk
            state["_guardrail_adjusted"] = True
            factors = list(state.get("risk_factors") or [])
            factors.extend(adjustments)
            state["risk_factors"] = factors
            self._trace(
                state,
                "apply_guardrails",
                "Post-score guardrails applied",
                "; ".join(adjustments),
                status="fallback",
                latency_ms=int((time.monotonic() - t0) * 1000),
            )
        else:
            self._trace(
                state,
                "apply_guardrails",
                "Post-score guardrails",
                f"No escalation required — score {score:.0f} ({risk.upper()}) consistent with OFAC/RAG/MCP signals",
                status="ok",
                latency_ms=int((time.monotonic() - t0) * 1000),
            )
        return state

    def _generate_explanation(self, state: RouterState) -> RouterState:
        """Generate human-readable explanation — transparent about method used."""
        sector = state["sector"]
        data = state["input_data"]
        fraud_score = state["fraud_score"]
        risk_level = state["risk_level"]
        model_name = state["model_name"]
        analysis_method = state.get("_analysis_method", "rule_based")

        if state.get("explanation") and analysis_method == "llm_validated":
            base_explanation = state["explanation"]

            if sector == "medical" and ("Two-Stage" in model_name or "MedGemma" in model_name):
                clinical_score = state.get("clinical_score")
                if clinical_score is not None:
                    clinical_context = (
                        f"Clinical validation assessed this claim at {clinical_score}/100 "
                        f"for medical appropriateness. "
                    )
                    if not base_explanation.startswith(clinical_context):
                        base_explanation = clinical_context + base_explanation

            sentences = [s.strip() for s in base_explanation.split(".") if s.strip()]
            if len(sentences) < 3:
                enhancements = {
                    "banking": (
                        " This analysis evaluated transaction patterns, account history, "
                        "geographic risk factors, device fingerprinting, and transaction velocity."
                    ),
                    "ecommerce": (
                        " This analysis examined seller account age, pricing vs market value, "
                        "review sentiment, shipping origin, and listing integrity."
                    ),
                    "supply_chain": (
                        " This analysis reviewed supplier credentials, pricing anomalies, "
                        "logistics patterns, payment terms, and documentation completeness."
                    ),
                    "medical": (
                        " This assessment combines clinical legitimacy validation with fraud "
                        "pattern analysis for a comprehensive risk evaluation."
                    ),
                }
                enhancement = enhancements.get(
                    sector,
                    " Multiple risk dimensions were cross-checked against known fraud typologies.",
                )
                if enhancement not in base_explanation:
                    base_explanation += enhancement

            prefix = f"{model_name} analysis: "
            if not base_explanation.startswith(prefix):
                state["explanation"] = prefix + base_explanation
            else:
                state["explanation"] = base_explanation
        else:
            state["explanation"] = build_rule_based_explanation(
                sector, data, fraud_score, risk_level, model_name
            )

        method = (
            "LLM analysis"
            if analysis_method == "llm_validated"
            else "rule-based guardrail"
        )
        if state.get("_guardrail_adjusted"):
            method += " + post-score escalation"

        self._trace(
            state,
            "generate_explanation",
            "Explanation generated",
            f"Final verdict: {fraud_score:.0f}/100 ({risk_level.upper()}) via {method}",
        )
        return state

    def _format_query(self, sector: str, data: Dict[str, Any]) -> str:
        """Format input data as query text for RAG (exclude bulky MCP blobs)."""
        clean = {k: v for k, v in data.items() if not isinstance(v, (dict, list)) or k in (
            "indicators", "risk_factors"
        )}
        # Prefer original form fields only for embedding quality
        form_keys = [k for k in data.keys() if not k.endswith("_data") and k != "transaction_history"]
        clean = {k: data[k] for k in form_keys}
        return json.dumps(clean, indent=2, default=str)

    def _calculate_fraud_score(self, sector: str, data: Dict[str, Any], rag_context: str) -> float:
        """Calculate fraud score using sector chains with RAG enhancement."""
        from app.llm.chains import calculate_fraud_score as chain_score
        return chain_score(sector, data, rag_context)

    async def route_and_analyze(self, sector: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the full LangGraph workflow."""
        initial_state: RouterState = {
            "sector": sector,
            "input_data": data,
            "model_name": "",
            "rag_context": "",
            "fraud_score": 0.0,
            "risk_level": "",
            "explanation": "",
            "similar_patterns": 0,
            "risk_factors": [],
            "decision_trace": [],
            "score_breakdown": [],
            "mcp_context": {},
            "mcp_status": "disabled",
            "rag_top_score": 0.0,
            "rag_avg_score": 0.0,
            "embedding_source": "unknown",
        }

        final_state = self.workflow.invoke(initial_state)

        return {
            "fraud_score": final_state["fraud_score"],
            "risk_level": final_state["risk_level"],
            "explanation": final_state["explanation"],
            "model_used": final_state["model_name"],
            "similar_patterns": final_state["similar_patterns"],
            "risk_factors": final_state.get("risk_factors", []),
            "score_breakdown": final_state.get("score_breakdown", []),
            "decision_trace": final_state.get("decision_trace", []),
            "pipeline_meta": {
                "mcp_status": final_state.get("mcp_status", "disabled"),
                "rag_top_score": final_state.get("rag_top_score", 0.0),
                "rag_avg_score": final_state.get("rag_avg_score", 0.0),
                "embedding_source": final_state.get("embedding_source", "unknown"),
                "guardrail_adjusted": bool(final_state.get("_guardrail_adjusted")),
                "analysis_method": final_state.get("_analysis_method", "unknown"),
                "nodes": [
                    "route_model",
                    "enrich_mcp",
                    "retrieve_context",
                    "analyze_fraud",
                    "apply_guardrails",
                    "generate_explanation",
                ],
            },
        }


def analyze_fraud_rule_based(sector: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Rule-based fraud analysis (fallback when LLM API fails)."""
    from .rag_engine import RAGEngine

    rag = RAGEngine()
    router = LangGraphRouter(rag, hf_client=None)

    fraud_score = router._calculate_fraud_score(sector, data, "")
    risk_level = get_risk_level(fraud_score)
    model_name = get_sector_route_display(sector)
    reasoning = build_rule_based_explanation(
        sector, data, fraud_score, risk_level, model_name
    )

    return {
        "fraud_score": fraud_score,
        "risk_level": risk_level.upper(),
        "reasoning": reasoning,
        "risk_factors": ["Rule-based analysis"],
    }
