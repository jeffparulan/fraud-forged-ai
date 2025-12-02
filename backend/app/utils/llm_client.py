"""
Unified LLM client for fraud detection.

- Primary provider: Hugging Face Inference API (router.huggingface.co with Nebius AI for Nemotron)
- Banking/Crypto: finance-Llama3-8B with finBERT fallback
- Medical claims: self-hosted MedGemma-4B on Google Colab (free tier) with ClinicalBERT fallback
- Retail & Supply chain: HF NVIDIA Nemotron Nano 12B v2 (Nebius inference) with OpenRouter fallback

HF is called FIRST for all models, before falling back to OpenRouter or RAG/rule-based scoring.

Rate Limiting: Implements exponential backoff retry for 429 errors (per-token limits, not per-IP).
"""
import os
import logging
import time
from typing import Dict, Any, Optional, List

import httpx
from huggingface_hub import InferenceClient

logger = logging.getLogger(__name__)

# HF Inference API - using official InferenceClient (updated Dec 2024)
# Automatically routes to: https://router.huggingface.co/hf-inference
HF_API_BASE_URL = "https://router.huggingface.co/hf-inference"

# Sector model configuration (provider-aware)
# provider: "hf" | "colab" | "openrouter"
SECTOR_MODELS: Dict[str, Dict[str, Any]] = {
    # Banking / Crypto fraud
    "banking": {
        "primary": {"provider": "hf", "model": "instruction-pretrain/finance-Llama3-8B"},
        "fallbacks": [
            {"provider": "hf", "model": "ProsusAI/finbert"},
        ],
    },
    # Medical claims fraud
    "medical": {
        # Self-hosted MedGemma in Colab (you deploy this to stay on free GPU tiers)
        "primary": {"provider": "colab", "model": "google/medgemma-4b-it"},
        # Fallback: HF ClinicalBERT
        "fallbacks": [
            {"provider": "hf", "model": "medicalai/ClinicalBERT"},
        ],
    },
    # Retail / E‑commerce fraud
    "ecommerce": {
        "primary": {"provider": "hf", "model": "nvidia/NVIDIA-Nemotron-Nano-12B-v2"},  # Using Nebius inference provider (faster than OpenRouter)
        "fallbacks": [
            {"provider": "openrouter", "model": "nvidia/nemotron-nano-12b-v2-vl:free"},  # OpenRouter as backup
            {"provider": "openrouter", "model": "mistralai/mistral-7b-instruct:free"},
            {"provider": "hf", "model": "meta-llama/Llama-3.1-8B-Instruct"},
        ],
    },
    # Supply chain fraud
    "supply_chain": {
        "primary": {"provider": "hf", "model": "nvidia/NVIDIA-Nemotron-Nano-12B-v2"},  # Using Nebius inference provider (faster than OpenRouter)
        "fallbacks": [
            {"provider": "openrouter", "model": "nvidia/nemotron-nano-12b-v2-vl:free"},  # OpenRouter as backup
            {"provider": "openrouter", "model": "mistralai/mistral-7b-instruct:free"},
            {"provider": "hf", "model": "meta-llama/Llama-3.1-8B-Instruct"},
        ],
    },
}

class LLMClient:
    """Client for multi-provider LLM inference (HF, Colab, OpenRouter)"""
    
    def __init__(self, api_token: Optional[str] = None):
        self.api_token = api_token or os.getenv('HUGGINGFACE_API_TOKEN')
        if not self.api_token:
            logger.warning("No Hugging Face API token provided - inference will fail")
        
        # Hugging Face router client (automatically uses HF_API_BASE_URL)
        self.client = InferenceClient(token=self.api_token)
        logger.info("✅ InferenceClient initialized (using HF router endpoint)")

        # OpenRouter configuration (free NVIDIA Nemotron tier)
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.openrouter_api_key:
            logger.warning("No OPENROUTER_API_KEY provided - OpenRouter models will be skipped")

        # Self-hosted MedGemma (Google Colab) endpoint
        self.medgemma_colab_url = os.getenv("MEDGEMMA_COLAB_URL")
        if not self.medgemma_colab_url:
            logger.warning("No MEDGEMMA_COLAB_URL set - MedGemma primary will be skipped, using ClinicalBERT fallback")
    
    def analyze_fraud(self, sector: str, data: Dict[str, Any], rag_context: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze fraud using sector-specific model with fallback support across providers.
        
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

        # Build prompt based on sector, including RAG context
        prompt = self._build_prompt(sector, data, rag_context)

        # Build ordered list: primary + fallbacks
        candidates: List[Dict[str, str]] = [model_config["primary"]]
        candidates.extend(model_config.get("fallbacks", []))

        for cfg in candidates:
            provider = cfg.get("provider")
            model_name = cfg.get("model")

            if not provider or not model_name:
                continue

            # Log fallback attempts
            if cfg != candidates[0]:
                logger.warning(f"⚠️  Primary model failed, trying fallback: {provider} - {model_name}")
            else:
                logger.info(f"Calling {provider} model: {model_name} for sector: {sector}")

            if provider == "hf":
                result = self._try_hf_model(model_name, prompt, sector, data)
            elif provider == "openrouter":
                result = self._try_openrouter_model(model_name, prompt, sector, data)
            elif provider == "colab":
                result = self._try_colab_model(model_name, prompt, sector, data)
            else:
                logger.error(f"Unknown provider '{provider}' for model {model_name}")
                result = None

            if result:
                if cfg != candidates[0]:
                    logger.info(f"✅ Fallback successful: Using {provider} - {model_name}")
                return result

        # All providers + fallbacks failed, use rule-based scoring
        logger.warning("All LLM providers failed, falling back to rule-based scoring")
        return self._fallback_analysis(sector, data)

    # -------------------------
    # Provider-specific helpers
    # -------------------------

    def _try_hf_model(self, model_name: str, prompt: str, sector: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
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
        """
        max_retries = 3
        base_delay = 2.0  # Start with 2 seconds
        
        # Models that are known to not support chat_completion (skip it)
        models_no_chat = [
            "instruction-pretrain/finance-Llama3-8B",
            "meta-llama/Llama-3.1-8B-Instruct",
            "mistralai/Mistral-7B-Instruct-v0.2"
        ]
        
        skip_chat = any(no_chat in model_name for no_chat in models_no_chat)
        
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
                    logger.info(f"✅ HF API success (chat) with {model_name}! Response: {str(generated_text)[:200]}...")
                    
                    # Parse the response to extract fraud score and reasoning
                    parsed = self._parse_model_response(str(generated_text), sector, data)
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
                    
                    # If 400 Bad Request, model doesn't support chat_completion - skip to text_generation
                    if status_code == 400 or "400" in error_str or "bad request" in error_str:
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
                    
                    # Other errors on final attempt - fall through to text_generation
                    if attempt == max_retries - 1:
                        logger.debug(f"  → chat_completion failed ({type(chat_error).__name__}), falling back to text_generation")
        
        # Use text_generation (either because chat_completion failed or model doesn't support it)
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
                
                logger.info(f"✅ HF API success (text_generation) with {model_name}! Response: {str(generated_text)[:200]}...")
                
                # Parse the response to extract fraud score and reasoning
                parsed = self._parse_model_response(str(generated_text), sector, data)
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
        """Call OpenRouter (e.g., nvidia/nemotron-nano-12b-v2-vl:free)."""
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
            logger.info(f"✅ OpenRouter success with {model_name}! Response: {str(generated_text)[:200]}...")

            parsed = self._parse_model_response(str(generated_text), sector, data)
            return parsed

        except Exception as e:
            logger.error(f"❌ OpenRouter call failed for {model_name}: {type(e).__name__}: {str(e)}")
            return None

    def _try_colab_model(self, model_name: str, prompt: str, sector: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Call self-hosted MedGemma running in Google Colab.

        Expected Colab service contract (you control this notebook/app):
        - HTTP POST to MEDGEMMA_COLAB_URL
        - JSON body: { "model": str, "prompt": str, "max_new_tokens": int, "temperature": float }
        - JSON response: { "text": str } OR { "generated_text": str }
        """
        if not self.medgemma_colab_url:
            logger.warning("MEDGEMMA_COLAB_URL not set, skipping Colab MedGemma")
            return None

        try:
            payload = {
                "model": model_name,
                "prompt": prompt,
                "max_new_tokens": 512,
                "temperature": 0.5,  # Lower temperature for more precise, deterministic fraud analysis
            }

            resp = httpx.post(self.medgemma_colab_url, json=payload, timeout=90.0)
            resp.raise_for_status()
            data_json = resp.json()

            generated_text = (
                data_json.get("text")
                or data_json.get("generated_text")
                or str(data_json)
            )

            logger.info(f"✅ Colab MedGemma success with {model_name}! Response: {str(generated_text)[:200]}...")
            parsed = self._parse_model_response(str(generated_text), sector, data)
            return parsed

        except Exception as e:
            logger.error(f"❌ Colab MedGemma call failed for {model_name}: {type(e).__name__}: {str(e)}")
            return None
    
    def _build_prompt(self, sector: str, data: Dict[str, Any], rag_context: Optional[str] = None) -> str:
        """Build fraud detection prompt for the LLM, including RAG context if available"""
        
        # Add RAG context section if available
        rag_section = ""
        if rag_context and rag_context.strip() and rag_context != "No similar patterns found.":
            rag_section = f"""

CONTEXT FROM SIMILAR FRAUD PATTERNS:
{rag_context}

Use this context to inform your analysis, but base your score on the specific transaction details provided below.
"""
        
        if sector == 'banking':
            wallet_info = ""
            if data.get('sender_wallet') or data.get('receiver_wallet'):
                wallet_info = f"""
Blockchain Details (Crypto Transaction):
- Sender Wallet: {data.get('sender_wallet', 'N/A')}
- Receiver Wallet: {data.get('receiver_wallet', 'N/A')}
- Note: Check wallet addresses against known fraud databases and Etherscan for transaction history
"""
            
            return f"""You are a senior financial fraud analyst with 15 years of experience. Analyze this transaction and provide a detailed, professional assessment in plain English. Do NOT generate code or technical syntax.
{rag_section}
Transaction Details:
- Transaction ID: {data.get('transaction_id')}
- Type: {data.get('transaction_type')}
- Amount: ${data.get('amount')}
- Source Country: {data.get('source_country')}
- Destination Country: {data.get('destination_country')}
- Account Age: {data.get('account_age_days')} days
- KYC Verified: {data.get('kyc_verified')}
- Previously Flagged: {data.get('previously_flagged')}
- Transaction Velocity: {data.get('transaction_velocity', 'N/A')} transactions in 24h
- IP Address: {data.get('ip_address', 'N/A')}
{wallet_info}
REQUIRED: Provide a comprehensive fraud analysis with:
1. FRAUD_SCORE: A number from 0-100
2. RISK_LEVEL: LOW, MEDIUM, HIGH, or CRITICAL
3. RISK_FACTORS: List 3-5 specific red flags you identified
4. REASONING: Write 3-4 complete sentences explaining:
   - WHY this transaction is flagged (cite specific data points)
   - WHAT patterns indicate fraud (be specific about amounts, timing, locations, wallet addresses)
   - HOW severe the risk is (justify your score)
   
Format exactly as:
FRAUD_SCORE: [number]
RISK_LEVEL: [level]
RISK_FACTORS: [factor1, factor2, factor3]
REASONING: [Write your detailed analysis here. Be specific about the transaction amount of ${data.get('amount')}, the account age of {data.get('account_age_days')} days, and the transaction from {data.get('source_country')}. Mention concrete red flags.]
"""
        
        elif sector == 'medical':
            return f"""You are a senior healthcare fraud investigator with 15 years of experience in medical billing fraud. Analyze this claim and provide a detailed, professional assessment in plain English. Do NOT generate code or technical syntax.
{rag_section}
Claim Details:
- Claim ID: {data.get('claim_id')}
- Patient Age: {data.get('patient_age')}
- Provider ID: {data.get('provider_id')}
- Specialty: {data.get('specialty')}
- Diagnosis Codes: {data.get('diagnosis_codes')}
- Procedure Codes: {data.get('procedure_codes')}
- Claim Amount: ${data.get('claim_amount')}
- Provider History: {data.get('provider_history')}
- Claim Details: {data.get('claim_details')}

REQUIRED: Provide a comprehensive fraud analysis with:
1. FRAUD_SCORE: A number from 0-100
2. RISK_LEVEL: LOW, MEDIUM, HIGH, or CRITICAL
3. RISK_FACTORS: List 3-5 specific red flags (e.g., unbundling, upcoding, procedure mismatches)
4. REASONING: Write 3-4 complete sentences explaining:
   - WHY this claim is suspicious (cite specific procedure codes and diagnosis codes)
   - WHAT billing patterns indicate fraud (be specific about the ${data.get('claim_amount')} amount)
   - HOW the procedures relate to the diagnosis (check for medical necessity)
   
Format exactly as:
FRAUD_SCORE: [number]
RISK_LEVEL: [level]
RISK_FACTORS: [factor1, factor2, factor3]
REASONING: [Write your detailed analysis here. Reference the specific claim amount of ${data.get('claim_amount')}, the procedure codes {data.get('procedure_codes')}, and why this claim raises red flags. Be specific and professional.]
"""
        
        elif sector == 'ecommerce':
            return f"""You are a senior e-commerce fraud prevention specialist with expertise in online marketplace scams. Analyze this transaction and provide a detailed, professional assessment in plain English. Do NOT generate code or technical syntax.
{rag_section}
Transaction Details:
- Order ID: {data.get('order_id')}
- Seller Age: {data.get('seller_age_days', 'N/A')} days
- Price: ${data.get('price', data.get('amount', 'N/A'))}
- Market Price: ${data.get('market_price', 'N/A')}
- Amount: ${data.get('amount', data.get('price', 'N/A'))}
- Shipping Address: {data.get('shipping_address', 'N/A')}
- Billing Address: {data.get('billing_address', 'N/A')}
- Payment Method: {data.get('payment_method', 'N/A')}
- IP Address: {data.get('ip_address', 'N/A')}
- Email Verified: {data.get('email_verified', False)}
- Reviews: {data.get('reviews', 'N/A')}
- Shipping Location: {data.get('shipping_location', 'N/A')}
- Product Details: {data.get('product_details', 'N/A')}

REQUIRED: Provide a comprehensive fraud analysis with:
1. FRAUD_SCORE: A number from 0-100
2. RISK_LEVEL: LOW, MEDIUM, HIGH, or CRITICAL
3. RISK_FACTORS: List 3-5 specific red flags (e.g., address mismatch, high-value item, unverified email)
4. REASONING: Write 3-4 complete sentences explaining:
   - WHY this order is suspicious (cite specific data like shipping/billing mismatch)
   - WHAT fraud patterns are present (be specific about the ${data.get('amount')} purchase)
   - HOW likely this is fraudulent (consider email verification, IP, and addresses)
   
Format exactly as:
FRAUD_SCORE: [number]
RISK_LEVEL: [level]
RISK_FACTORS: [factor1, factor2, factor3]
REASONING: [Write your detailed analysis here. Reference the specific order amount of ${data.get('amount')}, the email verification status, and explain why the shipping/billing addresses raise concerns. Be thorough and specific.]
"""
        
        elif sector == 'supply_chain':
            return f"""You are a senior supply chain fraud investigator with expertise in procurement fraud, kickback schemes, and ghost suppliers. Analyze this order and provide a detailed, professional assessment in plain English. Do NOT generate code or technical syntax.
{rag_section}
Order Details:
- Supplier ID: {data.get('supplier_id', 'N/A')}
- Supplier Name: {data.get('supplier_name', 'N/A')}
- Order Amount: ${data.get('order_amount', 'N/A')}
- Order Frequency: {data.get('order_frequency', 'N/A')} per year
- Payment Terms: {data.get('payment_terms', 'N/A')}
- Supplier Age: {data.get('supplier_age_days', 'N/A')} days
- Price Variance: {data.get('price_variance', 'N/A')}% from market average
- Delivery Variance: {data.get('delivery_variance', 'N/A')}%
- Quality Issues: {data.get('quality_issues', 'N/A')}
- Documentation Complete: {data.get('documentation_complete', False)}
- Regulatory Compliance: {data.get('regulatory_compliance', False)}
- Order Details: {data.get('order_details', 'N/A')}

REQUIRED: Provide a comprehensive fraud analysis with:
1. FRAUD_SCORE: A number from 0-100
2. RISK_LEVEL: LOW, MEDIUM, HIGH, or CRITICAL
3. RISK_FACTORS: List 3-5 specific red flags (e.g., ghost supplier, price inflation, missing docs)
4. REASONING: Write 3-4 complete sentences explaining:
   - WHY this supplier is suspicious (cite specific data like supplier age and price variance)
   - WHAT procurement fraud patterns are present (be specific about the ${data.get('order_amount')} amount and {data.get('price_variance')}% variance)
   - HOW severe the fraud risk is (consider documentation gaps and compliance issues)
   
Format exactly as:
FRAUD_SCORE: [number]
RISK_LEVEL: [level]
RISK_FACTORS: [factor1, factor2, factor3]
REASONING: [Write your detailed analysis here. Reference the ${data.get('order_amount')} order from a {data.get('supplier_age_days')}-day-old supplier with {data.get('price_variance')}% price variance. Explain specific kickback or ghost supplier indicators.]
"""
        
        return ""
    
    def _parse_model_response(self, text: str, sector: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse LLM response to extract structured fraud analysis"""
        import re
        
        # Try to extract fraud score
        score_match = re.search(r'FRAUD[_\s]SCORE:\s*(\d+)', text, re.IGNORECASE)
        if score_match:
            fraud_score = int(score_match.group(1))
        else:
            # Fallback: look for percentage
            pct_match = re.search(r'(\d+)%', text)
            fraud_score = int(pct_match.group(1)) if pct_match else 50
        
        # ALWAYS calculate risk level from fraud score (don't trust LLM classification)
        # This ensures consistent color coding across all sectors
        if fraud_score < 30:
            risk_level = 'LOW'
        elif fraud_score < 60:
            risk_level = 'MEDIUM'
        elif fraud_score < 85:
            risk_level = 'HIGH'
        else:
            risk_level = 'CRITICAL'
        
        # Try to extract risk factors
        factors_match = re.search(r'RISK[_\s]FACTORS:\s*([^\n]+)', text, re.IGNORECASE)
        if factors_match:
            risk_factors = [f.strip() for f in factors_match.group(1).split(',')]
        else:
            risk_factors = ['Analysis pending']
        
        # Extract reasoning
        reasoning_match = re.search(r'REASONING:\s*(.+)', text, re.IGNORECASE | re.DOTALL)
        if reasoning_match:
            reasoning = reasoning_match.group(1).strip()
        else:
            reasoning = text  # Use full text as reasoning
        
        # Clean up reasoning - remove code artifacts, regex patterns, and shell commands
        reasoning = self._clean_reasoning(reasoning)
        
        # Ensure reasoning ends at a complete sentence (NO truncation unless necessary)
        if len(reasoning) > 1200:  # Increased from 800 to 1200
            # Find the last complete sentence ending within 1200 chars
            last_period = max(
                reasoning[:1200].rfind('.'),
                reasoning[:1200].rfind('!'),
                reasoning[:1200].rfind('?')
            )
            if last_period > 150:  # Ensure substantial content (lowered from 200)
                reasoning = reasoning[:last_period + 1]
            else:
                # If no good sentence break, just take 1200 chars
                reasoning = reasoning[:1200]
        
        # Final check: if it ends with an incomplete sentence marker, remove it
        reasoning = reasoning.rstrip()
        if reasoning.endswith((' is', ' are', ' was', ' were', ' has', ' have', ' the')):
            # Incomplete sentence - find previous sentence
            prev_period = max(
                reasoning[:-10].rfind('.'),
                reasoning[:-10].rfind('!'),
                reasoning[:-10].rfind('?')
            )
            if prev_period > 150:
                reasoning = reasoning[:prev_period + 1]
        
        return {
            'fraud_score': fraud_score,
            'risk_level': risk_level,
            'risk_factors': risk_factors,
            'reasoning': reasoning
        }
    
    def _clean_reasoning(self, text: str) -> str:
        """Clean up reasoning text by removing code artifacts, regex, and shell commands"""
        import re
        
        # Remove FRAUD_SCORE and RISK_LEVEL statements (they're displayed separately)
        text = re.sub(r'FRAUD[_\s]SCORE:\s*\d+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'RISK[_\s]LEVEL:\s*(LOW|MEDIUM|HIGH|CRITICAL)', '', text, flags=re.IGNORECASE)
        text = re.sub(r'RISK[_\s]FACTORS:\s*[^\n]*', '', text, flags=re.IGNORECASE)
        
        # If the text contains "Code:" or code markers, this is likely a bad response
        if re.search(r'\bCode:\s*```|```python|```javascript|import\s+\w+|def\s+\w+\(', text, re.IGNORECASE):
            # Extract only the first sentence before any code
            match = re.search(r'^([^`#]+?)(?:\s*Code:|```|import|def|class)', text, re.IGNORECASE)
            if match:
                text = match.group(1).strip()
            else:
                # If all else fails, return a generic message
                return "The transaction shows fraud risk based on multiple indicators including transaction amount, account age, and geographic location."
        
        # Remove shell commands and pipes (e.g., " | sed 's/ /,/g'")
        text = re.sub(r'\s*\|\s*\w+\s+[\'"].*?[\'"]', '', text)
        
        # Remove regex patterns in quotes (e.g., 's/ /,/g')
        text = re.sub(r'[\'"]s/.*?/.*?/[gi]*[\'"]', '', text)
        
        # Remove code blocks (triple backticks or single backticks)
        text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        text = re.sub(r'`[^`]+`', '', text)
        
        # Remove Python imports, function definitions, comments
        text = re.sub(r'(?:import|from)\s+\w+.*', '', text)
        text = re.sub(r'def\s+\w+\(.*?\):', '', text)
        text = re.sub(r'#\s*\w+.*', '', text)
        
        # Remove trailing quotes and parentheses artifacts
        text = re.sub(r'["\']$', '', text)
        text = re.sub(r'\s*\)\s*$', '', text)
        
        # Remove extra whitespace and multiple spaces
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove any remaining standalone words like "Example:" or "REASONING:"
        text = re.sub(r'\b(Example|Reasoning|Analysis):\s*', '', text, flags=re.IGNORECASE)
        
        # If text is too short (incomplete sentence), provide a fallback
        if len(text) < 50:
            return "This transaction exhibits fraud risk based on the transaction details, account age, and geographic factors provided."
        
        # Ensure it ends with proper punctuation
        if text and not text[-1] in '.!?':
            # Don't add period if it looks like an incomplete sentence
            if len(text) > 100:
                text += '.'
        
        return text
    
    def _fallback_analysis(self, sector: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Rule-based fallback when API fails"""
        logger.info(f"Using rule-based fallback for sector: {sector}")
        
        # Import the original rule-based logic
        from app.langgraph_router import analyze_fraud_rule_based
        return analyze_fraud_rule_based(sector, data)

