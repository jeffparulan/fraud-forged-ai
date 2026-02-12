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
