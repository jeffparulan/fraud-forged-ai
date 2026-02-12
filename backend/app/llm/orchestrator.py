"""
Unified LLM client for fraud detection with multi-provider support.

Orchestrates: config, ofac, prompts, parsing, prechecks, providers.
"""
import os
import logging
import time
from typing import Dict, Any, Optional, List

import httpx
from huggingface_hub import InferenceClient

from .config import SECTOR_MODELS, SECTOR_LOCATION_FIELDS
from .ofac import check_ofac_in_data
from .prompts import build_prompt, build_stage1_clinical_prompt, build_stage2_fraud_prompt
from .parsing import parse_model_response, get_risk_level
from .prechecks import check_extreme_fraud_patterns

logger = logging.getLogger(__name__)

LOG_STAGE1_VERBOSE = os.getenv("LOG_STAGE1_VERBOSE", "0").lower() in ("1", "true", "yes")

try:
    from gradio_client import Client
    GRADIO_AVAILABLE = True
except ImportError:
    GRADIO_AVAILABLE = False
    logger.warning("gradio_client not installed - HF Space calls will fail. Install: pip install gradio_client")

class LLMClient:
    """
    Multi-provider LLM client for fraud detection with cost-optimized model alignment.
    
    ARCHITECTURE:
    - Single-stage: Banking, E-commerce, Supply Chain use one LLM call
    - Two-stage: Medical uses sequential MedGemma (clinical) → Qwen (fraud) pipeline
    
    MODEL SELECTION:
    - Banking: Qwen2.5-72B (HF Inference API) - Financial reasoning, AML patterns
    - Medical: TWO-STAGE
      ├─ Stage 1: MedGemma-4B-IT (HF Space) - Clinical legitimacy validation
      └─ Stage 2: Qwen2.5-72B (HF Inference API) - Fraud pattern analysis
    - E-commerce: Nemotron-2 12B VL (OpenRouter FREE) - Visual reasoning, marketplace dynamics
    - Supply Chain: Nemotron-2 12B VL (OpenRouter FREE) - Temporal reasoning, logistics
    
    FALLBACK CHAIN:
    - All sectors: Nemotron-3-Nano-30B (OpenRouter FREE) as primary fallback
    - Medical: MedGemma (Vertex AI) as specialized clinical fallback
    - Banking: Llama-3.1-70B (OpenRouter FREE) as additional fallback
    
    COST OPTIMIZATION:
    - Pre-checks (OFAC, extreme values) bypass expensive LLM calls
    - HF Pro: $9/month (already subscribed) for Banking/Medical
    - OpenRouter FREE: $0/month for E-commerce/Supply Chain
    - Total incremental cost: $0/month
    """
    
    def __init__(self, api_token: Optional[str] = None):
        self.api_token = api_token or os.getenv('HUGGINGFACE_API_TOKEN')
        if not self.api_token:
            logger.warning("No Hugging Face API token provided - HF fallback models will fail")
        
        # Hugging Face router client (for fallback models)
        self.client = InferenceClient(token=self.api_token)
        logger.info("✅ InferenceClient initialized (HF fallback endpoint)")

        # OpenRouter configuration (primary provider for all sectors)
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.openrouter_api_key:
            logger.warning("⚠️  No OPENROUTER_API_KEY - PRIMARY models unavailable (Qwen3, DeepSeek, Nemotron)")
        else:
            logger.info("✅ OpenRouter configured (primary provider for fraud-specialized models)")

    def analyze_fraud(self, sector: str, data: Dict[str, Any], rag_context: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze fraud using sector-specific model with fallback support across providers.
        
        COST OPTIMIZATION: Pre-checks for OFAC countries before LLM calls to save inference costs.
        If OFAC country detected + other red flags, returns high score immediately without LLM.
        
        Args:
            sector: One of 'banking', 'medical', 'ecommerce', 'supply_chain'
            data: Transaction/claim data to analyze
            rag_context: Optional RAG context from similar fraud patterns
        
        Returns:
            Dict with 'score', 'reasoning', 'risk_factors'
        """
        model_config = SECTOR_MODELS.get(sector)
        if not model_config:
            raise ValueError(f"Unknown sector: {sector}")
        
        # ============================================================
        # TWO-STAGE PROCESSING (MEDICAL CLAIMS ONLY)
        # ============================================================
        # Medical claims use a two-stage pipeline:
        # Stage 1: MedGemma (clinical legitimacy validation)
        # Stage 2: Qwen (fraud pattern analysis using Stage 1 output)
        
        if model_config.get("two_stage"):
            logger.info(f"🏥 [Two-Stage] {sector} sector using two-stage pipeline")
            return self._analyze_two_stage(sector, data, rag_context, model_config)

        # ============================================================
        # UNIVERSAL FRAUD PRE-CHECKS (ALL INDUSTRIES)
        # ============================================================
        # Check for extreme/impossible values BEFORE expensive LLM calls
        # Examples: 1000x price markup, negative amounts, impossible ages
        
        extreme_fraud = check_extreme_fraud_patterns(sector, data)
        if extreme_fraud:
            logger.info(f"🚨 [Extreme Fraud] Pre-check triggered - skipping LLM call")
            return extreme_fraud
        
        # ============================================================
        # COST-EFFICIENT PRE-CHECK: OFAC Country Detection
        # ============================================================
        # Check for OFAC countries BEFORE expensive LLM calls
        # This saves money on clear-cut cases (deterministic string matching)
        
        location_fields = SECTOR_LOCATION_FIELDS.get(sector, [])
        has_ofac, ofac_countries = check_ofac_in_data(data, location_fields)
        
        if has_ofac:
            # OFAC country detected - check for additional red flags
            red_flags_count = 0
            risk_factors = [f"OFAC sanctioned/high-risk country: {', '.join(ofac_countries)}"]
            
            # Check for VPN/proxy
            ip_address = str(data.get("ip_address", "")).lower()
            if "vpn" in ip_address or "proxy" in ip_address or "tor" in ip_address:
                red_flags_count += 1
                risk_factors.append("VPN/Proxy/TOR detected")
            
            # Check for unverified accounts (sector-specific)
            if sector == "banking":
                if not data.get("kyc_verified", False):
                    red_flags_count += 1
                    risk_factors.append("Unverified KYC")
            elif sector == "ecommerce":
                if not data.get("email_verified", False):
                    red_flags_count += 1
                    risk_factors.append("Unverified email")
            elif sector == "supply_chain":
                if not data.get("documentation_complete", False):
                    red_flags_count += 1
                    risk_factors.append("Missing documentation")
            
            # Check for new accounts/sellers/suppliers
            age_field = {
                "banking": "account_age_days",
                "ecommerce": "seller_age_days",
                "supply_chain": "supplier_age_days"
            }.get(sector)
            
            if age_field and data.get(age_field, 365) < 30:
                red_flags_count += 1
                risk_factors.append(f"New {sector.replace('_', ' ')} (< 30 days)")
            
            # If OFAC + 2+ other red flags, return immediately (save LLM costs)
            if red_flags_count >= 2:
                base_score = 75  # HIGH risk base for OFAC
                score_bonus = min(red_flags_count * 5, 20)  # Up to +20 for additional flags
                fraud_score = min(base_score + score_bonus, 100)
                
                risk_level = "HIGH" if fraud_score < 85 else "CRITICAL"
                
                countries_str = ", ".join(ofac_countries)
                reasoning = f"⚠️ CRITICAL: OFAC SANCTIONED/HIGH-RISK COUNTRY DETECTED - {countries_str}. " \
                           f"Transactions involving {countries_str} are subject to US Treasury OFAC sanctions or are known high-risk fraud countries. " \
                           f"Additional red flags detected: {', '.join(risk_factors[1:])}. " \
                           f"This transaction requires immediate review and manual verification."
                
                logger.info(f"💰 [Cost Savings] OFAC pre-check triggered - skipping LLM call. Score: {fraud_score} ({risk_level})")
                logger.info(f"   → Countries: {countries_str}, Red flags: {red_flags_count + 1}")
                
                return {
                    "fraud_score": fraud_score,
                    "risk_level": risk_level,
                    "risk_factors": risk_factors,
                    "reasoning": reasoning,
                    "model_used": "OFAC Pre-Check (Cost-Efficient)",
                    "cost_saved": True
                }
            # If OFAC but fewer red flags, still call LLM for detailed analysis
            else:
                logger.info(f"⚠️  OFAC country detected ({', '.join(ofac_countries)}) but proceeding with LLM for detailed analysis")

        # Build prompt based on sector, including RAG context
        prompt = build_prompt(sector, data, rag_context)

        # Build ordered list: primary + fallbacks
        candidates: List[Dict[str, str]] = [model_config["primary"]]
        candidates.extend(model_config.get("fallbacks", []))

        for idx, cfg in enumerate(candidates):
            provider = cfg.get("provider")
            model_name = cfg.get("model")

            if not provider or not model_name:
                continue

            is_fallback = (idx > 0)
            fallback_number = idx if is_fallback else None

            # Log fallback attempts
            if is_fallback:
                logger.warning(f"⚠️  Primary model failed, trying fallback #{fallback_number}: {provider} - {model_name}")
            else:
                logger.info(f"Calling {provider} model: {model_name} for sector: {sector}")

            if provider == "hf":
                result = self._try_hf_model(model_name, prompt, sector, data)
            elif provider == "openrouter":
                result = self._try_openrouter_model(model_name, prompt, sector, data)
            elif provider == "vertex":
                result = self._try_vertex_model(model_name, prompt, sector, data)
            else:
                logger.error(f"Unknown provider '{provider}' for model {model_name}")
                result = None

            if result:
                # Add model information to the response
                result["model_used"] = _format_model_name(model_name, provider, is_fallback, fallback_number)
                result["provider"] = provider
                
                if is_fallback:
                    logger.info(f"✅ Fallback #{fallback_number} successful: Using {provider} - {model_name}")
                
                return result

        # All providers + fallbacks failed, use rule-based scoring
        logger.warning("All LLM providers failed, falling back to rule-based scoring")
        return self._fallback_analysis(sector, data)

    # -------------------------
    # Provider-specific helpers
    # -------------------------

    def _try_hf_model(self, model_name: str, prompt: str, sector: str, data: Dict[str, Any], is_clinical_stage: bool = False) -> Optional[Dict[str, Any]]:
        """
        Call HF router using InferenceClient with retry logic for rate limiting.
        
        Many HF models don't support chat_completion API (returns 400 Bad Request).
        We try chat_completion first, but if it fails with 400, we immediately
        fall back to text_generation which most models support.
        
        GCP deployments often hit 429 errors due to:
        - Shared IP addresses (multiple Cloud Run instances)
        - Higher request volume
        - IP-based rate limiting by Hugging Face
        
        This method implements exponential backoff retry for 429 errors.
        
        Args:
            is_clinical_stage: If True, parse response as clinical validation (Stage 1),
                             otherwise parse as fraud detection (Stage 2 or single-stage)
        """
        max_retries = 3
        base_delay = 2.0  # Start with 2 seconds
        
        # Models that are known to not support chat_completion (skip it)
        models_no_chat = [
            "instruction-pretrain/finance-Llama3-8B",
            "meta-llama/Llama-3.1-8B-Instruct",
            "mistralai/Mistral-7B-Instruct-v0.2"
        ]
        
        # Models that ONLY support chat_completion (conversational) - NEVER use text_generation
        models_chat_only = [
            "qwen",
            "Qwen"
        ]
        
        skip_chat = any(no_chat in model_name for no_chat in models_no_chat)
        chat_only = any(chat_only_model in model_name for chat_only_model in models_chat_only)
        
        # Try chat_completion first (unless we know it doesn't work)
        if not skip_chat:
            for attempt in range(max_retries):
                try:
                    logger.info(f"  → Attempting chat_completion API with {model_name} (attempt {attempt + 1}/{max_retries})...")
                    messages = [{"role": "user", "content": prompt}]
                    
                    response = self.client.chat_completion(
                        messages=messages,
                        model=model_name,
                        max_tokens=512,
                        temperature=0.5,  # Lower temperature for more precise, deterministic fraud analysis
                        stream=False
                    )
                    
                    generated_text = response.choices[0].message.content
                    
                    logger.info(f"✅ HF API success (chat) with {model_name}! Response length: {len(str(generated_text))} chars")
                    
                    # Parse the response to extract fraud score and reasoning
                    parsed = parse_model_response(str(generated_text), sector, data, is_clinical_stage=is_clinical_stage)
                    return parsed
                
                except Exception as chat_error:
                    # Check for rate limit errors in multiple ways
                    error_str = str(chat_error).lower()
                    error_type = type(chat_error).__name__.lower()
                    
                    # Check HTTP status code if available
                    status_code = None
                    if hasattr(chat_error, 'status_code'):
                        status_code = chat_error.status_code
                    elif hasattr(chat_error, 'response') and hasattr(chat_error.response, 'status_code'):
                        status_code = chat_error.response.status_code
                    
                    # Log error details for debugging
                    logger.warning(f"⚠️  Chat completion error on attempt {attempt + 1}/{max_retries}: {type(chat_error).__name__}: {str(chat_error)[:200]}")
                    
                    # If 400 Bad Request, check if this is a chat-only model
                    if status_code == 400 or "400" in error_str or "bad request" in error_str:
                        if chat_only:
                            # Qwen models ONLY support chat - retry with better error handling
                            logger.warning(f"⚠️  Chat completion returned 400 for {model_name} (chat-only model). This might be a transient error. Retrying...")
                            if attempt < max_retries - 1:
                                delay = base_delay * (attempt + 1)  # Increasing delay: 2s, 4s, 6s
                                logger.info(f"  → Waiting {delay:.1f}s before retry...")
                                time.sleep(delay)
                                continue
                            else:
                                # Final attempt failed - don't fall back to text_generation
                                logger.error(f"❌ Chat completion failed for {model_name} after {max_retries} attempts with 400 error.")
                                logger.error(f"   Error details: {str(chat_error)}")
                                logger.error(f"   This model only supports conversational tasks (chat_completion).")
                                raise ValueError(f"Model {model_name} only supports conversational tasks (chat_completion), but chat_completion failed with 400 Bad Request after {max_retries} attempts: {str(chat_error)}")
                        else:
                            # Non-chat-only model - can fall back to text_generation
                            logger.debug(f"  → Model {model_name} doesn't support chat_completion (400), using text_generation directly")
                            break  # Skip chat_completion, go to text_generation
                    
                    is_rate_limit = (
                        status_code == 429 or
                        "429" in error_str or
                        "rate limit" in error_str or
                        "too many requests" in error_str or
                        "ratelimit" in error_type or
                        "rate_limit" in error_type
                    )
                    
                    if is_rate_limit and attempt < max_retries - 1:
                        # Exponential backoff: 2s, 4s, 8s
                        delay = base_delay * (2 ** attempt)
                        logger.warning(f"⚠️  Rate limit (429) on attempt {attempt + 1}, retrying in {delay:.1f}s...")
                        time.sleep(delay)
                        continue
                    
                    # Other errors on final attempt
                    if attempt == max_retries - 1:
                        if chat_only:
                            # Chat-only model - don't fall back to text_generation
                            logger.error(f"❌ Chat completion failed for {model_name} after {max_retries} attempts. This model only supports conversational tasks.")
                            raise ValueError(f"Model {model_name} only supports conversational tasks (chat_completion), but chat_completion failed: {str(chat_error)}")
                        else:
                            logger.debug(f"  → chat_completion failed ({type(chat_error).__name__}), falling back to text_generation")
        
        # Use text_generation (only if model is NOT chat-only)
        if chat_only:
            # Should never reach here - chat_only models should raise above
            logger.error(f"❌ Internal error: chat_only model {model_name} reached text_generation fallback")
            raise ValueError(f"Model {model_name} only supports conversational tasks, but reached text_generation fallback")
        
        logger.info(f"  → Using text_generation API with {model_name}...")
        
        for text_attempt in range(max_retries):
            try:
                result = self.client.text_generation(
                    prompt,
                    model=model_name,
                    max_new_tokens=512,
                    temperature=0.5,  # Lower temperature for more precise, deterministic fraud analysis
                    return_full_text=False
                )
                
                # Handle generators, strings, and TextGenerationOutput responses
                import inspect
                if inspect.isgenerator(result) or hasattr(result, '__iter__') and not isinstance(result, (str, bytes)):
                    # It's a generator or iterator - consume it
                    try:
                        generated_text = ''.join(str(chunk) for chunk in result)
                    except StopIteration:
                        # Empty generator
                        raise ValueError("Model returned empty response")
                elif hasattr(result, 'generated_text'):
                    generated_text = result.generated_text
                elif isinstance(result, str):
                    generated_text = result
                else:
                    generated_text = str(result)
                
                logger.info(f"✅ HF API success (text_generation) with {model_name}! Response length: {len(str(generated_text))} chars")
                
                # Parse the response to extract fraud score and reasoning
                parsed = parse_model_response(str(generated_text), sector, data, is_clinical_stage=is_clinical_stage)
                return parsed
            
            except Exception as text_error:
                # Check for rate limit errors in multiple ways
                text_error_str = str(text_error).lower()
                text_error_type = type(text_error).__name__.lower()
                
                # Check HTTP status code if available
                text_status_code = None
                if hasattr(text_error, 'status_code'):
                    text_status_code = text_error.status_code
                elif hasattr(text_error, 'response') and hasattr(text_error.response, 'status_code'):
                    text_status_code = text_error.response.status_code
                
                is_text_rate_limit = (
                    text_status_code == 429 or
                    "429" in text_error_str or
                    "rate limit" in text_error_str or
                    "too many requests" in text_error_str or
                    "ratelimit" in text_error_type or
                    "rate_limit" in text_error_type
                )
                
                if is_text_rate_limit and text_attempt < max_retries - 1:
                    delay = base_delay * (2 ** text_attempt)
                    logger.warning(f"⚠️  Rate limit (429) on text_generation attempt {text_attempt + 1}, retrying in {delay:.1f}s...")
                    time.sleep(delay)
                    continue
                
                # Final attempt failed or non-rate-limit error
                if text_attempt == max_retries - 1:
                    logger.error(f"❌ text_generation failed after {max_retries} attempts: {type(text_error).__name__}: {str(text_error)}")
                    break
        
        # All retries exhausted
        logger.error(f"❌ text_generation failed for {model_name} after {max_retries} attempts")
        return None

    def _try_openrouter_model(self, model_name: str, prompt: str, sector: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Call OpenRouter (e.g., nvidia/nemotron-3-nano-30b-a3b:free)."""
        if not self.openrouter_api_key:
            logger.warning("OPENROUTER_API_KEY not set, skipping OpenRouter model")
            return None

        try:
            headers = {
                "Authorization": f"Bearer {self.openrouter_api_key}",
                "Content-Type": "application/json",
                # Recommended but optional metadata
                "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "https://fraudforge.local"),
                "X-Title": os.getenv("OPENROUTER_APP_NAME", "FraudForge AI"),
            }
            payload = {
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 384,  # Reduced from 512 to speed up response (still enough for fraud analysis)
                "temperature": 0.5,  # Lower temperature for more precise, deterministic fraud analysis
            }

            resp = httpx.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=90.0,  # Increased timeout to 90s for free tier models which can be slower
            )
            resp.raise_for_status()
            data_json = resp.json()
            choices = data_json.get("choices") or []
            if not choices:
                logger.error(f"OpenRouter returned no choices for model {model_name}")
                return None

            generated_text = choices[0]["message"]["content"]
            logger.info(f"✅ OpenRouter success with {model_name}! Response length: {len(str(generated_text))} chars")

            parsed = parse_model_response(str(generated_text), sector, data)
            return parsed

        except Exception as e:
            logger.error(f"❌ OpenRouter call failed for {model_name}: {type(e).__name__}: {str(e)}")
            return None

    def _try_hf_space_model(self, space_name: str, data: Dict[str, Any], sector: str, is_clinical_stage: bool = False) -> Optional[Dict[str, Any]]:
        """
        Call Hugging Face Space API using gradio_client.
        
        Args:
            space_name: HF Space name (e.g., "ironjeffe/google-medgemma-4b-it")
            data: Medical claim data dictionary
            sector: Sector name
            is_clinical_stage: If True, parse as clinical validation response
        
        Returns:
            Parsed response dict or None if failed
        """
        if not GRADIO_AVAILABLE:
            logger.error("❌ gradio_client not installed - cannot call HF Space")
            logger.info("  → Install: pip install gradio_client")
            return None
        
        try:
            logger.info(f"  → Calling HF Space: {space_name}")
            
            # Initialize Gradio client with HF token for authentication
            hf_token = self.api_token  # Use the same HF token from LLMClient
            if not hf_token:
                logger.error("❌ No HF token available - cannot authenticate with HF Space")
                return None
            
            # Initialize client with HF token for authentication
            # Note: gradio_client has 120s default timeout, but we'll increase it
            client = Client(space_name, token=hf_token)
            
            # Increase timeout by patching the underlying httpx client
            # gradio_client uses httpx internally with 120s timeout
            if hasattr(client, 'client') and hasattr(client.client, 'timeout'):
                client.client.timeout = httpx.Timeout(300.0, connect=10.0)  # 5 min total
                logger.info("  → Increased HTTP timeout to 300 seconds for CPU inference")
            elif hasattr(client, '_client') and hasattr(client._client, 'timeout'):
                client._client.timeout = httpx.Timeout(300.0, connect=10.0)
                logger.info("  → Increased HTTP timeout to 300 seconds (via _client)")
            
            # Build formatted claim text for the Space
            # The Space wraps this with its own prompt, so we just provide structured claim data
            # Format matches the Space's example format for best results
            # Keep it simple - just the facts, no instructions (Space adds those)
            
            # Handle both singular and plural field names, and arrays
            diagnosis_codes = data.get('diagnosis_codes', [])
            if not diagnosis_codes:
                diagnosis_codes = [data.get('diagnosis_code', 'Unknown')]
            if isinstance(diagnosis_codes, str):
                diagnosis_codes = [c.strip() for c in diagnosis_codes.split(',') if c.strip()]
            diagnosis_str = ', '.join(diagnosis_codes) if diagnosis_codes else 'Unknown'
            
            procedure_codes = data.get('procedure_codes', [])
            if not procedure_codes:
                procedure_codes = [data.get('procedure_code', 'Unknown')]
            if isinstance(procedure_codes, str):
                procedure_codes = [c.strip() for c in procedure_codes.split(',') if c.strip()]
            procedure_str = ', '.join(procedure_codes) if procedure_codes else 'Unknown'
            
            # Map field names (frontend uses 'specialty', backend expects 'provider_specialty')
            provider_specialty = data.get('provider_specialty') or data.get('specialty', 'Unknown')
            
            # Get descriptions if available, otherwise use codes
            diagnosis_desc = data.get('diagnosis_description', '')
            procedure_desc = data.get('procedure_description', '')
            
            claim_text = f"""Diagnosis Codes (ICD-10): {diagnosis_str}"""
            if diagnosis_desc:
                claim_text += f" - {diagnosis_desc}"
            
            claim_text += f"""
Procedure Codes (CPT): {procedure_str}"""
            if procedure_desc:
                claim_text += f" - {procedure_desc}"
            
            claim_text += f"""
Patient Age: {data.get('patient_age', 'Unknown')} years
Patient Gender: {data.get('gender', 'Unknown')}
Provider ID: {data.get('provider_id', 'Unknown')}
Provider Specialty: {provider_specialty}
Claim Amount: ${data.get('claim_amount', 0):,.2f}
Treatment Date: {data.get('treatment_date', 'Unknown')}
Provider History: {data.get('provider_history', 'Unknown')}"""
            
            # Add claim details or medical notes if available
            claim_details = data.get('claim_details') or data.get('medical_notes', '')
            if claim_details and str(claim_details).strip() and str(claim_details) != 'No additional notes provided':
                claim_text += f"\nClaim Details: {claim_details}"
            
            # Verbose logging disabled for security (sensitive medical data)
            logger.info("  → Sending claim data to MedGemma Space")
            
            # Call the space API
            # The Space uses a simple Interface with analyze_claim(claim_text) function
            result = None
            try:
                # Get available API endpoints
                api_info = client.view_api()
                
                if api_info and isinstance(api_info, dict):
                    logger.info(f"  → Available API endpoints: {list(api_info.keys())}")
                    
                    # Try to find the correct endpoint (usually "analyze_claim" or first one)
                    api_name = None
                    for endpoint_name in api_info.keys():
                        # Look for analyze_claim or similar
                        if "analyze" in endpoint_name.lower() or "claim" in endpoint_name.lower():
                            api_name = endpoint_name
                            break
                    
                    # If not found, use the first endpoint
                    if not api_name and api_info:
                        api_name = list(api_info.keys())[0]
                        logger.info(f"  → Using first available endpoint: {api_name}")
                    elif api_name:
                        logger.info(f"  → Using endpoint: {api_name}")
                    
                    if api_name:
                        result = client.predict(
                            claim_text,
                            api_name=api_name
                        )
            except Exception as api_error:
                logger.warning(f"  → Could not determine API endpoint: {api_error}")
            
            # If endpoint detection failed or api_info was None, try without api_name (uses default)
            if result is None:
                logger.info("  → Using default endpoint (no api_name specified)...")
                result = client.predict(claim_text)
            
            result_str = str(result)
            logger.info(f"✅ HF Space API success! Response length: {len(result_str)} chars")
            
            # Check if the Space returned an error (CUDA errors, etc.)
            error_indicators = [
                "CUDA error",
                "device-side assert",
                "Error processing claim",
                "RuntimeError",
                "ValueError",
                "AttributeError",
                "TypeError"
            ]
            
            if any(indicator in result_str for indicator in error_indicators):
                logger.error(f"❌ HF Space returned an error response: {result_str[:300]}")
                logger.warning("  → Treating as failure, will fallback to next model")
                return None  # Return None to trigger fallback
            
            # Parse the response (space returns text, need to extract JSON if present)
            parsed = parse_model_response(result_str, sector, data, is_clinical_stage=is_clinical_stage)
            return parsed
            
        except Exception as e:
            logger.error(f"❌ HF Space call failed for {space_name}: {type(e).__name__}: {str(e)}")
            return None
    
    def _try_vertex_model(self, model_name: str, prompt: str, sector: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Call Google Vertex AI (for MedGemma models - currently unused, using HF Space instead).
        
        Requires:
            - GOOGLE_APPLICATION_CREDENTIALS environment variable
            - Vertex AI API enabled in GCP project
            - Service account with Vertex AI permissions
        
        Note: This is a placeholder for Vertex AI integration.
        Full implementation requires google-cloud-aiplatform library.
        """
        logger.warning(f"⚠️  Vertex AI provider not fully implemented yet for {model_name}")
        logger.info("  → Install: pip install google-cloud-aiplatform")
        logger.info("  → Set GOOGLE_APPLICATION_CREDENTIALS to service account JSON")
        
        # For now, skip to next fallback
        return None
    
    def _analyze_two_stage(self, sector: str, data: Dict[str, Any], rag_context: Optional[str], model_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Two-stage fraud analysis pipeline (currently only for medical claims).
        
        Stage 1: Clinical Legitimacy Validation (MedGemma)
          - Validates medical coherence
          - Checks diagnosis-procedure compatibility
          - Assesses treatment timeline plausibility
          - Evaluates CPT/ICD code relationships
        
        Stage 2: Fraud Pattern Analysis (Qwen)
          - Analyzes billing behavior using Stage 1 validation
          - Detects cost outliers and peer deviation
          - Identifies fraud patterns (upcoding, unbundling, etc.)
          - Provides final fraud score
        
        Args:
            sector: Sector name (e.g., 'medical')
            data: Claim/transaction data
            rag_context: Optional RAG context
            model_config: Two-stage model configuration
        
        Returns:
            Dict with fraud_score, reasoning, risk_factors, model_used
        """
        stage1_config = model_config["stage1"]
        stage2_config = model_config["stage2"]
        
        logger.info(f"🏥 [Stage 1] Starting {stage1_config['name']}")
        logger.info(f"   Model: {stage1_config['model']} ({stage1_config['provider']})")
        
        # ============================================================
        # STAGE 1: CLINICAL LEGITIMACY VALIDATION (MedGemma)
        # ============================================================
        
        stage1_prompt = build_stage1_clinical_prompt(data, rag_context)
        
        # Try Stage 1 model
        if stage1_config["provider"] == "hf_space":
            stage1_result = self._try_hf_space_model(stage1_config["model"], data, sector, is_clinical_stage=True)
        elif stage1_config["provider"] == "hf":
            stage1_result = self._try_hf_model(stage1_config["model"], stage1_prompt, sector, data, is_clinical_stage=True)
        elif stage1_config["provider"] == "vertex":
            stage1_result = self._try_vertex_model(stage1_config["model"], stage1_prompt, sector, data)
        else:
            stage1_result = None
        
        # If Stage 1 fails, fallback to single-stage
        if not stage1_result:
            logger.warning(f"⚠️  Stage 1 ({stage1_config['name']}) failed, trying fallbacks")
            return self._try_fallback_models(sector, data, rag_context, model_config)
        
        clinical_score = stage1_result.get("clinical_legitimacy_score", 50)
        clinical_reasoning = stage1_result.get("reasoning", "Clinical validation completed.")
        clinical_flags = stage1_result.get("risk_factors", [])
        
        logger.info(f"✅ [Stage 1] Clinical legitimacy score: {clinical_score}/100")
        logger.info(f"   Clinical flags: {len(clinical_flags)}")
        
        # ============================================================
        # STAGE 2: FRAUD PATTERN ANALYSIS (Qwen)
        # ============================================================
        
        logger.info(f"🔍 [Stage 2] Starting {stage2_config['name']}")
        logger.info(f"   Model: {stage2_config['model']} ({stage2_config['provider']})")
        
        stage2_prompt = build_stage2_fraud_prompt(data, rag_context, clinical_score, clinical_reasoning, clinical_flags)
        logger.info("  → Sending fraud analysis request to Qwen")
        
        # Try Stage 2 model
        if stage2_config["provider"] == "hf":
            stage2_result = self._try_hf_model(stage2_config["model"], stage2_prompt, sector, data)
        elif stage2_config["provider"] == "openrouter":
            stage2_result = self._try_openrouter_model(stage2_config["model"], stage2_prompt, sector, data)
        else:
            stage2_result = None
        
        # If Stage 2 fails, fallback to single-stage
        if not stage2_result:
            logger.warning(f"⚠️  Stage 2 ({stage2_config['name']}) failed, trying fallbacks")
            return self._try_fallback_models(sector, data, rag_context, model_config)
        
        fraud_score = stage2_result.get("fraud_score", 50)
        fraud_reasoning = stage2_result.get("reasoning", "Fraud analysis completed.")
        fraud_risk_factors = stage2_result.get("risk_factors", [])
        
        logger.info(f"✅ [Stage 2] Final fraud score: {fraud_score}/100 ({get_risk_level(fraud_score)})")
        logger.info(f"   Risk factors: {len(fraud_risk_factors)}")
        
        # ============================================================
        # COMBINE STAGE 1 + STAGE 2 RESULTS
        # ============================================================
        
        # Combine risk factors from both stages
        all_risk_factors = []
        if clinical_flags:
            all_risk_factors.extend([f"[Clinical] {flag}" for flag in clinical_flags])
        if fraud_risk_factors:
            all_risk_factors.extend([f"[Fraud] {flag}" for flag in fraud_risk_factors])
        
        # Build comprehensive reasoning
        combined_reasoning = f"**CLINICAL VALIDATION (Stage 1 - MedGemma):**\n{clinical_reasoning}\n\n" \
                           f"**FRAUD ANALYSIS (Stage 2 - Qwen):**\n{fraud_reasoning}"
        
        # Format model name to show two-stage pipeline
        stage1_name = stage1_config['model'].split('/')[-1].replace('google-medgemma-4b-it', 'MedGemma-4B-IT')
        stage2_name = stage2_config['model'].split('/')[-1].replace('Qwen2.5-72B-Instruct', 'Qwen2.5-72B')
        model_used = f"Two-Stage: {stage1_name} → {stage2_name}"
        
        return {
            "fraud_score": fraud_score,
            "risk_level": get_risk_level(fraud_score),
            "risk_factors": all_risk_factors,
            "reasoning": combined_reasoning,
            "model_used": model_used,
            "provider": "two_stage",
            "clinical_score": clinical_score,  # Additional metadata
            "stage1_model": stage1_config["model"],
            "stage2_model": stage2_config["model"]
        }
    
    def _try_fallback_models(self, sector: str, data: Dict[str, Any], rag_context: Optional[str], model_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Try fallback models when two-stage pipeline fails.
        Falls back to single-stage inference with Nemotron or other fallbacks.
        """
        prompt = build_prompt(sector, data, rag_context)
        
        for idx, fallback_cfg in enumerate(model_config.get("fallbacks", [])):
            provider = fallback_cfg.get("provider")
            model_name = fallback_cfg.get("model")
            
            logger.warning(f"⚠️  Trying fallback #{idx + 1}: {provider} - {model_name}")
            
            if provider == "hf":
                result = self._try_hf_model(model_name, prompt, sector, data)
            elif provider == "openrouter":
                result = self._try_openrouter_model(model_name, prompt, sector, data)
            else:
                result = None
            
            if result:
                result["model_used"] = f"{model_name.split('/')[-1]} (Fallback #{idx + 1})"
                result["provider"] = provider
                return result
        
        # All fallbacks failed
        logger.error(f"❌ All models failed for {sector} sector")
        return {
            "fraud_score": 50,
            "risk_level": "MEDIUM",
            "risk_factors": ["All LLM models unavailable"],
            "reasoning": "Unable to analyze - all models failed. Manual review required.",
            "model_used": "None (All Failed)",
            "provider": "none"
        }
    
    def _fallback_analysis(self, sector: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Rule-based fallback when API fails"""
        logger.info(f"Using rule-based fallback for sector: {sector}")

        from app.core import analyze_fraud_rule_based
        return analyze_fraud_rule_based(sector, data)


def _format_model_name(model_name: str, provider: str, is_fallback: bool, fallback_number: Optional[int]) -> str:
    """Format model name for display in UI with provider and fallback information."""
    display_name = model_name
    if "Qwen2.5-72B" in model_name:
        display_name = "Qwen2.5-72B-Instruct"
    elif "Qwen2.5-32B" in model_name:
        display_name = "Qwen2.5-32B-Instruct"
    elif "nemotron-nano-12b-v2-vl" in model_name.lower():
        display_name = "Nemotron-2 (12B VL)"
    elif "nemotron-3-nano-30b" in model_name.lower():
        display_name = "Nemotron-3-Nano-30B"
    elif "deepseek-v3" in model_name.lower():
        display_name = "DeepSeek-V3"
    elif "deepseek-r1" in model_name.lower():
        display_name = "DeepSeek-R1"
    elif "llama-3.1-70b" in model_name.lower():
        display_name = "Llama-3.1-70B"
    elif "medgemma" in model_name.lower():
        display_name = "MedGemma-4B-IT" if "4b" in model_name.lower() else "MedGemma"
    provider_display = {"hf": "HF Pro", "openrouter": "OpenRouter FREE", "vertex": "Vertex AI"}.get(provider, provider.upper())
    if is_fallback and fallback_number is not None:
        return f"{display_name} (Fallback #{fallback_number} - {provider_display})"
    return f"{display_name} ({provider_display})"

