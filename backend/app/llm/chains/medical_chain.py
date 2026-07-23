"""Medical claims fraud scoring chain."""
from typing import Dict, Any, List, Tuple


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


def _normalize_cpt(code: str) -> str:
    return "".join(ch for ch in str(code) if ch.isalnum()).upper()


def _detect_unbundling(procedures: List[str], details: str) -> List[Tuple[str, float]]:
    """
    Classic orthopedic / same-session unbundling signals.
    Keep contributions calibrated for labeled Medium samples (~50 range).
    """
    hits: List[Tuple[str, float]] = []
    codes = {_normalize_cpt(p) for p in procedures}
    arthro = {c for c in codes if c.startswith("298")}
    has_tka = "27447" in codes
    has_revision = "27486" in codes

    if has_tka and arthro:
        hits.append(
            (
                "Possible unbundling: total knee arthroplasty (27447) billed with "
                f"arthroscopy ({', '.join(sorted(arthro))}) in the same claim",
                20.0,
            )
        )
    if has_tka and has_revision:
        hits.append(
            (
                "Primary arthroplasty (27447) billed with revision component (27486) "
                "on the same encounter",
                12.0,
            )
        )

    detail_signals = [
        ("typically bundled", "Claim notes components that are typically bundled"),
        ("should be bundled", "Claim notes components that should be bundled"),
        ("same operative session", "Multiple major procedures documented in the same operative session"),
        ("billed separately", "Claim explicitly flags separately billed components"),
    ]
    for needle, label in detail_signals:
        if needle in details and not any(label in h[0] for h in hits):
            hits.append((label, 10.0))
            break  # one narrative keyword bump is enough with CPT hits

    return hits


def score_medical_fraud_detailed(data: Dict[str, Any]) -> Tuple[float, List[Dict[str, Any]]]:
    """Medical claims fraud scoring with contribution breakdown / risk factor labels.

    Breakdown items match banking shape: {label, points, signal} for the UI.
    """
    score = 0.0
    breakdown: List[Dict[str, Any]] = []

    def add(points: float, label: str, signal: str = "billing") -> None:
        nonlocal score
        if points == 0:
            return
        score += points
        breakdown.append({"label": label, "points": points, "signal": signal})

    try:
        claim_amount = float(data.get("claim_amount", 0))
    except (ValueError, TypeError):
        claim_amount = 0.0

    if claim_amount > 100000:
        add(35, f"Very high claim amount (${claim_amount:,.0f})", "amount")
    elif claim_amount > 50000:
        add(25, f"High claim amount (${claim_amount:,.0f})", "amount")
    elif claim_amount > 20000:
        add(15, f"Elevated claim amount (${claim_amount:,.0f})", "amount")
    elif claim_amount < 1000:
        add(-5, "Low claim amount", "amount")

    procedures = _get_procedures(data)
    diagnoses = _get_diagnoses(data)
    proc_count = len(procedures)
    diag_count = len(diagnoses)

    if proc_count > 10:
        add(35, f"{proc_count} procedures on a single claim", "procedures")
    elif proc_count >= 7:
        add(25, f"{proc_count} procedures on a single claim", "procedures")
    elif proc_count >= 5:
        add(15, f"{proc_count} procedures on a single claim", "procedures")
    elif proc_count >= 3:
        add(5, f"{proc_count} procedures on a single claim", "procedures")

    if proc_count >= 5 and diag_count > 0 and proc_count >= 2 * diag_count + 1:
        add(20, "Procedure volume high relative to diagnosis count", "procedures")

    if proc_count >= 5 and claim_amount > 50000:
        add(15, "High procedure count with high claim amount", "procedures")

    provider_history = str(data.get("provider_history", "clean")).lower()
    if "flagged" in provider_history or "suspended" in provider_history or "fraud" in provider_history:
        add(40, "Provider history includes prior fraud / compliance flags", "provider")
    elif "clean" in provider_history or "verified" in provider_history:
        add(-5, "Provider history clean", "provider")

    details = str(data.get("claim_details", "")).lower()
    suspicion_keywords = [
        ("no visits", "No visits documented for billed dates", "phantom_visits", 15),
        ("no consent", "No consent documented for billed procedures", "phantom_consent", 15),
        ("no record", "Missing clinical record for billed services", "docs_record", 15),
        ("no documentation", "Missing documentation for billed services", "docs_missing", 15),
        ("missing record", "Missing record for billed services", "docs_missing_alt", 15),
        ("no significant improvement", "Care continued without documented improvement", "necessity", 15),
        ("all tests in", "Intensity of same-day testing exceeds typical necessity", "upcoding", 10),
        ("minimal supporting", "Minimal supporting documentation", "docs_minimal", 15),
    ]
    keyword_hits = 0
    seen_signals = set()
    for needle, label, signal, points in suspicion_keywords:
        if needle not in details:
            continue
        if signal in seen_signals:
            continue
        keyword_hits += 1
        if keyword_hits > 2:
            break
        seen_signals.add(signal)
        add(points, label, signal)

    for reason, points in _detect_unbundling(procedures, details):
        add(points, reason, "unbundling")

    if data.get("diagnosis_mismatch", False):
        add(40, "Diagnosis–procedure mismatch flagged", "mismatch")

    if not data.get("provider_verified", True):
        add(25, "Provider not verified", "provider")

    final = max(0.0, min(100.0, score))
    return final, breakdown


def score_medical_fraud(data: Dict[str, Any]) -> float:
    """Medical claims fraud scoring — claim amount, procedure volume, provider history, mismatch."""
    score, _ = score_medical_fraud_detailed(data)
    return score
