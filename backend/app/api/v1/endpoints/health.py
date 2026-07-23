"""Health check endpoints."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint for Docker and load balancers."""
    return {"status": "healthy", "service": "FraudForge AI Backend"}


@router.get("/status")
async def get_status():
    """Get service status (including kill switch state)."""
    from app.api.deps import KILL_SWITCH_ACTIVE
    return {
        "status": "maintenance" if KILL_SWITCH_ACTIVE else "operational",
        "message": "Budget limit reached - service paused" if KILL_SWITCH_ACTIVE else "All systems operational"
    }


@router.get("/providers/medgemma-local")
async def medgemma_local_health():
    """
    Probe local MedGemma /healthz (Mac Mini via ngrok).
    Never returns the base URL or API key — only ok/detail metadata.
    """
    from app.llm.medgemma_local import health_check, is_configured

    if not is_configured():
        return {
            "ok": False,
            "configured": False,
            "detail": "MEDGEMMA_LOCAL_* env not configured",
        }
    result = health_check()
    return {
        "ok": bool(result.get("ok")),
        "configured": True,
        "detail": result.get("detail", "unknown"),
    }
