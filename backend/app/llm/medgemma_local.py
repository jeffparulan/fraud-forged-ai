"""
Local MedGemma clinical audit client (Mac Mini via Ollama + ngrok).

Reads MEDGEMMA_LOCAL_BASE_URL / MEDGEMMA_LOCAL_API_KEY from the environment at
call time. Never logs request/response bodies (PHI).
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

# Local inference is ~17–25s on short notes; allow headroom for cold tunnel/GPU.
DEFAULT_TIMEOUT_SECONDS = 220.0

_SUPPORT_RANK = {
    "supported": 90,
    "ambiguous": 55,
    "not_supported": 25,
}


class MedGemmaLocalConfigError(RuntimeError):
    """Misconfiguration (missing env, 401, 422) — do not retry."""


class MedGemmaLocalUpstreamError(RuntimeError):
    """Transient upstream failure (502, timeout, non-JSON) — Stage 1 fallback path."""


def _env_base_url() -> str:
    return (os.getenv("MEDGEMMA_LOCAL_BASE_URL") or "").strip().rstrip("/")


def _env_api_key() -> str:
    return (os.getenv("MEDGEMMA_LOCAL_API_KEY") or "").strip()


def is_configured() -> bool:
    return bool(_env_base_url() and _env_api_key())


def _as_code_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        return [p.strip() for p in value.replace(";", ",").split(",") if p.strip()]
    return [str(value).strip()] if str(value).strip() else []


def build_audit_request(data: Dict[str, Any]) -> Dict[str, Any]:
    """Map FraudForge medical claim fields → local /v1/audit-claim body."""
    icd = _as_code_list(data.get("diagnosis_codes") or data.get("diagnosis_code"))
    cpt = _as_code_list(data.get("procedure_codes") or data.get("procedure_code"))

    notes_parts: List[str] = []
    for key in ("claim_details", "medical_notes", "clinical_notes", "notes"):
        val = data.get(key)
        if isinstance(val, str) and val.strip():
            notes_parts.append(val.strip())
            break

    # Keep the audit payload lean — long duplicated metadata slows local inference.
    # ICD/CPT are already sent as structured fields on the request.
    if not notes_parts:
        notes_parts.append(
            "No free-text clinical notes provided. Assess clinical legitimacy from "
            f"ICD ({', '.join(icd) if icd else 'none'}) and CPT "
            f"({', '.join(cpt) if cpt else 'none'}) plus claim metadata only. "
            f"Specialty: {data.get('provider_specialty') or data.get('specialty', 'Unknown')}. "
            f"Age: {data.get('patient_age', 'Unknown')}."
        )

    clinical_notes = "\n\n".join(notes_parts)
    if len(clinical_notes) > 12000:
        clinical_notes = clinical_notes[:12000]

    return {
        "clinical_notes": clinical_notes,
        "icd_codes": icd or ["Unknown"],
        "cpt_codes": cpt or ["Unknown"],
    }


def _finding_score(finding: Dict[str, Any]) -> int:
    doc = str(finding.get("documentation_support") or "ambiguous").lower()
    evi = str(finding.get("evidence_of_performance") or "ambiguous").lower()
    return min(_SUPPORT_RANK.get(doc, 55), _SUPPORT_RANK.get(evi, 55))


def _looks_like_insufficient_chart(
    summary: str,
    findings: List[Dict[str, Any]],
    unsupported: int,
) -> bool:
    """
    True when MedGemma mostly says not_supported because the note is too thin to audit,
    not because codes are medically incoherent. Demo one-liners trigger this a lot.
    """
    if not findings or unsupported == 0:
        return False
    # Majority (or all) CPTs unsupported
    if unsupported < max(1, int(0.75 * len(findings))):
        return False

    gap_text = " ".join(
        str(g)
        for f in findings
        for g in (f.get("documentation_gaps") or [])
    ).lower()
    summary_l = (summary or "").lower()
    insufficiency_tokens = (
        "insufficient",
        "not enough",
        "no operative",
        "no documentation",
        "lacking",
        "missing",
        "absent",
        "cannot verify",
        "unable to verify",
        "too brief",
        "inadequate",
        "not documented",
        "no evidence in the note",
        "note does not",
        "does not document",
    )
    blob = f"{summary_l} {gap_text}"
    if any(tok in blob for tok in insufficiency_tokens):
        return True
    # No gaps + every CPT not_supported usually means "can't support from this note"
    # rather than a coded clinical incompatibility signal.
    total_gaps = sum(len(f.get("documentation_gaps") or []) for f in findings)
    if unsupported == len(findings) and total_gaps == 0:
        return True
    return False


def map_audit_response_to_stage1(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Reconcile local structured audit JSON into the Stage 1 dict Stage 2 already consumes:
      clinical_legitimacy_score, reasoning, risk_factors,
      diagnosis_procedure_match, provider_specialty_appropriate, medical_necessity
    """
    assessment = payload.get("clinical_assessment") or {}
    if not isinstance(assessment, dict):
        raise MedGemmaLocalUpstreamError("clinical_assessment missing or invalid")

    summary = str(assessment.get("overall_summary") or "").strip()
    findings = assessment.get("cpt_findings") or []
    if not isinstance(findings, list):
        findings = []

    risk_factors: List[str] = []
    scores: List[int] = []
    unsupported = 0
    ambiguous = 0
    reasoning_bits: List[str] = []
    if summary:
        reasoning_bits.append(summary)

    typed_findings: List[Dict[str, Any]] = [f for f in findings if isinstance(f, dict)]

    for finding in typed_findings:
        cpt = str(finding.get("cpt_code") or "?")
        doc = str(finding.get("documentation_support") or "ambiguous").lower()
        evi = str(finding.get("evidence_of_performance") or "ambiguous").lower()
        scores.append(_finding_score(finding))

        if doc == "not_supported" or evi == "not_supported":
            unsupported += 1
            risk_factors.append(f"CPT {cpt}: documentation/evidence not supported")
        elif doc == "ambiguous" or evi == "ambiguous":
            ambiguous += 1
            risk_factors.append(f"CPT {cpt}: ambiguous clinical support")

        severity = str(finding.get("severity_complexity_assessment") or "").strip()
        if severity:
            # Severity text is clinical assessment, not quote-level PHI dumps.
            reasoning_bits.append(f"CPT {cpt}: {severity[:400]}")

        for gap in finding.get("documentation_gaps") or []:
            gap_s = str(gap).strip()
            if gap_s:
                # Short gap labels for Stage 2 / UI — avoid dumping long note excerpts.
                risk_factors.append(f"CPT {cpt} documentation gap: {gap_s[:160]}")

        linked = finding.get("linked_icd_codes") or []
        if isinstance(linked, list) and linked:
            reasoning_bits.append(
                f"CPT {cpt} linked ICD: {', '.join(str(x) for x in linked[:12])}"
            )

    if scores:
        clinical_score = int(round(sum(scores) / len(scores)))
    else:
        # No CPT findings — neutral baseline; summary alone cannot invent certainty.
        clinical_score = 50

    # Thin-note audits: don't treat "can't verify from this note" as medical impossibility.
    # That was collapsing MEDIUM billing scenarios into HIGH fraud via Stage 1 score 25.
    incomplete_chart = _looks_like_insufficient_chart(summary, typed_findings, unsupported)
    if incomplete_chart:
        clinical_score = max(clinical_score, 52)
        clinical_score = min(clinical_score, 62)
        diagnosis_match = "Questionable"
        medical_necessity = "Uncertain"
        risk_factors = [
            "Limited clinical documentation for full CPT audit "
            "(Stage 1 cannot confirm performance from the provided notes)"
        ]
        reasoning_bits.insert(
            0,
            "Clinical audit limited by sparse notes — findings reflect incomplete "
            "chart detail rather than proven medical incompatibility.",
        )
    elif unsupported:
        diagnosis_match = "Incompatible"
        medical_necessity = "Unjustified"
    elif ambiguous:
        diagnosis_match = "Questionable"
        medical_necessity = "Uncertain"
    elif findings:
        diagnosis_match = "Compatible"
        medical_necessity = "Clearly Justified"
    else:
        diagnosis_match = "Unknown"
        medical_necessity = "Unknown"

    reasoning = " ".join(reasoning_bits).strip() or "Local MedGemma clinical audit completed."
    if len(reasoning) > 2500:
        reasoning = reasoning[:2500].rsplit(" ", 1)[0] + "…"

    # Deduplicate flags while preserving order
    seen = set()
    unique_flags: List[str] = []
    for flag in risk_factors:
        if flag not in seen:
            seen.add(flag)
            unique_flags.append(flag)

    return {
        "clinical_legitimacy_score": max(0, min(100, clinical_score)),
        "reasoning": reasoning,
        "risk_factors": unique_flags[:16],
        "diagnosis_procedure_match": diagnosis_match,
        "provider_specialty_appropriate": "Unknown",
        "medical_necessity": medical_necessity,
        "model_used": str(payload.get("model_used") or "medgemma-local"),
        "inference_seconds": payload.get("inference_seconds"),
        "provider": "medgemma_local",
        "incomplete_chart_audit": incomplete_chart,
    }


def _assert_json_response(response: httpx.Response) -> Dict[str, Any]:
    content_type = (response.headers.get("content-type") or "").lower()
    if "application/json" not in content_type:
        raise MedGemmaLocalUpstreamError(
            "upstream returned non-JSON — check ngrok tunnel "
            "(missing ngrok-skip-browser-warning header?)"
        )
    try:
        data = response.json()
    except Exception as exc:
        raise MedGemmaLocalUpstreamError(
            "upstream returned non-JSON — check ngrok tunnel"
        ) from exc
    if not isinstance(data, dict):
        raise MedGemmaLocalUpstreamError("upstream JSON was not an object")
    return data


def health_check(timeout_seconds: float = 5.0) -> Dict[str, Any]:
    """GET /healthz — metadata only; never log URL/key."""
    if not is_configured():
        return {"ok": False, "detail": "MEDGEMMA_LOCAL_* env not configured"}
    try:
        resp = httpx.get(
            f"{_env_base_url()}/healthz",
            headers={
                "X-API-Key": _env_api_key(),
                "ngrok-skip-browser-warning": "true",
            },
            timeout=timeout_seconds,
        )
        if resp.status_code != 200:
            return {"ok": False, "detail": f"healthz status={resp.status_code}"}
        body = _assert_json_response(resp)
        ok = str(body.get("status", "")).lower() in ("ok", "healthy")
        return {"ok": ok, "detail": "healthy" if ok else f"status={body.get('status')}"}
    except MedGemmaLocalUpstreamError as exc:
        return {"ok": False, "detail": str(exc)}
    except Exception as exc:
        return {"ok": False, "detail": f"{type(exc).__name__}"}


def audit_claim(
    data: Dict[str, Any],
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> Dict[str, Any]:
    """
    POST /v1/audit-claim and return Stage-1-shaped dict.

    Raises:
      MedGemmaLocalConfigError: missing env, 401, 422 (no retry)
      MedGemmaLocalUpstreamError: 502, timeout, network, non-JSON (Stage 1 fallback)
    """
    base = _env_base_url()
    key = _env_api_key()
    if not base or not key:
        raise MedGemmaLocalConfigError(
            "MEDGEMMA_LOCAL_BASE_URL / MEDGEMMA_LOCAL_API_KEY not configured"
        )

    body = build_audit_request(data)
    n_icd = len(body["icd_codes"])
    n_cpt = len(body["cpt_codes"])
    notes_len = len(body["clinical_notes"])

    headers = {
        "Content-Type": "application/json",
        "X-API-Key": key,
        "ngrok-skip-browser-warning": "true",
    }

    logger.info(
        "[MedGemma Local] POST /v1/audit-claim "
        f"(icd={n_icd}, cpt={n_cpt}, notes_chars={notes_len}, timeout={timeout_seconds:.0f}s)"
    )

    try:
        resp = httpx.post(
            f"{base}/v1/audit-claim",
            headers=headers,
            json=body,
            timeout=timeout_seconds,
        )
    except httpx.TimeoutException as exc:
        raise MedGemmaLocalUpstreamError("local MedGemma request timed out") from exc
    except httpx.HTTPError as exc:
        raise MedGemmaLocalUpstreamError(
            f"local MedGemma network error: {type(exc).__name__}"
        ) from exc

    if resp.status_code == 401:
        logger.error(
            "[MedGemma Local] 401 Unauthorized — check MEDGEMMA_LOCAL_API_KEY "
            "(config bug; not retrying)"
        )
        raise MedGemmaLocalConfigError("local MedGemma 401 Unauthorized")
    if resp.status_code == 422:
        logger.error(
            "[MedGemma Local] 422 Unprocessable Entity — request schema bug "
            f"(icd={n_icd}, cpt={n_cpt}, notes_chars={notes_len}; not retrying)"
        )
        raise MedGemmaLocalConfigError("local MedGemma 422 Unprocessable Entity")
    if resp.status_code == 502 or resp.status_code >= 500:
        raise MedGemmaLocalUpstreamError(
            f"local MedGemma upstream failure status={resp.status_code}"
        )
    if resp.status_code != 200:
        raise MedGemmaLocalUpstreamError(
            f"local MedGemma unexpected status={resp.status_code}"
        )

    payload = _assert_json_response(resp)
    mapped = map_audit_response_to_stage1(payload)
    logger.info(
        "[MedGemma Local] audit ok "
        f"model_used={mapped.get('model_used')} "
        f"inference_seconds={mapped.get('inference_seconds')} "
        f"clinical_score={mapped.get('clinical_legitimacy_score')} "
        f"flags={len(mapped.get('risk_factors') or [])}"
    )
    return mapped


def try_audit_claim(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Stage 1 helper: return mapped result or None on any failure path
    (config / upstream) so orchestrator can use existing Stage 1 fallback semantics.
    """
    try:
        return audit_claim(data)
    except MedGemmaLocalConfigError as exc:
        logger.error(f"[MedGemma Local] config/client error (no retry): {exc}")
        return None
    except MedGemmaLocalUpstreamError as exc:
        logger.warning(f"[MedGemma Local] upstream failure → Stage 1 fallback: {exc}")
        return None
    except Exception as exc:
        logger.warning(
            f"[MedGemma Local] unexpected {type(exc).__name__} → Stage 1 fallback"
        )
        return None
