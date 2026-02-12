"""Unit tests for core validation logic."""
import pytest
from app.core.validation import get_risk_level, validate_llm_result


class TestGetRiskLevel:
    def test_critical_risk(self):
        assert get_risk_level(85) == "critical"
        assert get_risk_level(90) == "critical"
        assert get_risk_level(100) == "critical"
    
    def test_high_risk(self):
        assert get_risk_level(60) == "high"
        assert get_risk_level(70) == "high"
        assert get_risk_level(84) == "high"
    
    def test_medium_risk(self):
        assert get_risk_level(30) == "medium"
        assert get_risk_level(45) == "medium"
        assert get_risk_level(59) == "medium"
    
    def test_low_risk(self):
        assert get_risk_level(0) == "low"
        assert get_risk_level(15) == "low"
        assert get_risk_level(29) == "low"


class TestValidateLLMResult:
    def test_no_hf_client(self):
        result = validate_llm_result(
            hf_client=None,
            sector="banking",
            data={},
            rag_context="",
            enhanced_data={},
            calculate_fraud_score=lambda s, d, r: 50.0
        )
        assert result["use_hf"] is False
        assert result["hf_result"] is None
        assert result["rule_based_score"] == 50.0
        assert result["rule_based_risk"] == "medium"
    
    def test_llm_accepted_close_scores(self):
        class MockHFClient:
            def analyze_fraud(self, sector, data, rag_context):
                return {
                    "fraud_score": 55.0,
                    "risk_level": "medium",
                    "risk_factors": ["test"],
                    "reasoning": "test"
                }
        
        result = validate_llm_result(
            hf_client=MockHFClient(),
            sector="banking",
            data={},
            rag_context="",
            enhanced_data={},
            calculate_fraud_score=lambda s, d, r: 50.0
        )
        assert result["use_hf"] is True
        assert result["hf_result"]["fraud_score"] == 55.0
    
    def test_llm_rejected_large_discrepancy(self):
        class MockHFClient:
            def analyze_fraud(self, sector, data, rag_context):
                return {
                    "fraud_score": 90.0,
                    "risk_level": "critical",
                    "risk_factors": ["test"],
                    "reasoning": "test"
                }
        
        result = validate_llm_result(
            hf_client=MockHFClient(),
            sector="banking",
            data={},
            rag_context="",
            enhanced_data={},
            calculate_fraud_score=lambda s, d, r: 10.0
        )
        assert result["use_hf"] is False
        assert result["rule_based_score"] == 10.0
    
    def test_medical_sector_trusts_pipeline(self):
        class MockHFClient:
            def analyze_fraud(self, sector, data, rag_context):
                return {
                    "fraud_score": 60.0,
                    "risk_level": "high",
                    "risk_factors": ["test"],
                    "reasoning": "test"
                }
        
        result = validate_llm_result(
            hf_client=MockHFClient(),
            sector="medical",
            data={},
            rag_context="",
            enhanced_data={},
            calculate_fraud_score=lambda s, d, r: 40.0
        )
        assert result["use_hf"] is True
