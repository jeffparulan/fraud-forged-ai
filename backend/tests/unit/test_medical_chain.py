"""Medical billing-rule scoring — unbundling / sample calibration."""
from app.llm.chains.medical_chain import score_medical_fraud_detailed
from app.llm.parsing import get_risk_level


UNBUNDLING = {
    "claim_amount": 28000,
    "procedure_codes": ["27447", "27486", "29881", "29882"],
    "diagnosis_codes": ["M17.11", "M25.561"],
    "claim_details": (
        "Operative note: Right total knee arthroplasty (CPT 27447). "
        "Same encounter also billed revision component (27486) plus arthroscopic "
        "meniscectomy/repair (29881, 29882). Arthroscopy was performed in the same "
        "operative session as the arthroplasty. Billing concern: arthroscopy and "
        "arthroplasty components are typically bundled rather than billed separately."
    ),
    "provider_history": "clean",
}


def test_unbundling_scores_medium_with_explicit_factors():
    score, breakdown = score_medical_fraud_detailed(UNBUNDLING)
    labels = " ".join(str(b.get("label", "")).lower() for b in breakdown)
    assert 30 <= score < 60, score
    assert get_risk_level(score) == "MEDIUM"
    assert all("label" in b and "points" in b and "signal" in b for b in breakdown)
    assert "unbundling" in labels or "27447" in labels
    assert "29881" in labels or "arthroscopy" in labels


def test_unequal_icd_cpt_counts_alone_do_not_imply_mismatch():
    """Frontend used to set diagnosis_mismatch when len(ICD) != len(CPT).

    That is normal claim shape and was falsely boosting Medium unbundling to CRITICAL.
    """
    payload = {
        **UNBUNDLING,
        # Explicitly omit diagnosis_mismatch — unequal counts must not auto-fire +40.
    }
    assert len(payload["diagnosis_codes"]) != len(payload["procedure_codes"])
    score, breakdown = score_medical_fraud_detailed(payload)
    assert score < 60, score
    assert get_risk_level(score) == "MEDIUM"
    assert not any(b.get("signal") == "mismatch" for b in breakdown)

    # When a real mismatch is asserted, the +40 signal should apply.
    flagged = {**payload, "diagnosis_mismatch": True}
    flagged_score, flagged_breakdown = score_medical_fraud_detailed(flagged)
    assert flagged_score >= score + 35
    assert any(b.get("signal") == "mismatch" for b in flagged_breakdown)


def test_legitimate_surgery_stays_low():
    score, _ = score_medical_fraud_detailed(
        {
            "claim_amount": 45000,
            "procedure_codes": ["63081", "22614", "20936"],
            "diagnosis_codes": ["M48.06", "G95.11", "M50.22"],
            "claim_details": (
                "Complex multi-level procedure with bone grafting. "
                "Well documented medical necessity and consent."
            ),
            "provider_history": "clean",
        }
    )
    assert score < 30, score
