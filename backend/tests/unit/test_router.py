"""Unit tests for LangGraph router."""
import pytest
from unittest.mock import Mock, patch
from app.core.router import LangGraphRouter, analyze_fraud_rule_based


class TestLangGraphRouter:
    def test_init(self):
        mock_rag = Mock()
        router = LangGraphRouter(mock_rag)
        assert router.rag_engine == mock_rag
        assert router.hf_client is None
    
    def test_init_with_hf_client(self):
        mock_rag = Mock()
        mock_hf = Mock()
        router = LangGraphRouter(mock_rag, hf_client=mock_hf)
        assert router.hf_client == mock_hf
    
    def test_model_mapping(self):
        from app.llm.config import SECTOR_MODELS, get_sector_route_display
        for sector in ("banking", "medical", "ecommerce", "supply_chain"):
            assert sector in SECTOR_MODELS
            assert get_sector_route_display(sector)

    def test_retrieve_rag_context(self):
        mock_rag = Mock()
        mock_rag.query_similar_patterns.return_value = {
            "context": "test context",
            "count": 3,
            "patterns": [{"risk_level": "high", "description": "x", "score": 0.9}],
            "top_score": 0.9,
            "avg_score": 0.8,
            "embedding_source": "hf",
        }
        router = LangGraphRouter(mock_rag)
        state = {
            "sector": "banking",
            "input_data": {"amount": 1000},
            "rag_context": "",
            "similar_patterns": 0,
            "decision_trace": [],
        }
        result = router._retrieve_rag_context(state)
        assert result["rag_context"] == "test context"
        assert result["similar_patterns"] == 3
        assert result["rag_top_score"] == 0.9
        assert result["embedding_source"] == "hf"
        assert result["rag_top_risk_level"] == "high"

    def test_guardrail_ignores_high_sim_low_risk_rag(self):
        """Matching a LOW pattern at high similarity must not force HIGH."""
        mock_rag = Mock()
        router = LangGraphRouter(mock_rag)
        state = {
            "sector": "medical",
            "input_data": {},
            "fraud_score": 30.0,
            "risk_level": "medium",
            "rag_top_score": 0.88,
            "rag_top_risk_level": "low",
            "risk_factors": [],
            "decision_trace": [],
            "mcp_context": {},
        }
        out = router._apply_guardrails(state)
        assert out["fraud_score"] == 30.0
        assert out["risk_level"] == "medium"
        assert not out.get("_guardrail_adjusted")

    def test_guardrail_escalates_high_sim_critical_rag(self):
        mock_rag = Mock()
        router = LangGraphRouter(mock_rag)
        state = {
            "sector": "medical",
            "input_data": {},
            "fraud_score": 35.0,
            "risk_level": "medium",
            "rag_top_score": 0.9,
            "rag_top_risk_level": "critical",
            "risk_factors": [],
            "decision_trace": [],
            "mcp_context": {},
        }
        out = router._apply_guardrails(state)
        assert out["fraud_score"] >= 85.0
        assert out["risk_level"] == "critical"
        assert out.get("_guardrail_adjusted")

    def test_ecommerce_maps_to_ultra(self):
        from app.llm.config import get_sector_route_display
        assert "Ultra" in get_sector_route_display("ecommerce")
        assert "Ultra" in get_sector_route_display("supply_chain")
        assert "MedGemma" in get_sector_route_display("medical")

    def test_route_to_model(self):
        mock_rag = Mock()
        router = LangGraphRouter(mock_rag)
        state = {"sector": "banking", "input_data": {}, "decision_trace": []}
        result = router._route_to_model(state)
        assert "Qwen" in result["model_name"]
        assert len(result["decision_trace"]) == 1

    def test_calculate_fraud_score(self):
        mock_rag = Mock()
        router = LangGraphRouter(mock_rag)
        score = router._calculate_fraud_score("banking", {"amount": 1000}, "")
        assert isinstance(score, (int, float))
        assert 0 <= score <= 100

    def test_no_gpt_or_gemma_in_config(self):
        from app.llm.config import get_sector_model_candidates
        banned = ("gpt-oss", "gemma-4", "hy3", "tencent")
        for sector in ("banking", "medical", "ecommerce", "supply_chain"):
            for c in get_sector_model_candidates(sector):
                mid = c["model"].lower()
                assert not any(b in mid for b in banned), f"{sector}: {c['model']}"
