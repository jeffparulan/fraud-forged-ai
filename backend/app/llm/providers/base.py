"""
Abstract base class for LLM providers.

Implements the Strategy Pattern - all providers implement a common interface,
making them swappable and testable independently.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class BaseLLMProvider(ABC):
    """
    Abstract base class for all LLM providers.
    
    Each provider (HuggingFace, OpenRouter, HF Spaces, etc.) implements
    this interface, allowing them to be used interchangeably.
    """
    
    def __init__(self, api_token: Optional[str] = None):
        """
        Initialize the provider with optional API token.
        
        Args:
            api_token: API key/token for authentication
        """
        self.api_token = api_token
        self.provider_name = self.__class__.__name__.replace("Provider", "").lower()
    
    @abstractmethod
    async def generate(
        self,
        model_name: str,
        prompt: str,
        sector: str,
        data: Dict[str, Any],
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a response from the LLM.
        
        Args:
            model_name: Model identifier (e.g., "Qwen/Qwen2.5-72B-Instruct")
            prompt: The formatted prompt text
            sector: Fraud detection sector (banking, medical, ecommerce, supply_chain)
            data: Original transaction/claim/order data
            **kwargs: Provider-specific parameters
        
        Returns:
            Dict with fraud analysis results or None if failed:
            {
                "fraud_score": float (0-100),
                "risk_level": str (LOW/MEDIUM/HIGH/CRITICAL),
                "explanation": str,
                "reasoning": str,
                "model_used": str,
                "provider": str
            }
        """
        pass
    
    def _parse_response(
        self,
        response_text: str,
        sector: str,
        data: Dict[str, Any],
        is_clinical_stage: bool = False
    ) -> Dict[str, Any]:
        """
        Parse LLM response text into structured fraud analysis.
        
        This method can be overridden by specific providers if they need
        custom parsing logic.
        
        Args:
            response_text: Raw text response from LLM
            sector: Fraud detection sector
            data: Original transaction data
            is_clinical_stage: Whether this is Stage 1 of medical pipeline
        
        Returns:
            Parsed fraud analysis dictionary
        """
        # Import here to avoid circular dependency
        from ..response_parser import parse_model_response
        return parse_model_response(response_text, sector, data, is_clinical_stage)
    
    def _get_risk_level(self, fraud_score: float) -> str:
        """Calculate risk level from fraud score."""
        if fraud_score < 30:
            return 'LOW'
        elif fraud_score < 60:
            return 'MEDIUM'
        elif fraud_score < 85:
            return 'HIGH'
        else:
            return 'CRITICAL'
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"
