"""Unit tests for local MedGemma Stage 1 client."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.llm import medgemma_local as ml


SAMPLE_AUDIT = {
    "clinical_assessment": {
        "overall_summary": "CPT 99213 is supported by the note; ICD linkage is appropriate.",
        "cpt_findings": [
            {
                "cpt_code": "99213",
                "documentation_support": "supported",
                "evidence_of_performance": "supported",
                "linked_icd_codes": ["J06.9"],
                "severity_complexity_assessment": "Low complexity office visit.",
                "supporting_quotes": ["Patient presents with sore throat."],
                "documentation_gaps": [],
            }
        ],
    },
    "model_used": "medgemma-1.5-local",
    "inference_seconds": 19.2,
}


UNSUPPORTED_AUDIT = {
    "clinical_assessment": {
        "overall_summary": "CPT is clinically incompatible with the stated diagnosis set.",
        "cpt_findings": [
            {
                "cpt_code": "27447",
                "documentation_support": "not_supported",
                "evidence_of_performance": "not_supported",
                "linked_icd_codes": ["J06.9"],
                "severity_complexity_assessment": "Knee arthroplasty is not appropriate for URI diagnosis.",
                "supporting_quotes": [],
                # Clinical incompatibility — not a thin-note / missing-chart signal
                "documentation_gaps": ["CPT/ICD clinical mismatch for procedure selection."],
            }
        ],
    },
    "model_used": "medgemma-1.5-local",
    "inference_seconds": 21.0,
}

THIN_NOTE_AUDIT = {
    "clinical_assessment": {
        "overall_summary": "Note is too brief to verify procedures.",
        "cpt_findings": [
            {
                "cpt_code": "27447",
                "documentation_support": "not_supported",
                "evidence_of_performance": "not_supported",
                "linked_icd_codes": ["M17.11"],
                "severity_complexity_assessment": "Cannot verify from one-line note.",
                "supporting_quotes": [],
                "documentation_gaps": [],
            },
            {
                "cpt_code": "29881",
                "documentation_support": "not_supported",
                "evidence_of_performance": "not_supported",
                "linked_icd_codes": ["M17.11"],
                "severity_complexity_assessment": "Cannot verify from one-line note.",
                "supporting_quotes": [],
                "documentation_gaps": [],
            },
        ],
    },
    "model_used": "medgemma-1.5-local",
    "inference_seconds": 12.0,
}


CLAIM = {
    "claim_id": "CLM-1",
    "patient_age": 45,
    "specialty": "Family Medicine",
    "diagnosis_codes": ["J06.9"],
    "procedure_codes": ["99213"],
    "claim_amount": 185,
    "claim_details": "Office visit for acute URI.",
    "provider_history": "clean",
}


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    monkeypatch.setenv("MEDGEMMA_LOCAL_BASE_URL", "https://example.invalid")
    monkeypatch.setenv("MEDGEMMA_LOCAL_API_KEY", "test-key-not-real")
    yield


def test_map_audit_supported():
    mapped = ml.map_audit_response_to_stage1(SAMPLE_AUDIT)
    assert mapped["clinical_legitimacy_score"] >= 80
    assert "supported" in mapped["reasoning"].lower() or "99213" in mapped["reasoning"]
    assert mapped["diagnosis_procedure_match"] == "Compatible"
    assert mapped["model_used"] == "medgemma-1.5-local"
    # Supporting quotes must not be required in Stage 1 reasoning (PHI minimization)
    assert "Patient presents with sore throat" not in mapped["reasoning"]


def test_map_audit_unsupported_flags():
    mapped = ml.map_audit_response_to_stage1(UNSUPPORTED_AUDIT)
    assert mapped["clinical_legitimacy_score"] <= 40
    assert mapped["diagnosis_procedure_match"] == "Incompatible"
    assert mapped.get("incomplete_chart_audit") is False
    assert any("not supported" in f.lower() for f in mapped["risk_factors"])
    assert any("documentation gap" in f.lower() for f in mapped["risk_factors"])


def test_map_thin_note_not_treated_as_medical_impossibility():
    mapped = ml.map_audit_response_to_stage1(THIN_NOTE_AUDIT)
    assert mapped.get("incomplete_chart_audit") is True
    assert 50 <= mapped["clinical_legitimacy_score"] <= 62
    assert mapped["diagnosis_procedure_match"] == "Questionable"
    assert any("limited clinical documentation" in f.lower() for f in mapped["risk_factors"])
    assert not any("cpt 27447: documentation/evidence not supported" in f.lower() for f in mapped["risk_factors"])


def test_build_audit_request_shape():
    body = ml.build_audit_request(CLAIM)
    assert set(body.keys()) == {"clinical_notes", "icd_codes", "cpt_codes"}
    assert body["icd_codes"] == ["J06.9"]
    assert body["cpt_codes"] == ["99213"]
    assert "Office visit" in body["clinical_notes"]
    assert 1 <= len(body["clinical_notes"]) <= 50000


def test_audit_claim_success(monkeypatch):
    def fake_post(url, headers=None, json=None, timeout=None):
        assert url.endswith("/v1/audit-claim")
        assert headers["X-API-Key"] == "test-key-not-real"
        assert headers["ngrok-skip-browser-warning"] == "true"
        assert "example.invalid" not in str(json)  # body is claim fields, fine
        resp = MagicMock()
        resp.status_code = 200
        resp.headers = {"content-type": "application/json"}
        resp.json.return_value = SAMPLE_AUDIT
        return resp

    monkeypatch.setattr(ml.httpx, "post", fake_post)
    result = ml.audit_claim(CLAIM)
    assert result["clinical_legitimacy_score"] >= 80
    assert result["provider"] == "medgemma_local"


def test_audit_claim_401_no_retry(monkeypatch):
    calls = {"n": 0}

    def fake_post(url, headers=None, json=None, timeout=None):
        calls["n"] += 1
        resp = MagicMock()
        resp.status_code = 401
        resp.headers = {"content-type": "application/json"}
        return resp

    monkeypatch.setattr(ml.httpx, "post", fake_post)
    with pytest.raises(ml.MedGemmaLocalConfigError):
        ml.audit_claim(CLAIM)
    assert calls["n"] == 1
    assert ml.try_audit_claim(CLAIM) is None
    assert calls["n"] == 2  # try_ wraps once more, still no retry loop


def test_audit_claim_422_no_retry(monkeypatch):
    calls = {"n": 0}

    def fake_post(url, headers=None, json=None, timeout=None):
        calls["n"] += 1
        resp = MagicMock()
        resp.status_code = 422
        resp.headers = {"content-type": "application/json"}
        return resp

    monkeypatch.setattr(ml.httpx, "post", fake_post)
    with pytest.raises(ml.MedGemmaLocalConfigError):
        ml.audit_claim(CLAIM)
    assert calls["n"] == 1


def test_audit_claim_502_triggers_fallback_none(monkeypatch):
    def fake_post(url, headers=None, json=None, timeout=None):
        resp = MagicMock()
        resp.status_code = 502
        resp.headers = {"content-type": "text/plain"}
        return resp

    monkeypatch.setattr(ml.httpx, "post", fake_post)
    with pytest.raises(ml.MedGemmaLocalUpstreamError):
        ml.audit_claim(CLAIM)
    assert ml.try_audit_claim(CLAIM) is None


def test_audit_claim_timeout_triggers_fallback_none(monkeypatch):
    def fake_post(url, headers=None, json=None, timeout=None):
        raise httpx.TimeoutException("timed out")

    monkeypatch.setattr(ml.httpx, "post", fake_post)
    with pytest.raises(ml.MedGemmaLocalUpstreamError):
        ml.audit_claim(CLAIM)
    assert ml.try_audit_claim(CLAIM) is None


def test_audit_claim_ngrok_html_non_json(monkeypatch):
    def fake_post(url, headers=None, json=None, timeout=None):
        resp = MagicMock()
        resp.status_code = 200
        resp.headers = {"content-type": "text/html; charset=utf-8"}
        resp.json.side_effect = ValueError("no json")
        return resp

    monkeypatch.setattr(ml.httpx, "post", fake_post)
    with pytest.raises(ml.MedGemmaLocalUpstreamError) as exc:
        ml.audit_claim(CLAIM)
    assert "ngrok" in str(exc.value).lower() or "non-json" in str(exc.value).lower()
    assert ml.try_audit_claim(CLAIM) is None


def test_stage1_failure_continues_when_optional():
    """Orchestrator: medgemma_local None + stage1_optional → Stage 2 still runs."""
    from app.llm.orchestrator import LLMClient

    client = LLMClient(api_token="unused")
    model_config = {
        "two_stage": True,
        "stage1_optional": True,
        "stage1": {
            "name": "Clinical Legitimacy Validation",
            "provider": "medgemma_local",
            "model": "medgemma-local-1.5",
            "display": "MedGemma-1.5 (Local)",
        },
        "stage2": {
            "name": "Fraud Pattern Analysis",
            "provider": "openrouter",
            "model": "nvidia/nemotron-3-super-120b-a12b:free",
            "display": "Nemotron-Super-120B",
        },
        "fallbacks": [],
    }

    stage2_parsed = {
        "fraud_score": 72,
        "risk_level": "high",
        "reasoning": "Billing anomalies present.",
        "risk_factors": ["high claim amount"],
        "score_parsed": True,
    }

    with patch("app.llm.medgemma_local.try_audit_claim", return_value=None), patch.object(
        client, "_try_openrouter_model", return_value=stage2_parsed
    ) as mock_or:
        result = client._analyze_two_stage("medical", CLAIM, "rag ctx", model_config)

    mock_or.assert_called_once()
    # Stage 2 prompt should include deferred clinical messaging
    prompt = mock_or.call_args[0][1]
    assert "Clinical Legitimacy Score: 50/100" in prompt
    assert "unavailable" in prompt.lower() or "skipped" in prompt.lower()
    assert result["fraud_score"] == 72
    assert "MedGemma deferred" in result["model_used"]


def test_stage1_success_skips_stage2_when_opted_out(monkeypatch):
    """MEDICAL_TRY_STAGE2_LLM=0 → blend with rules; do not call OpenRouter."""
    from app.llm.orchestrator import LLMClient

    monkeypatch.setenv("MEDICAL_TRY_STAGE2_LLM", "0")
    client = LLMClient(api_token="unused")
    model_config = {
        "two_stage": True,
        "stage1_optional": True,
        "stage1": {
            "name": "Clinical Legitimacy Validation",
            "provider": "medgemma_local",
            "model": "medgemma-local-1.5",
            "display": "MedGemma-1.5 (Local)",
        },
        "stage2": {
            "name": "Fraud Pattern Analysis",
            "provider": "openrouter",
            "model": "nvidia/nemotron-3-super-120b-a12b:free",
            "display": "Nemotron-Super-120B",
        },
        "fallbacks": [],
    }
    stage1 = ml.map_audit_response_to_stage1(UNSUPPORTED_AUDIT)

    with patch("app.llm.medgemma_local.try_audit_claim", return_value=stage1), patch.object(
        client, "_try_openrouter_model"
    ) as mock_or:
        result = client._analyze_two_stage("medical", CLAIM, None, model_config)

    mock_or.assert_not_called()
    assert "Two-Stage:" in result["model_used"]
    assert "MedGemma" in result["model_used"]
    assert "Billing Rules + Clinical Blend" in result["model_used"]
    assert "unavailable" not in result["model_used"].lower()
    assert result.get("score_parsed") is True
    assert not any("unavailable" in f.lower() for f in result.get("risk_factors", []))


def test_stage1_success_calls_nemotron_stage2_by_default(monkeypatch):
    """Default path: MedGemma Stage 1 → Nemotron Stage 2."""
    from app.llm.orchestrator import LLMClient

    monkeypatch.delenv("MEDICAL_TRY_STAGE2_LLM", raising=False)
    client = LLMClient(api_token="unused")
    model_config = {
        "two_stage": True,
        "stage1_optional": True,
        "stage1": {
            "name": "Clinical Legitimacy Validation",
            "provider": "medgemma_local",
            "model": "medgemma-local-1.5",
            "display": "MedGemma-1.5 (Local)",
        },
        "stage2": {
            "name": "Fraud Pattern Analysis",
            "provider": "openrouter",
            "model": "nvidia/nemotron-3-super-120b-a12b:free",
            "display": "Nemotron-Super-120B",
        },
        "fallbacks": [],
    }
    stage1 = ml.map_audit_response_to_stage1(SAMPLE_AUDIT)
    stage2_parsed = {
        "fraud_score": 80,
        "risk_level": "high",
        "reasoning": "Clinical + billing risk.",
        "risk_factors": ["mismatch"],
        "score_parsed": True,
    }

    with patch("app.llm.medgemma_local.try_audit_claim", return_value=stage1), patch.object(
        client, "_try_openrouter_model", return_value=stage2_parsed
    ) as mock_or:
        result = client._analyze_two_stage("medical", CLAIM, None, model_config)

    mock_or.assert_called_once()
    assert result["fraud_score"] == 80
    assert "Nemotron" in result["model_used"] or "nemotron" in result["model_used"].lower()
    assert "Two-Stage:" in result["model_used"]
    assert "Billing Rules" not in result["model_used"]


def test_stage1_success_can_force_stage2_llm(monkeypatch):
    from app.llm.orchestrator import LLMClient

    monkeypatch.setenv("MEDICAL_TRY_STAGE2_LLM", "1")
    client = LLMClient(api_token="unused")
    model_config = {
        "two_stage": True,
        "stage1_optional": True,
        "stage1": {
            "name": "Clinical Legitimacy Validation",
            "provider": "medgemma_local",
            "model": "medgemma-local-1.5",
            "display": "MedGemma-1.5 (Local)",
        },
        "stage2": {
            "name": "Fraud Pattern Analysis",
            "provider": "openrouter",
            "model": "nvidia/nemotron-3-super-120b-a12b:free",
            "display": "Nemotron-Super-120B",
        },
        "fallbacks": [],
    }
    stage1 = ml.map_audit_response_to_stage1(SAMPLE_AUDIT)
    stage2_parsed = {
        "fraud_score": 80,
        "risk_level": "high",
        "reasoning": "Clinical + billing risk.",
        "risk_factors": ["mismatch"],
        "score_parsed": True,
    }

    with patch("app.llm.medgemma_local.try_audit_claim", return_value=stage1), patch.object(
        client, "_try_openrouter_model", return_value=stage2_parsed
    ) as mock_or:
        result = client._analyze_two_stage("medical", CLAIM, None, model_config)

    mock_or.assert_called_once()
    assert result["fraud_score"] == 80


def test_health_check_ok(monkeypatch):
    def fake_get(url, headers=None, timeout=None):
        assert url.endswith("/healthz")
        assert headers["ngrok-skip-browser-warning"] == "true"
        resp = MagicMock()
        resp.status_code = 200
        resp.headers = {"content-type": "application/json"}
        resp.json.return_value = {"status": "ok"}
        return resp

    monkeypatch.setattr(ml.httpx, "get", fake_get)
    assert ml.health_check()["ok"] is True


def test_no_phi_in_success_logs(monkeypatch, caplog):
    import logging

    def fake_post(url, headers=None, json=None, timeout=None):
        resp = MagicMock()
        resp.status_code = 200
        resp.headers = {"content-type": "application/json"}
        resp.json.return_value = SAMPLE_AUDIT
        return resp

    monkeypatch.setattr(ml.httpx, "post", fake_post)
    with caplog.at_level(logging.INFO, logger="app.llm.medgemma_local"):
        ml.audit_claim(CLAIM)
    joined = " ".join(r.message for r in caplog.records)
    assert "Office visit for acute URI" not in joined
    assert "Patient presents with sore throat" not in joined
    assert "test-key-not-real" not in joined
    assert "example.invalid" not in joined
