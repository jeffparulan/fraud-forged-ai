"""Unit tests for explanation generation."""
import pytest
from app.core.explanations import (
    explain_banking,
    explain_medical,
    explain_ecommerce,
    explain_supply_chain,
    build_rule_based_explanation
)


class TestExplainBanking:
    def test_high_amount_flagged(self):
        data = {"amount": 15000}
        result = explain_banking(data, 70)
        assert "high transaction amount" in result.lower()
        assert "$15,000" in result
    
    def test_new_account_flagged(self):
        data = {"user_age_days": 15}
        result = explain_banking(data, 60)
        assert "15 days" in result
    
    def test_legitimate_transaction(self):
        data = {"amount": 100, "user_age_days": 365}
        result = explain_banking(data, 10)
        assert "legitimate" in result.lower()


class TestExplainMedical:
    def test_high_claim_amount(self):
        data = {"claim_amount": 25000}
        result = explain_medical(data, 70)
        assert "$25,000" in result
    
    def test_many_procedures(self):
        data = {"procedures": ["A", "B", "C", "D", "E", "F"]}
        result = explain_medical(data, 65)
        assert "6 procedures" in result
    
    def test_legitimate_claim(self):
        data = {"claim_amount": 500, "procedures": ["A"]}
        result = explain_medical(data, 10)
        assert "standard" in result.lower()


class TestExplainEcommerce:
    def test_new_seller(self):
        data = {"seller_age_days": 10}
        result = explain_ecommerce(data, 60)
        assert "10 days" in result
    
    def test_price_below_market(self):
        data = {"price": 50, "market_price": 200}
        result = explain_ecommerce(data, 70)
        assert "below market" in result.lower()
    
    def test_no_reviews(self):
        data = {"reviews": []}
        result = explain_ecommerce(data, 50)
        assert "no customer reviews" in result.lower()


class TestExplainSupplyChain:
    def test_new_supplier(self):
        data = {"supplier_age_days": 20}
        result = explain_supply_chain(data, 60)
        assert "20 days" in result
    
    def test_advance_payment(self):
        data = {"payment_terms": "ADVANCE"}
        result = explain_supply_chain(data, 55)
        assert "advance payment" in result.lower()
    
    def test_legitimate_supplier(self):
        data = {"supplier_age_days": 500}
        result = explain_supply_chain(data, 10)
        assert "legitimate" in result.lower()


class TestBuildRuleBasedExplanation:
    def test_banking_explanation(self):
        result = build_rule_based_explanation(
            "banking",
            {"amount": 20000},
            75,
            "high",
            "Test Model"
        )
        assert "Test Model" in result
        assert "high risk" in result.lower()
        assert "$20,000" in result
    
    def test_medical_explanation(self):
        result = build_rule_based_explanation(
            "medical",
            {"claim_amount": 30000},
            80,
            "high",
            "Test Model"
        )
        assert "Test Model" in result
        assert "$30,000" in result
    
    def test_unknown_sector(self):
        result = build_rule_based_explanation(
            "unknown",
            {},
            50,
            "medium",
            "Test Model"
        )
        assert "Test Model" in result
        assert "medium risk" in result.lower()
