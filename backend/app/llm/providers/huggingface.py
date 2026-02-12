"""
Hugging Face Inference API provider.

Handles HF Inference API calls with retry logic, rate limiting,
and support for both chat_completion and text_generation APIs.
"""
from typing import Dict, Any, Optional
import time
import logging
import inspect
import os
from huggingface_hub import InferenceClient

from .base import BaseLLMProvider

logger = logging.getLogger(__name__)

# Toggleable verbose logging
LOG_STAGE1_VERBOSE = os.getenv("LOG_STAGE1_VERBOSE", "0").lower() in ("1", "true", "yes")


class HuggingFaceProvider(BaseLLMProvider):
    """
    Hugging Face Inference API provider.
    
    Supports both chat_completion and text_generation APIs with:
    - Automatic fallback between APIs
    - Rate limit retry with exponential backoff
    - Special handling for chat-only models (Qwen)
    """
    
    def __init__(self, api_token: Optional[str] = None):
        super().__init__(api_token)
        self.client = InferenceClient(token=api_token)
        self.max_retries = 3
        self.base_delay = 2.0
        
        # Models that don't support chat_completion
        self.models_no_chat = [
            "instruction-pretrain/finance-Llama3-8B",
            "meta-llama/Llama-3.1-8B-Instruct",
            "mistralai/Mistral-7B-Instruct-v0.2"
        ]
        
        # Models that ONLY support chat_completion (never use text_generation)
        self.models_chat_only = ["qwen", "Qwen"]
    
    async def generate(
        self,
        model_name: str,
        prompt: str,
        sector: str,
        data: Dict[str, Any],
        is_clinical_stage: bool = False,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Generate response from Hugging Face model.
        
        Tries chat_completion first, falls back to text_generation if needed.
        Implements retry logic for rate limiting (429 errors).
        """
        skip_chat = any(no_chat in model_name for no_chat in self.models_no_chat)
        chat_only = any(chat_only_model in model_name for chat_only_model in self.models_chat_only)
        
        # Try chat_completion first (unless we know it doesn't work)
        if not skip_chat:
            result = await self._try_chat_completion(
                model_name, prompt, sector, data, is_clinical_stage, chat_only
            )
            if result:
                return result
        
        # Fall back to text_generation (only if model is NOT chat-only)
        if chat_only:
            logger.error(f"❌ Chat-only model {model_name} failed chat_completion, cannot fall back")
            raise ValueError(f"Model {model_name} only supports chat_completion")
        
        return await self._try_text_generation(model_name, prompt, sector, data, is_clinical_stage)
    
    async def _try_chat_completion(
        self,
        model_name: str,
        prompt: str,
        sector: str,
        data: Dict[str, Any],
        is_clinical_stage: bool,
        chat_only: bool
    ) -> Optional[Dict[str, Any]]:
        """Try chat_completion API with retry logic."""
        for attempt in range(self.max_retries):
            try:
                logger.info(f"  → Attempting chat_completion with {model_name} (attempt {attempt + 1}/{self.max_retries})...")
                messages = [{"role": "user", "content": prompt}]
                
                response = self.client.chat_completion(
                    messages=messages,
                    model=model_name,
                    max_tokens=512,
                    temperature=0.5,
                    stream=False
                )
                
                generated_text = response.choices[0].message.content
                
                # Log full response if verbose logging enabled
                if LOG_STAGE1_VERBOSE and not is_clinical_stage:
                    logger.info("=" * 80)
                    logger.info(f"📥 [Stage 2] FULL RESPONSE FROM {model_name}:")
                    logger.info("=" * 80)
                    logger.info(f"{str(generated_text)}")
                    logger.info("=" * 80)
                else:
                    logger.info(f"✅ HF API success (chat) with {model_name}! Response: {str(generated_text)[:200]}...")
                
                return self._parse_response(str(generated_text), sector, data, is_clinical_stage)
            
            except Exception as chat_error:
                error_str = str(chat_error).lower()
                status_code = getattr(chat_error, 'status_code', None)
                
                logger.warning(f"⚠️  Chat completion error on attempt {attempt + 1}/{self.max_retries}: {type(chat_error).__name__}: {str(chat_error)[:200]}")
                
                # Handle 400 Bad Request
                if status_code == 400 or "400" in error_str or "bad request" in error_str:
                    if chat_only:
                        # Qwen models ONLY support chat - retry
                        if attempt < self.max_retries - 1:
                            delay = self.base_delay * (attempt + 1)
                            logger.info(f"  → Waiting {delay:.1f}s before retry...")
                            time.sleep(delay)
                            continue
                        else:
                            logger.error(f"❌ Chat completion failed for {model_name} after {self.max_retries} attempts")
                            raise ValueError(f"Model {model_name} chat_completion failed after {self.max_retries} attempts")
                    else:
                        # Non-chat-only model - can fall back to text_generation
                        logger.debug(f"  → Model {model_name} doesn't support chat_completion (400), will try text_generation")
                        return None  # Signal to try text_generation
                
                # Handle rate limiting
                is_rate_limit = (
                    status_code == 429 or
                    "429" in error_str or
                    "rate limit" in error_str or
                    "too many requests" in error_str
                )
                
                if is_rate_limit and attempt < self.max_retries - 1:
                    delay = self.base_delay * (2 ** attempt)
                    logger.warning(f"⚠️  Rate limit (429), retrying in {delay:.1f}s...")
                    time.sleep(delay)
                    continue
                
                # Final attempt failed
                if attempt == self.max_retries - 1:
                    if chat_only:
                        logger.error(f"❌ Chat completion failed for {model_name} after {self.max_retries} attempts")
                        raise ValueError(f"Model {model_name} chat_completion failed")
                    else:
                        logger.debug(f"  → chat_completion failed, will try text_generation")
                        return None  # Signal to try text_generation
        
        return None
    
    async def _try_text_generation(
        self,
        model_name: str,
        prompt: str,
        sector: str,
        data: Dict[str, Any],
        is_clinical_stage: bool
    ) -> Optional[Dict[str, Any]]:
        """Try text_generation API with retry logic."""
        logger.info(f"  → Using text_generation API with {model_name}...")
        
        for attempt in range(self.max_retries):
            try:
                result = self.client.text_generation(
                    prompt,
                    model=model_name,
                    max_new_tokens=512,
                    temperature=0.5,
                    return_full_text=False
                )
                
                # Handle different response types
                if inspect.isgenerator(result) or (hasattr(result, '__iter__') and not isinstance(result, (str, bytes))):
                    generated_text = ''.join(str(chunk) for chunk in result)
                elif hasattr(result, 'generated_text'):
                    generated_text = result.generated_text
                elif isinstance(result, str):
                    generated_text = result
                else:
                    generated_text = str(result)
                
                logger.info(f"✅ HF API success (text_generation) with {model_name}! Response: {str(generated_text)[:200]}...")
                
                return self._parse_response(str(generated_text), sector, data, is_clinical_stage)
            
            except Exception as text_error:
                text_error_str = str(text_error).lower()
                status_code = getattr(text_error, 'status_code', None)
                
                is_rate_limit = (
                    status_code == 429 or
                    "429" in text_error_str or
                    "rate limit" in text_error_str or
                    "too many requests" in text_error_str
                )
                
                if is_rate_limit and attempt < self.max_retries - 1:
                    delay = self.base_delay * (2 ** attempt)
                    logger.warning(f"⚠️  Rate limit (429) on text_generation attempt {attempt + 1}, retrying in {delay:.1f}s...")
                    time.sleep(delay)
                    continue
                
                # Final attempt failed
                if attempt == self.max_retries - 1:
                    logger.error(f"❌ text_generation failed after {self.max_retries} attempts: {type(text_error).__name__}: {str(text_error)}")
                    return None
        
        return None
