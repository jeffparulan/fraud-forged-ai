"""
LangGraph-powered intelligent routing engine for fraud detection.
Routes requests to sector-specific LLMs with RAG enhancement.
"""
from typing import Dict, Any, TypedDict
from langgraph.graph import Graph, StateGraph
import json
import logging

from .validation import validate_llm_result, get_risk_level
from .explanations import build_rule_based_explanation

logger = logging.getLogger(__name__)

# Optional MCP integration for enhanced context
try:
    from app.mcp.client import get_mcp_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logger.info("MCP client not available - enhanced context features disabled")


class RouterState(TypedDict):
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


class LangGraphRouter:
    """
    LangGraph-powered intelligent routing engine.
    Routes requests to sector-specific LLMs with RAG enhancement.
    """
    
    def __init__(self, rag_engine, hf_client=None):
        self.rag_engine = rag_engine
        self.hf_client = hf_client
        # Cost-optimized model alignment (HF Pro + OpenRouter FREE)
        self.model_mapping = {
            "banking": "Qwen2.5-72B-Instruct (HF Pro)",
            "medical": "Two-Stage: MedGemma-4B-IT → Qwen2.5-32B (HF Inference API)",
            "ecommerce": "Nemotron-2 (12B VL) (FREE)",
            "supply_chain": "Nemotron-2 (12B VL) (FREE)"
        }
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> Graph:
        """Build LangGraph workflow for fraud detection - RAG FIRST for context, then HF/fallback"""
        
        workflow = StateGraph(RouterState)
        
        workflow.add_node("route_model", self._route_to_model)
        workflow.add_node("retrieve_context", self._retrieve_rag_context)
        workflow.add_node("analyze_fraud", self._analyze_with_llm)
        workflow.add_node("generate_explanation", self._generate_explanation)
        
        workflow.set_entry_point("route_model")
        workflow.add_edge("route_model", "retrieve_context")
        workflow.add_edge("retrieve_context", "analyze_fraud")
        workflow.add_edge("analyze_fraud", "generate_explanation")
        workflow.set_finish_point("generate_explanation")
        
        return workflow.compile()
    
    def _route_to_model(self, state: RouterState) -> RouterState:
        """Route to appropriate model based on sector"""
        sector = state["sector"]
        state["model_name"] = self.model_mapping.get(sector, "Nemotron-3-Nano-30B (fallback)")
        return state
    
    def _retrieve_rag_context(self, state: RouterState) -> RouterState:
        """Retrieve similar fraud patterns from Pinecone"""
        sector = state["sector"]
        input_data = state["input_data"]
        
        query_text = self._format_query(sector, input_data)
        
        results = self.rag_engine.query_similar_patterns(
            sector=sector,
            query_text=query_text,
            n_results=5
        )
        
        state["rag_context"] = results["context"]
        state["similar_patterns"] = results["count"]
        
        return state
    
    def _analyze_with_llm(self, state: RouterState) -> RouterState:
        """
        Analyze fraud using LLM if available and validated,
        otherwise fall back to rule-based scoring.
        Enhanced with MCP (Model Context Protocol) for external context.
        """
        sector = state["sector"]
        data = state["input_data"]
        rag_context = state["rag_context"]

        mcp_context = {}
        if MCP_AVAILABLE:
            try:
                mcp_client = get_mcp_client()
                if mcp_client.enabled:
                    mcp_context = mcp_client.get_context(sector, data)
                    logger.info(f"✅ MCP context retrieved: {list(mcp_context.keys())}")
            except Exception as e:
                logger.warning(f"MCP context retrieval failed: {e}")

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

        if not use_hf:
            state["fraud_score"] = rule_based_score
            state["risk_level"] = rule_based_risk
            state["risk_factors"] = []
            state["model_name"] = "Rule-Based Scoring (LLM rejected or unavailable)"
            state["_analysis_method"] = "rule_based"
            state["_hf_rejected"] = True
            logger.info(
                f"[Final] ✅ Using RULE-BASED score: {rule_based_score:.2f} ({rule_based_risk.upper()}) - "
                f"{provider_label} was rejected or unavailable"
            )
        else:
            state["fraud_score"] = hf_result["fraud_score"]
            state["risk_level"] = hf_result["risk_level"].lower()
            state["risk_factors"] = hf_result.get("risk_factors", [])
            state["explanation"] = hf_result.get("reasoning", "")
            if "model_used" in hf_result:
                state["model_name"] = hf_result["model_used"]
            if "clinical_score" in hf_result:
                state["clinical_score"] = hf_result["clinical_score"]
            state["_analysis_method"] = "llm_validated"
            state["_hf_rejected"] = False
            logger.info(
                f"[Final] ✅ Using VALIDATED {provider_label} score: {hf_result['fraud_score']:.2f} "
                f"({hf_result['risk_level']}) - Validated against rule-based ({rule_based_score:.2f})"
            )

        return state
    
    def _generate_explanation(self, state: RouterState) -> RouterState:
        """Generate human-readable explanation - TRANSPARENT about method used"""
        sector = state["sector"]
        data = state["input_data"]
        fraud_score = state["fraud_score"]
        risk_level = state["risk_level"]
        model_name = state["model_name"]
        analysis_method = state.get("_analysis_method", "rule_based")
        
        if state.get("explanation") and analysis_method == "llm_validated":
            base_explanation = state["explanation"]
            
            # For medical claims with two-stage pipeline, add clinical context
            if sector == "medical" and ("Two-Stage" in model_name or "MedGemma" in model_name):
                clinical_score = state.get("clinical_score")
                if clinical_score is not None:
                    clinical_context = f"Clinical validation assessed this claim at {clinical_score}/100 for medical appropriateness. "
                    if not base_explanation.startswith(clinical_context):
                        base_explanation = clinical_context + base_explanation
                
                if len(base_explanation.split('.')) < 3:
                    enhancement = f" This assessment combines clinical legitimacy validation with fraud pattern analysis to provide a comprehensive risk evaluation."
                    if enhancement not in base_explanation:
                        base_explanation += enhancement
            
            # Ensure explanation has sufficient detail (at least 3 sentences)
            sentences = [s.strip() for s in base_explanation.split('.') if s.strip()]
            if len(sentences) < 3:
                enhancements = {
                    "banking": " This analysis evaluated transaction patterns, account history, geographic risk factors, device fingerprinting, and transaction velocity to determine the fraud probability. The assessment considers both individual risk indicators and their combined impact on overall fraud likelihood.",
                    "ecommerce": " This analysis examined seller account age, pricing patterns relative to market value, customer review sentiment, shipping origin transparency, and product listing details to assess fraud risk. Multiple data points were cross-referenced to identify potential scams or fraudulent listings.",
                    "supply_chain": " This analysis reviewed supplier credentials, pricing anomalies relative to market rates, logistics patterns, payment terms, and documentation completeness to identify potential fraud. The evaluation considers both individual risk factors and their correlation with known fraud patterns.",
                }
                enhancement = enhancements.get(sector, " This analysis evaluated multiple risk factors across different dimensions to determine the fraud probability. The assessment combines pattern recognition with statistical analysis to provide a comprehensive risk evaluation.")
                
                if enhancement not in base_explanation:
                    base_explanation += enhancement
            
            prefix = f"{model_name} analysis: "
            if not base_explanation.startswith(prefix):
                state["explanation"] = prefix + base_explanation
            else:
                state["explanation"] = base_explanation
            logger.debug(f"[Explanation] Using enhanced LLM-generated explanation from {model_name}")
        else:
            explanation = build_rule_based_explanation(sector, data, fraud_score, risk_level, model_name)
            state["explanation"] = explanation
            logger.debug(f"[Explanation] Generated rule-based explanation (HF was rejected or unavailable)")
        
        return state
    
    def _format_query(self, sector: str, data: Dict[str, Any]) -> str:
        """Format input data as query text for RAG"""
        return json.dumps(data, indent=2)
    
    def _calculate_fraud_score(self, sector: str, data: Dict[str, Any], rag_context: str) -> float:
        """Calculate fraud score using sector chains with RAG enhancement."""
        from app.llm.chains import calculate_fraud_score as chain_score
        return chain_score(sector, data, rag_context)

    async def route_and_analyze(self, sector: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the full LangGraph workflow"""
        
        initial_state: RouterState = {
            "sector": sector,
            "input_data": data,
            "model_name": "",
            "rag_context": "",
            "fraud_score": 0.0,
            "risk_level": "",
            "explanation": "",
            "similar_patterns": 0,
            "risk_factors": []
        }
        
        final_state = self.workflow.invoke(initial_state)
        
        return {
            "fraud_score": final_state["fraud_score"],
            "risk_level": final_state["risk_level"],
            "explanation": final_state["explanation"],
            "model_used": final_state["model_name"],
            "similar_patterns": final_state["similar_patterns"],
            "risk_factors": final_state.get("risk_factors", [])
        }


# Helper function for HF client fallback
def analyze_fraud_rule_based(sector: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Rule-based fraud analysis (fallback when HF API fails)"""
    from .rag_engine import RAGEngine

    rag = RAGEngine()
    router = LangGraphRouter(rag, hf_client=None)

    fraud_score = router._calculate_fraud_score(sector, data, "")
    risk_level = get_risk_level(fraud_score)
    model_name = router.model_mapping.get(sector, "Nemotron-3-Nano-30B (fallback)")
    reasoning = build_rule_based_explanation(sector, data, fraud_score, risk_level, model_name)

    return {
        "fraud_score": fraud_score,
        "risk_level": risk_level.upper(),
        "reasoning": reasoning,
        "risk_factors": ["Rule-based analysis"]
    }
