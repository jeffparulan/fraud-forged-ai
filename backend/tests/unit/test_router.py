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
        mock_rag = Mock()
        router = LangGraphRouter(mock_rag)
        assert "banking" in router.model_mapping
        assert "medical" in router.model_mapping
        assert "ecommerce" in router.model_mapping
        assert "supply_chain" in router.model_mapping
    
    def test_route_to_model(self):
        mock_rag = Mock()
        router = LangGraphRouter(mock_rag)
        state = {"sector": "banking", "input_data": {}}
        result = router._route_to_model(state)
        assert "Qwen" in result["model_name"]
    
    def test_retrieve_rag_context(self):
        mock_rag = Mock()
        mock_rag.query_similar_patterns.return_value = {
            "context": "test context",
            "count": 3
        }
        router = LangGraphRouter(mock_rag)
        state = {
            "sector": "banking",
            "input_data": {"amount": 1000},
            "rag_context": "",
            "similar_patterns": 0
        }
        result = router._retrieve_rag_context(state)
        assert result["rag_context"] == "test context"
        assert result["similar_patterns"] == 3
    
    def test_calculate_fraud_score(self):
        mock_rag = Mock()
        router = LangGraphRouter(mock_rag)
        score = router._calculate_fraud_score("banking", {"amount": 1000}, "")
        assert isinstance(score, (int, float))
        assert 0 <= score <= 100

