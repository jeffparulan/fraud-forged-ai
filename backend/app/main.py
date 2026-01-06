from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, Literal
import time
import os
import logging
import asyncio
from threading import Thread
from contextlib import asynccontextmanager
import base64
import json

# Your internal modules
from .langgraph_router import LangGraphRouter
from .rag_engine import RAGEngine
from .utils.secrets import get_huggingface_token
from .utils.llm_client import LLMClient

# ----------------------------
# FastAPI App + Lifespan
# ----------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    Thread(target=_initialize_services_background, daemon=True).start()
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
KILL_SWITCH_ACTIVE = False

@app.middleware("http")
async def check_kill_switch(request: Request, call_next):
    if KILL_SWITCH_ACTIVE and request.url.path not in ["/api/health", "/api/status", "/health", "/"]:
        raise HTTPException(
            status_code=503,
            detail="Service paused: monthly budget limit reached. Contact admin."
        )
    response = await call_next(request)
    return response

@app.get("/api/health")
async def health_check():
    """Health check endpoint for Docker and load balancers"""
    return {"status": "healthy", "service": "FraudForge AI Backend"}

@app.get("/health")
async def health_check_short():
    """Short health check endpoint"""
    return {"status": "healthy"}

@app.get("/api/status")
async def get_status():
    return {
        "status": "maintenance" if KILL_SWITCH_ACTIVE else "operational",
        "message": "Budget limit reached - service paused" if KILL_SWITCH_ACTIVE else "All systems operational"
    }

# ----------------------------
# Fraud Detection Endpoint
# ----------------------------
class FraudDetectionRequest(BaseModel):
    sector: Literal["banking", "medical", "ecommerce", "supply_chain"] = Field(
        ..., description="Industry sector for fraud detection"
    )
    data: Dict[str, Any] = Field(..., description="Transaction or claim data to analyze")

@app.post("/api/detect")
async def detect_fraud(request: FraudDetectionRequest):
    """
    Main fraud detection endpoint.
    Uses LangGraph router with RAG-enhanced LLM analysis.
    """
    start_time = time.time()
    
    try:
        # Check if services are initialized
        if "router" not in app_state:
            raise HTTPException(
                status_code=503,
                detail="Service is still initializing. Please try again in a moment."
            )
        
        router = app_state["router"]
        
        # Execute fraud detection workflow
        result = await router.route_and_analyze(
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
            "risk_factors": result.get("risk_factors", [])
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fraud detection error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Fraud detection failed: {str(e)}"
        )

@app.get("/api/models")
async def get_models():
    """Get available fraud-specialized AI models for each sector (Cost-Optimized 2025)"""
    return {
        "banking": "Qwen/Qwen2.5-72B-Instruct (HF Pro - Financial Reasoning)",
        "medical": "Qwen/Qwen2.5-32B-Instruct (HF Pro - Billing Pattern Analysis)",
        "ecommerce": "Nemotron-2 (12B VL) (FREE - Marketplace Fraud Detection)",
        "supply_chain": "Nemotron-2 (12B VL) (FREE - Logistics Fraud Detection)"
    }

# ----------------------------
# Background Initialization (unchanged)
# ----------------------------
def _initialize_services_background():
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
    global KILL_SWITCH_ACTIVE

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
        if not KILL_SWITCH_ACTIVE:
            logger.warning("BUDGET EXCEEDED → ACTIVATING KILL SWITCH & SCALING CLOUD RUN TO 0")
            KILL_SWITCH_ACTIVE = True

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