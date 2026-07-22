"""Sector-specific fraud scoring chains."""
from .banking_chain import score_banking_fraud, score_banking_fraud_detailed
from .medical_chain import score_medical_fraud
from .ecommerce_chain import score_ecommerce_fraud
from .supply_chain_chain import score_supply_chain_fraud
from typing import Dict, Any, List, Tuple
import logging

logger = logging.getLogger(__name__)

SCORING_CHAINS = {
    "banking": score_banking_fraud,
    "medical": score_medical_fraud,
    "ecommerce": score_ecommerce_fraud,
    "supply_chain": score_supply_chain_fraud,
}


def score_with_breakdown(sector: str, data: Dict[str, Any]) -> Tuple[float, List[Dict[str, Any]]]:
    """Return (score, contribution breakdown). Banking has full detail; others return empty breakdown."""
    if sector == "banking":
        return score_banking_fraud_detailed(data)
    score_fn = SCORING_CHAINS.get(sector)
    score = score_fn(data) if score_fn else 50.0
    return score, []


def calculate_fraud_score(sector: str, data: Dict[str, Any], rag_context: str = "") -> float:
    """
    Calculate fraud score with sector-specific logic and optional RAG enhancement.
    """
    score, _ = score_with_breakdown(sector, data)

    if rag_context and rag_context != "No similar patterns found.":
        rag_lower = rag_context.lower()
        legitimate_keywords = ["low risk", "legitimate", "normal", "standard", "established", "verified", "clean"]
        if any(kw in rag_lower for kw in legitimate_keywords) and score < 30:
            score = max(0, score * 0.8)
        elif score > 30:
            if any(kw in rag_lower for kw in ["high risk", "fraud", "critical", "suspicious", "anomaly"]):
                score = min(100, score * 1.1)
            elif any(kw in rag_lower for kw in ["medium risk", "warning", "unusual", "irregular"]):
                score = min(100, score * 1.05)

    return round(score, 1)
