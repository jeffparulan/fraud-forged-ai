"""Medical claims fraud scoring chain."""
from typing import Dict, Any


def score_medical_fraud(data: Dict[str, Any]) -> float:
    """Medical claims fraud scoring - claim amount, procedures, provider history."""
    score = 0.0

    try:
        claim_amount = float(data.get("claim_amount", 0))
    except (ValueError, TypeError):
        claim_amount = 0.0
    if claim_amount > 100000:
        score += 35
    elif claim_amount > 50000:
        score += 25
    elif claim_amount > 20000:
        score += 15
    elif claim_amount < 1000:
        score -= 5

    procedures = data.get("procedures", [])
    if isinstance(procedures, list):
        if len(procedures) > 10:
            score += 30
        elif len(procedures) > 5:
            score += 20
    elif isinstance(procedures, str):
        procedure_count = len(procedures.split(",")) if procedures else 0
        if procedure_count > 10:
            score += 30
        elif procedure_count > 5:
            score += 20

    provider_history = str(data.get("provider_history", "clean")).lower()
    if "flagged" in provider_history or "suspended" in provider_history:
        score += 45
    elif "clean" in provider_history or "verified" in provider_history:
        score -= 5

    if data.get("diagnosis_mismatch", False):
        score += 40

    if not data.get("provider_verified", True):
        score += 25

    return max(0, min(100, score))
