"""Prompt templates for fraud detection."""
from .base_prompts import build_rag_section
from .banking_prompts import build_banking_prompt
from .medical_prompts import build_medical_prompt, build_stage1_clinical_prompt, build_stage2_fraud_prompt
from .ecommerce_prompts import build_ecommerce_prompt
from .supply_chain_prompts import build_supply_chain_prompt
from typing import Dict, Any, Optional, List


def build_prompt(sector: str, data: Dict[str, Any], rag_context: Optional[str] = None) -> str:
    """Build fraud detection prompt for the given sector."""
    if sector == "banking":
        return build_banking_prompt(data, rag_context)
    elif sector == "medical":
        return build_medical_prompt(data, rag_context)
    elif sector == "ecommerce":
        return build_ecommerce_prompt(data, rag_context)
    elif sector == "supply_chain":
        return build_supply_chain_prompt(data, rag_context)
    return ""


__all__ = [
    "build_rag_section",
    "build_banking_prompt",
    "build_medical_prompt",
    "build_stage1_clinical_prompt",
    "build_stage2_fraud_prompt",
    "build_ecommerce_prompt",
    "build_supply_chain_prompt",
    "build_prompt",
]
