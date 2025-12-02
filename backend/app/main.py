from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, Literal
import time
import os
import logging
import asyncio
from threading import Thread
from contextlib import asynccontextmanager

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
    # Startup: fire and forget background init
    Thread(target=_initialize_services_background, daemon=True).start()
    yield
    # Shutdown
    logger.info("Shutting down FraudForge AI...")
    app_state.clear()


app = FastAPI(
    title="FraudForge AI",
    description="Open-source GenAI fraud detection platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS — permanently allow all (this is a public demo API)
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
kill_switch_active = False
app_state: Dict[str, Any] = {}


# ----------------------------
# Background Initialization
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
        app_state.update({"rag_engine": None, "router": None, "hf_client": None})


# ----------------------------
# Models
# ----------------------------
class FraudDetectionRequest(BaseModel):
    sector: Literal["banking", "medical", "ecommerce", "supply_chain"]
    data: Dict[str, Any]

class FraudDetectionResponse(BaseModel):
    fraud_score: float
    risk_level: str
    explanation: str
    model_used: str
    processing_time_ms: int
    similar_patterns: Optional[int] = None


# ----------------------------
# Routes
# ----------------------------
@app.get("/")
async def root():
    return {"service": "FraudForge AI", "status": "running", "version": "1.0.0"}

@app.get("/api/health")
async def health_check():
    components = {
        "rag_engine": "ready" if app_state.get("rag_engine") else "initializing",
        "router": "ready" if app_state.get("router") else "initializing"
    }
    return {
        "status": "healthy",
        "kill_switch": kill_switch_active,
        "components": components,
        "timestamp": time.time()
    }

@app.post("/api/detect", response_model=FraudDetectionResponse)
async def detect_fraud(request: FraudDetectionRequest):
    if kill_switch_active:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")

    # Wait max 60s for router
    for _ in range(600):
        if app_state.get("router"):
            break
        await asyncio.sleep(0.1)
    else:
        raise HTTPException(status_code=503, detail="Service still initializing")

    start = time.time()
    result = await app_state["router"].route_and_analyze(request.sector, request.data)
    processing_time_ms = int((time.time() - start) * 1000)

    return FraudDetectionResponse(
        fraud_score=result["fraud_score"],
        risk_level=result["risk_level"],
        explanation=result["explanation"],
        model_used=result["model_used"],
        processing_time_ms=processing_time_ms,
        similar_patterns=result.get("similar_patterns")
    )

@app.get("/api/models")
async def list_models():
    return {
        "banking": {"model": "FinGPT"},
        "medical": {"model": "MedGemma"},
        "ecommerce": {"model": "Nemotron Nano"},
        "audit": {"model": "Phi-3-small-audit-tuned"}
    }

# Optional: keep your internal kill-switch if you want
@app.post("/api/internal/killswitch")
async def toggle_kill_switch(state: Literal["on", "off"], admin_key: str = Query(...)):
    if admin_key != os.getenv("ADMIN_KEY", "change-this-in-production"):
        raise HTTPException(status_code=403, detail="Unauthorized")
    global kill_switch_active
    kill_switch_active = (state == "on")
    return {"status": "success", "kill_switch": kill_switch_active}


# ----------------------------
# Local dev only
# ----------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8080)), reload=True)