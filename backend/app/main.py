from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any
import os
import logging
import asyncio
from contextlib import asynccontextmanager

from .core import LangGraphRouter, RAGEngine
from .core.security import get_huggingface_token
from .llm.orchestrator import LLMClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Block startup until services are ready - prevents 503 on cold start
    # Cloud Run sends traffic as soon as port is open; init takes ~60-90s (Pinecone)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _initialize_services_sync)
    api_deps.set_app_state(app_state)
    yield
    logger.info("Shutting down FraudForge AI...")
    app_state.clear()


app = FastAPI(
    title="FraudForge AI",
    description="Open-source GenAI fraud detection platform",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS: ALLOWED_ORIGINS is a comma-separated allowlist.
# Cloud Run exposes two URL shapes for the same service (hash *.a.run.app and
# project-number *.REGION.run.app). Allow both via regex so browser preflights
# don't 400 when users open either frontend URL.
_allowed_origins = [
    o.strip()
    for o in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if o.strip()
]
_allowed_origin_regex = os.getenv(
    "ALLOWED_ORIGIN_REGEX",
    r"https://fraud-forge-frontend-[\w-]+\.(?:a\.run\.app|[a-z0-9-]+\.run\.app)|http://(localhost|127\.0\.0\.1):\d+",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_origin_regex=_allowed_origin_regex,
    allow_credentials="*" not in _allowed_origins,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app_state: Dict[str, Any] = {}

from .api import deps as api_deps


@app.middleware("http")
async def check_kill_switch(request: Request, call_next):
    if api_deps.KILL_SWITCH_ACTIVE and request.url.path not in [
        "/api/health",
        "/api/status",
        "/health",
        "/",
    ]:
        raise HTTPException(
            status_code=503,
            detail="Service paused: monthly budget limit reached. Contact admin.",
        )
    return await call_next(request)


from .api.v1.router import api_router

app.include_router(api_router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint."""
    return {"service": "FraudForge AI", "docs": "/docs"}


@app.get("/health")
async def health_check_short():
    """Short health check endpoint for load balancers."""
    return {"status": "healthy"}


def _initialize_services_sync():
    global app_state
    logger.info("Initializing FraudForge AI services (background)...")
    try:
        hf_token = get_huggingface_token()
        hf_client = LLMClient(hf_token) if hf_token else None
        rag_engine = RAGEngine(namespace="rag")
        rag_engine.initialize()
        langgraph_router = LangGraphRouter(rag_engine, hf_client=hf_client)

        app_state.update(
            {
                "rag_engine": rag_engine,
                "router": langgraph_router,
                "hf_client": hf_client,
            }
        )
        logger.info("FraudForge AI ready!")
    except Exception as e:
        logger.error(f"Initialization failed: {e}", exc_info=True)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8080)),
        reload=True,
    )
