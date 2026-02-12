"""Main API router - aggregates all v1 endpoints."""
from fastapi import APIRouter

from app.api.v1.endpoints import detect, health, models

api_router = APIRouter()

# Include endpoints
api_router.include_router(health.router, tags=["health"])
api_router.include_router(detect.router, tags=["detect"])
api_router.include_router(models.router, tags=["models"])
