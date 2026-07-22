"""Model metadata and availability endpoints — backed by app/llm/models.yaml."""
from typing import Dict, Any

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_app_state
from app.llm.config import (
    SECTOR_MODELS,
    get_sector_model_candidates,
    build_models_summary,
)
from app.llm.orchestrator import LLMClient

router = APIRouter()


def _get_or_create_llm_client(app_state: Dict[str, Any]) -> LLMClient:
    """Use initialized LLM client when available, otherwise create an ad-hoc one."""
    client = app_state.get("hf_client")
    if client:
        return client
    return LLMClient()


@router.get("/models")
async def get_models(state: Dict[str, Any] = Depends(get_app_state)):
    """
    Get all configured fraud-detection models by sector (from models.yaml).

    Returns:
    - **summary**: human-readable display names per sector (primary + fallbacks)
    - **candidates**: ordered model candidate list with provider/role metadata
    - **readiness**: provider readiness based on environment variable configuration
    """
    llm_client = _get_or_create_llm_client(state)
    readiness = llm_client.get_model_availability_report(live_test=False)

    return {
        "summary": build_models_summary(),
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
