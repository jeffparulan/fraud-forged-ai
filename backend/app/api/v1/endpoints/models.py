"""Model metadata and availability endpoints."""
from typing import Dict, Any, List

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_app_state
from app.llm.config import SECTOR_MODELS, get_sector_model_candidates
from app.llm.orchestrator import LLMClient, _format_model_name

router = APIRouter()

# Human-readable sector labels
SECTOR_LABELS: Dict[str, str] = {
    "banking": "Banking & Crypto",
    "medical": "Healthcare & Medical Claims",
    "ecommerce": "E-commerce & Marketplace",
    "supply_chain": "Supply Chain & Logistics",
}


def _get_or_create_llm_client(app_state: Dict[str, Any]) -> LLMClient:
    """Use initialized LLM client when available, otherwise create an ad-hoc one."""
    client = app_state.get("hf_client")
    if client:
        return client
    return LLMClient()


def _build_summary() -> Dict[str, Any]:
    """Build a concise human-readable model summary keyed by sector."""
    summary: Dict[str, Any] = {}
    for sector, cfg in SECTOR_MODELS.items():
        label = SECTOR_LABELS.get(sector, sector)
        if cfg.get("two_stage"):
            s1 = cfg["stage1"]
            s2 = cfg["stage2"]
            primary_display = (
                f"{_format_model_name(s1['model'], s1['provider'], False, None)}"
                f" → {_format_model_name(s2['model'], s2['provider'], False, None)}"
            )
            pipeline = "two-stage"
        else:
            p = cfg["primary"]
            primary_display = _format_model_name(p["model"], p["provider"], False, None)
            pipeline = "single-stage"

        fallback_displays: List[str] = [
            _format_model_name(f["model"], f["provider"], True, i + 1)
            for i, f in enumerate(cfg.get("fallbacks", []))
        ]

        summary[sector] = {
            "label": label,
            "pipeline": pipeline,
            "primary": primary_display,
            "fallbacks": fallback_displays,
        }
    return summary


@router.get("/models")
async def get_models(state: Dict[str, Any] = Depends(get_app_state)):
    """
    Get all configured fraud-detection models by sector.

    Returns:
    - **summary**: human-readable display names per sector (primary + fallbacks)
    - **candidates**: ordered model candidate list with provider/role metadata
    - **readiness**: provider readiness based on environment variable configuration
    """
    llm_client = _get_or_create_llm_client(state)
    readiness = llm_client.get_model_availability_report(live_test=False)

    return {
        "summary": _build_summary(),
        "candidates": {
            sector: get_sector_model_candidates(sector) for sector in SECTOR_MODELS.keys()
        },
        "readiness": readiness,
    }


@router.get("/models/availability")
async def get_model_availability(
    live_test: bool = Query(
        default=False,
        description="If true, performs lightweight provider calls to verify model reachability.",
    ),
    state: Dict[str, Any] = Depends(get_app_state),
):
    """Get model availability report; optional live probe verifies that models are reachable."""
    llm_client = _get_or_create_llm_client(state)
    return llm_client.get_model_availability_report(live_test=live_test)
