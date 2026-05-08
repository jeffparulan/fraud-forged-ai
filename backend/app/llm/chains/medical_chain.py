"""Medical claims fraud scoring chain."""
from typing import Dict, Any, List


def _get_procedures(data: Dict[str, Any]) -> List[str]:
    """Normalize procedure list across input shapes (procedures | procedure_codes, list | comma string)."""
    raw = data.get("procedures") or data.get("procedure_codes") or []
    if isinstance(raw, list):
        return [str(p).strip() for p in raw if str(p).strip()]
    if isinstance(raw, str):
        return [p.strip() for p in raw.split(",") if p.strip()]
    return []


def _get_diagnoses(data: Dict[str, Any]) -> List[str]:
    """Normalize diagnosis list across input shapes."""
    raw = data.get("diagnosis_codes") or data.get("diagnoses") or []
    if isinstance(raw, list):
        return [str(d).strip() for d in raw if str(d).strip()]
    if isinstance(raw, str):
        return [d.strip() for d in raw.split(",") if d.strip()]
    return []


def score_medical_fraud(data: Dict[str, Any]) -> float:
    """Medical claims fraud scoring — claim amount, procedure volume, provider history, mismatch."""
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

    procedures = _get_procedures(data)
    diagnoses = _get_diagnoses(data)
    proc_count = len(procedures)
    diag_count = len(diagnoses)

    if proc_count > 10:
        score += 35
    elif proc_count >= 7:
        score += 25
    elif proc_count >= 5:
        score += 15
    elif proc_count >= 3:
        score += 5

    if proc_count >= 5 and diag_count > 0 and proc_count >= 2 * diag_count + 1:
        score += 20

    if proc_count >= 5 and claim_amount > 50000:
        score += 15

    provider_history = str(data.get("provider_history", "clean")).lower()
    if "flagged" in provider_history or "suspended" in provider_history or "fraud" in provider_history:
        score += 45
    elif "clean" in provider_history or "verified" in provider_history:
        score -= 5

    details = str(data.get("claim_details", "")).lower()
    suspicion_keywords = [
        "no visits", "no record", "no documentation", "missing record",
        "typically bundled", "should be bundled", "minimal supporting",
        "no significant improvement", "all tests in single visit",
    ]
    keyword_hits = sum(1 for kw in suspicion_keywords if kw in details)
    if keyword_hits >= 2:
        score += 30
    elif keyword_hits == 1:
        score += 20

    if data.get("diagnosis_mismatch", False):
        score += 40

    if not data.get("provider_verified", True):
        score += 25

    return max(0, min(100, score))
