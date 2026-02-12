"""API request schemas."""
from pydantic import BaseModel, Field
from typing import Dict, Any, Literal


class FraudDetectionRequest(BaseModel):
    """Request body for fraud detection endpoint."""
    sector: Literal["banking", "medical", "ecommerce", "supply_chain"] = Field(
        ..., description="Industry sector for fraud detection"
    )
    data: Dict[str, Any] = Field(
        ..., description="Transaction or claim data to analyze"
    )
