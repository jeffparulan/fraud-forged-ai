"""Fraud detection endpoint."""
import time
import logging
from fastapi import APIRouter, Depends, HTTPException

from app.models.request import FraudDetectionRequest
from app.api.security import require_api_key, enforce_rate_limit

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/detect", dependencies=[Depends(require_api_key), Depends(enforce_rate_limit)])
async def detect_fraud(request: FraudDetectionRequest):
    """
    Main fraud detection endpoint.
    Uses LangGraph router with RAG-enhanced LLM analysis.
    """
    from app.api.deps import get_app_state

    start_time = time.time()
    app_state = get_app_state()

    if "router" not in app_state:
        raise HTTPException(
            status_code=503,
            detail="Service is still initializing. Please try again in a moment."
        )

    langgraph_router = app_state["router"]

    try:
        result = await langgraph_router.route_and_analyze(
            sector=request.sector,
            data=request.data
        )

        processing_time_ms = int((time.time() - start_time) * 1000)

        return {
            "fraud_score": result["fraud_score"],
            "risk_level": result["risk_level"],
            "explanation": result["explanation"],
            "model_used": result["model_used"],
            "processing_time_ms": processing_time_ms,
            "similar_patterns": result.get("similar_patterns", 0),
            "risk_factors": result.get("risk_factors", []),
            "score_breakdown": result.get("score_breakdown", []),
            "decision_trace": result.get("decision_trace", []),
            "pipeline_meta": result.get("pipeline_meta", {}),
        }

    except HTTPException:
        raise
    except Exception as e:
        # Log full detail server-side; never leak internals to the client
        logger.error(f"Fraud detection error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Fraud detection failed due to an internal error. Please try again."
        )
