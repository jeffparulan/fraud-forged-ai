"""Model info endpoint."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/models")
async def get_models():
    """Get available fraud-specialized AI models for each sector (Cost-Optimized 2025)."""
    return {
        "banking": "Qwen/Qwen2.5-72B-Instruct (HF Pro - Financial Reasoning)",
        "medical": "Qwen/Qwen2.5-32B-Instruct (HF Pro - Billing Pattern Analysis)",
        "ecommerce": "Nemotron-2 (12B VL) (FREE - Marketplace Fraud Detection)",
        "supply_chain": "Nemotron-2 (12B VL) (FREE - Logistics Fraud Detection)"
    }
