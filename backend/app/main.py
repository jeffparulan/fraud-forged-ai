from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any
import os
import logging
import asyncio
from contextlib import asynccontextmanager
import base64
import json

# Your internal modules
from .core import LangGraphRouter, RAGEngine
from .core.security import get_huggingface_token
from .llm.orchestrator import LLMClient

# ----------------------------
# FastAPI App + Lifespan
# ----------------------------
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
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global state
app_state: Dict[str, Any] = {}

# ----------------------------
# Kill Switch - Controlled by budget Pub/Sub
# ----------------------------
from .api import deps as api_deps

@app.middleware("http")
async def check_kill_switch(request: Request, call_next):
    if api_deps.KILL_SWITCH_ACTIVE and request.url.path not in ["/api/health", "/api/status", "/health", "/"]:
        raise HTTPException(
            status_code=503,
            detail="Service paused: monthly budget limit reached. Contact admin."
        )
    response = await call_next(request)
    return response

# Include API routes from api/v1
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

# ----------------------------
# Service Initialization (runs at startup, blocks until ready)
# ----------------------------
def _initialize_services_sync():
    global app_state
    logger.info("Initializing FraudForge AI services (background)...")
    try:
        hf_token = get_huggingface_token()
        hf_client = LLMClient(hf_token) if hf_token else None
        rag_engine = RAGEngine(namespace="rag")
        rag_engine.initialize()
        langgraph_router = LangGraphRouter(rag_engine, hf_client=hf_client)

        app_state.update({
            "rag_engine": rag_engine,
            "router": langgraph_router,
            "hf_client": hf_client
        })
        logger.info("FraudForge AI ready!")
    except Exception as e:
        logger.error(f"Initialization failed: {e}", exc_info=True)



# ----------------------------
# BUDGET ALERT HANDLER — This is the new part
# This function runs when your $5 budget is breached
# ----------------------------
def process_budget_alert(event, context):
    """Background Cloud Function to be triggered by Pub/Sub budget alerts."""
    logger.info(f"Received budget alert event ID: {context.event_id}")

    # Decode the Pub/Sub message
    if 'data' not in event:
        logger.warning("No data in event")
        return

    message_data = base64.b64decode(event['data']).decode('utf-8')
    payload = json.loads(message_data)

    cost = float(payload.get("costAmount", 0))
    budget = float(payload.get("budgetAmount", 0))
    threshold = payload.get("alertThresholdExceeded", 0)

    logger.info(f"Budget alert: cost=${cost}, budget=${budget}, threshold={threshold}")

    # Only act when we actually exceed the budget (100%+)
    if cost >= budget:
        if not api_deps.KILL_SWITCH_ACTIVE:
            logger.warning("BUDGET EXCEEDED → ACTIVATING KILL SWITCH & SCALING CLOUD RUN TO 0")
            api_deps.set_kill_switch(True)

            # Optional: instantly scale your Cloud Run services to 0 (production only)
            project_id = os.getenv("PROJECT_ID")
            region = os.getenv("REGION", "us-central1")
            backend_service = os.getenv("BACKEND_SERVICE", "fraud-forge-backend")

            # Only try to scale if we're in production (not local-dev)
            if project_id and project_id != "local-dev":
                try:
                    from google.cloud import run_v2
                    client = run_v2.ServicesClient()
                    service_name = f"projects/{project_id}/locations/{region}/services/{backend_service}"

                    request = run_v2.UpdateServiceRequest(
                        service=run_v2.Service(
                            name=service_name,
                            template=run_v2.RevisionTemplate(
                                scaling=run_v2.RevisionScaling(min_instance_count=0)
                            )
                        )
                    )
                    operation = client.update_service(request)
                    operation.result()  # wait for completion
                    logger.info(f"Scaled {backend_service} to 0 instances")
                except ImportError:
                    logger.warning("Google Cloud Run client not available (local dev mode)")
                except Exception as e:
                    logger.error(f"Failed to scale down Cloud Run: {e}")
            else:
                logger.info("Local dev mode - skipping Cloud Run scaling")

        else:
            logger.info("Kill switch already active")
    else:
        logger.info("Budget alert received but not exceeded yet")

# ----------------------------
# Local dev only
# ----------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8080)), reload=True)