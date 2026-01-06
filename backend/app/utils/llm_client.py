"""
Unified LLM client for fraud detection with multi-provider support.

MODEL ALIGNMENT (Cost-Optimized Strategy):
- Banking: Qwen2.5-72B-Instruct (HF Pro) - Financial reasoning, AML patterns
    - Medical: TWO-STAGE PIPELINE (HF Inference API)
  ├─ Stage 1: MedGemma-4B-IT (Clinical legitimacy validation)
  └─ Stage 2: Qwen2.5-72B-Instruct (Fraud pattern analysis)
- E-commerce: Nemotron-2 (12B VL) (OpenRouter FREE) - Refund abuse, seller manipulation
- Supply Chain: Nemotron-2 (12B VL) (OpenRouter FREE) - Temporal reasoning, logistics

FALLBACK STRATEGY:
- Primary models use HF Pro (Banking/Medical) or OpenRouter FREE (E-commerce/Supply Chain)
- Fallbacks: Nemotron-3-Nano-30B (FREE), Llama-3.1-70B (FREE), MedGemma (Vertex AI)
- Rate limiting: Exponential backoff retry for 429 errors

COST OPTIMIZATION:
- Universal fraud pre-checks (OFAC countries, extreme values) skip LLM calls
- Leverages existing HF Pro subscription ($9/month)
- Maximizes FREE OpenRouter usage for E-commerce/Supply Chain
"""
import os
import logging
import time
from typing import Dict, Any, Optional, List, Tuple

import httpx
from huggingface_hub import InferenceClient

logger = logging.getLogger(__name__)

# Toggleable verbose logging for Stage 1 prompts/responses
# Set LOG_STAGE1_VERBOSE=1 in environment to enable
LOG_STAGE1_VERBOSE = os.getenv("LOG_STAGE1_VERBOSE", "0").lower() in ("1", "true", "yes")

try:
    from gradio_client import Client
    GRADIO_AVAILABLE = True
except ImportError:
    GRADIO_AVAILABLE = False
    logger.warning("gradio_client not installed - HF Space calls will fail. Install: pip install gradio_client")

# HF Inference API - using official InferenceClient (updated Dec 2024)
# Automatically routes to: https://router.huggingface.co/hf-inference
HF_API_BASE_URL = "https://router.huggingface.co/hf-inference"

# OFAC (Office of Foreign Assets Control) Sanctioned Countries and High-Risk Fraud Countries
# Based on US Treasury OFAC sanctions and high-risk fraud patterns
OFAC_SANCTIONED_COUNTRIES = [
    # Fully sanctioned countries (comprehensive sanctions)
    'cuba', 'iran', 'north korea', 'syria', 'crimea', 'donetsk', 'luhansk',
    # Countries with significant sanctions
    'russia', 'belarus', 'venezuela', 'myanmar', 'burma', 'sudan', 'south sudan',
    'libya', 'yemen', 'somalia', 'central african republic', 'democratic republic of congo',
    'congo', 'zimbabwe', 'mali', 'burkina faso', 'niger',
    # High-risk fraud countries (not OFAC but high fraud rates)
    'nigeria', 'ghana', 'cameroon', 'ivory coast', 'senegal', 'togo', 'benin',
    'philippines', 'indonesia', 'malaysia', 'thailand', 'vietnam', 'pakistan',
    'bangladesh', 'romania', 'bulgaria', 'ukraine', 'moldova', 'albania',
    'serbia', 'bosnia', 'macedonia', 'montenegro', 'kosovo',
    # Additional high-risk regions
    'west africa', 'east africa', 'balkans', 'eastern europe'
]

def check_ofac_country(location_str: str) -> Tuple[bool, str]:
    """
    Check if a location string contains OFAC sanctioned or high-risk countries.
    
    Args:
        location_str: Location string to check (country name, address, etc.)
    
    Returns:
        Tuple of (is_ofac_country: bool, country_found: str)
    """
    if not location_str:
        return False, ""
    
    location_lower = str(location_str).lower()
    
    for country in OFAC_SANCTIONED_COUNTRIES:
        if country in location_lower:
            return True, country.title()
    
    return False, ""

def check_ofac_in_data(data: Dict[str, Any], location_fields: List[str]) -> Tuple[bool, List[str]]:
    """
    Check if any OFAC countries are present in the data (cost-efficient pre-check).
    
    Args:
        data: Transaction/claim/order data dictionary
        location_fields: List of field names to check for country information
    
    Returns:
        Tuple of (has_ofac: bool, countries_found: List[str])
    """
    countries_found = []
    
    for field in location_fields:
        field_value = data.get(field, "")
        if field_value:
            is_ofac, country = check_ofac_country(str(field_value))
            if is_ofac and country not in countries_found:
                countries_found.append(country)
    
    return len(countries_found) > 0, countries_found

def build_ofac_risk_warning(data: Dict[str, Any], location_fields: List[str]) -> str:
    """
    Build OFAC risk warning for any sector by checking multiple location fields.
    
    Args:
        data: Transaction/claim/order data dictionary
        location_fields: List of field names to check for country information
    
    Returns:
        Warning string if OFAC country found, empty string otherwise
    """
    has_ofac, countries_found = check_ofac_in_data(data, location_fields)
    
    if has_ofac:
        countries_str = ", ".join(countries_found)
        return f"⚠️ CRITICAL: OFAC SANCTIONED/HIGH-RISK COUNTRY DETECTED - {countries_str}\n" \
               f"Transactions involving {countries_str} are subject to US Treasury OFAC sanctions or are known high-risk fraud countries.\n" \
               f"This is a MAJOR RED FLAG requiring immediate review. Add 40-60 points to fraud score."
    
    return ""

# Sector model configuration (provider-aware)
# provider: "hf" | "openrouter"
# 
# FRAUD-SPECIALIZED MODEL ALIGNMENT (Production-Grade 2025):
# COST-OPTIMIZED STRATEGY (User has HF Pro subscription):
# - Primary: OpenRouter FREE models (DeepSeek-V3, DeepSeek-R1, Nemotron-3-Nano)
# - Fallback: HF Pro subscription (Qwen2.5-72B, Llama-3.1-70B)
# - Goal: Maximize FREE usage, leverage existing HF Pro for redundancy
# 
# Banking: Qwen2.5-72B for financial reasoning (HF Pro with fallbacks)
# Medical: Qwen2.5-72B for billing patterns (HF Pro with fallbacks)
# E-commerce: DeepSeek-V3 (FREE) for process reasoning
# Supply Chain: DeepSeek-R1 (FREE) for temporal reasoning
SECTOR_MODELS: Dict[str, Dict[str, Any]] = {
    # Banking / Crypto fraud (math-heavy, AML patterns, multi-step transaction flow)
    "banking": {
        "primary": {"provider": "hf", "model": "Qwen/Qwen2.5-72B-Instruct"},  # HF Pro
        "fallbacks": [
            {"provider": "openrouter", "model": "nvidia/nemotron-3-nano-30b-a3b:free"},  # FREE
            {"provider": "openrouter", "model": "meta-llama/llama-3.1-70b-instruct:free"},  # FREE
        ],
    },
    # Medical claims fraud (TWO-STAGE PIPELINE for clinical + fraud analysis)
    "medical": {
        "two_stage": True,  # Enable two-stage processing
        "stage1": {
            "name": "Clinical Legitimacy Validation",
            "provider": "hf_space",  # HF Space API (FREE with HF Pro)
            "model": "ironjeffe/google-medgemma-4b-it",  # HF Space - Clinical validation
            "purpose": "Validate medical coherence, diagnosis-procedure compatibility, clinical plausibility"
        },
        "stage2": {
            "name": "Fraud Pattern Analysis",
            "provider": "hf",  # HF Inference API (FREE with HF Pro)
            "model": "Qwen/Qwen2.5-72B-Instruct",  # HF Inference API - Fraud analysis (32B not available, using 72B)
            "purpose": "Analyze billing behavior, cost outliers, peer deviation, fraud patterns"
        },
        "fallbacks": [
            {"provider": "openrouter", "model": "nvidia/nemotron-3-nano-30b-a3b:free"},  # FREE single-stage fallback
        ],
    },
    # E-commerce fraud (refund abuse, seller manipulation, marketplace dynamics)
    "ecommerce": {
        "primary": {"provider": "openrouter", "model": "nvidia/nemotron-nano-12b-v2-vl:free"},  # FREE - User confirmed better accuracy
        "fallbacks": [
            {"provider": "hf", "model": "Qwen/Qwen2.5-72B-Instruct"},  # HF Pro
            {"provider": "openrouter", "model": "nvidia/nemotron-3-nano-30b-a3b:free"},  # FREE backup
        ],
    },
    # Supply chain fraud (temporal reasoning, logistics anomalies, kickback schemes)
    "supply_chain": {
        "primary": {"provider": "openrouter", "model": "nvidia/nemotron-nano-12b-v2-vl:free"},  # FREE - User confirmed better accuracy
        "fallbacks": [
            {"provider": "hf", "model": "Qwen/Qwen2.5-72B-Instruct"},  # HF Pro
            {"provider": "openrouter", "model": "nvidia/nemotron-3-nano-30b-a3b:free"},  # FREE backup
        ],
    },
}

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
        
        extreme_fraud = self._check_extreme_fraud_patterns(sector, data)
        if extreme_fraud:
            logger.info(f"🚨 [Extreme Fraud] Pre-check triggered - skipping LLM call")
            return extreme_fraud
        
        # ============================================================
        # COST-EFFICIENT PRE-CHECK: OFAC Country Detection
        # ============================================================
        # Check for OFAC countries BEFORE expensive LLM calls
        # This saves money on clear-cut cases (deterministic string matching)
        
        sector_location_fields = {
            "banking": ["source_country", "destination_country", "location"],
            "medical": ["provider_location", "patient_location", "billing_address", "service_location"],
            "ecommerce": ["shipping_location", "shipping_address", "billing_address", "origin_country"],
            "supply_chain": ["supplier_location", "supplier_country", "origin_country", "shipping_location", "billing_address"]
        }
        
        location_fields = sector_location_fields.get(sector, [])
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
        prompt = self._build_prompt(sector, data, rag_context)

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
            elif provider == "colab":
                result = self._try_colab_model(model_name, prompt, sector, data)
            elif provider == "vertex":
                result = self._try_vertex_model(model_name, prompt, sector, data)
            else:
                logger.error(f"Unknown provider '{provider}' for model {model_name}")
                result = None

            if result:
                # Add model information to the response
                result["model_used"] = self._format_model_name(model_name, provider, is_fallback, fallback_number)
                result["provider"] = provider
                
                if is_fallback:
                    logger.info(f"✅ Fallback #{fallback_number} successful: Using {provider} - {model_name}")
                
                return result

        # All providers + fallbacks failed, use rule-based scoring
        logger.warning("All LLM providers failed, falling back to rule-based scoring")
        return self._fallback_analysis(sector, data)

    # -------------------------
    # Helper Methods
    # -------------------------

    def _check_extreme_fraud_patterns(self, sector: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Universal fraud pre-checks for extreme/impossible values across all industries.
        Returns fraud result immediately if extreme patterns detected, None otherwise.
        
        Examples of extreme fraud:
            - E-commerce: 1000x price markup (pricing scam)
            - Banking: $10M+ transactions from new accounts
            - Medical: Claims 10x above typical amounts
            - Supply Chain: 500%+ price variance
            - All: Negative amounts, impossible dates/ages
        """
        risk_factors = []
        base_score = 0
        
        # ============================================================
        # E-COMMERCE: EXTREME PRICE DISCREPANCY
        # ============================================================
        if sector == "ecommerce":
            try:
                listed_price = float(data.get("listed_price", 0))
                market_price = float(data.get("market_price", 0))
                
                if market_price > 0 and listed_price > 0:
                    markup_ratio = listed_price / market_price
                    markup_percent = (markup_ratio - 1) * 100
                    
                    # CRITICAL: >1000% markup (10x) = Pricing scam
                    if markup_ratio > 10:
                        base_score = 95
                        risk_factors.append(f"Extreme price markup: {markup_percent:.0f}% ({markup_ratio:.1f}x)")
                        risk_factors.append("Pricing scam/manipulation detected")
                    # HIGH: >500% markup (5x) = Major red flag
                    elif markup_ratio > 5:
                        base_score = 85
                        risk_factors.append(f"High price markup: {markup_percent:.0f}% ({markup_ratio:.1f}x)")
                    # MEDIUM-HIGH: >200% markup (2x) = Suspicious
                    elif markup_ratio > 2:
                        base_score = 70
                        risk_factors.append(f"Suspicious price markup: {markup_percent:.0f}% ({markup_ratio:.1f}x)")
            except (ValueError, ZeroDivisionError):
                pass
        
        # ============================================================
        # BANKING: EXTREME TRANSACTION AMOUNTS
        # ============================================================
        elif sector == "banking":
            try:
                amount = float(data.get("amount", 0))
                account_age = int(data.get("account_age_days", 365))
                
                # CRITICAL: >$1M from account <30 days old
                if amount > 1000000 and account_age < 30:
                    base_score = 95
                    risk_factors.append(f"Extreme amount ${amount:,.0f} from new account ({account_age} days)")
                # HIGH: >$500K from account <90 days old
                elif amount > 500000 and account_age < 90:
                    base_score = 85
                    risk_factors.append(f"High amount ${amount:,.0f} from young account ({account_age} days)")
                # CRITICAL: >$10M regardless of age (potential money laundering)
                elif amount > 10000000:
                    base_score = 90
                    risk_factors.append(f"Extreme transaction amount: ${amount:,.0f}")
            except (ValueError, TypeError):
                pass
        
        # ============================================================
        # MEDICAL: EXTREME CLAIM AMOUNTS
        # ============================================================
        elif sector == "medical":
            try:
                claim_amount = float(data.get("claim_amount", 0))
                
                # CRITICAL: >$1M medical claim (extremely rare)
                if claim_amount > 1000000:
                    base_score = 95
                    risk_factors.append(f"Extreme claim amount: ${claim_amount:,.0f}")
                # HIGH: >$500K claim
                elif claim_amount > 500000:
                    base_score = 85
                    risk_factors.append(f"Very high claim amount: ${claim_amount:,.0f}")
            except (ValueError, TypeError):
                pass
        
        # ============================================================
        # SUPPLY CHAIN: EXTREME PRICE VARIANCE
        # ============================================================
        elif sector == "supply_chain":
            try:
                price_variance = float(data.get("price_variance", 0))
                
                # CRITICAL: >500% price variance
                if price_variance > 500:
                    base_score = 90
                    risk_factors.append(f"Extreme price variance: {price_variance}%")
                # HIGH: >300% price variance
                elif price_variance > 300:
                    base_score = 80
                    risk_factors.append(f"High price variance: {price_variance}%")
            except (ValueError, TypeError):
                pass
        
        # ============================================================
        # UNIVERSAL: IMPOSSIBLE/NEGATIVE VALUES
        # ============================================================
        # Check for negative amounts (all sectors)
        for field in ["amount", "claim_amount", "listed_price", "market_price", "order_amount"]:
            try:
                value = float(data.get(field, 0))
                if value < 0:
                    base_score = max(base_score, 85)
                    risk_factors.append(f"Impossible negative value: {field} = ${value}")
            except (ValueError, TypeError):
                pass
        
        # ============================================================
        # RETURN IMMEDIATE RESULT IF EXTREME FRAUD DETECTED
        # ============================================================
        if base_score >= 70 and len(risk_factors) > 0:
            fraud_score = min(base_score + len(risk_factors) * 2, 100)  # Bonus for multiple red flags
            risk_level = "CRITICAL" if fraud_score >= 85 else "HIGH"
            
            reasoning = f"🚨 EXTREME FRAUD PATTERN DETECTED - Immediate intervention required. " \
                       f"This transaction exhibits clear fraud indicators that exceed normal risk thresholds: " \
                       f"{'. '.join(risk_factors)}. " \
                       f"Automated systems have flagged this for immediate manual review. " \
                       f"Such extreme patterns are statistically rare (<0.1% of transactions) and typically indicate " \
                       f"fraudulent activity, system manipulation, or data entry errors."
            
            logger.info(f"🚨 [Extreme Fraud] Score: {fraud_score} ({risk_level})")
            logger.info(f"   → Red flags: {', '.join(risk_factors)}")
            
            return {
                "fraud_score": fraud_score,
                "risk_level": risk_level,
                "risk_factors": risk_factors,
                "reasoning": reasoning,
                "model_used": "Extreme Fraud Pre-Check (Deterministic)",
                "cost_saved": True
            }
        
        # No extreme patterns - proceed to normal fraud analysis
        return None

    def _format_model_name(self, model_name: str, provider: str, is_fallback: bool, fallback_number: Optional[int]) -> str:
        """
        Format model name for display in UI with provider and fallback information.
        
        Examples:
            - "Qwen2.5-72B-Instruct (HF Pro)"
            - "Nemotron-3-Nano-30B (Fallback #1 - OpenRouter FREE)"
            - "MedGemma-4B-IT (HF Inference API)"
        """
        # Simplify model names for better readability
        display_name = model_name
        
        # Simplify common model names
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
            if "4b" in model_name.lower():
                display_name = "MedGemma-4B-IT"
            else:
                display_name = "MedGemma"
        
        # Format provider name
        provider_display = {
            "hf": "HF Pro",
            "openrouter": "OpenRouter FREE",
            "vertex": "Vertex AI",
            "colab": "Colab"
        }.get(provider, provider.upper())
        
        # Add fallback indicator if applicable
        if is_fallback and fallback_number is not None:
            return f"{display_name} (Fallback #{fallback_number} - {provider_display})"
        else:
            return f"{display_name} ({provider_display})"

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
                    
                    # Log full response if verbose logging is enabled (for Stage 2)
                    if LOG_STAGE1_VERBOSE and not is_clinical_stage:
                        logger.info("=" * 80)
                        logger.info(f"📥 [Stage 2] FULL RESPONSE FROM {model_name}:")
                        logger.info("=" * 80)
                        logger.info(f"{str(generated_text)}")
                        logger.info("=" * 80)
                    else:
                        logger.info(f"✅ HF API success (chat) with {model_name}! Response: {str(generated_text)[:200]}...")
                    
                    # Parse the response to extract fraud score and reasoning
                    parsed = self._parse_model_response(str(generated_text), sector, data, is_clinical_stage=is_clinical_stage)
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
                
                logger.info(f"✅ HF API success (text_generation) with {model_name}! Response: {str(generated_text)[:200]}...")
                
                # Parse the response to extract fraud score and reasoning
                parsed = self._parse_model_response(str(generated_text), sector, data, is_clinical_stage=is_clinical_stage)
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
            
            # Log the prompt request if verbose logging is enabled
            if LOG_STAGE1_VERBOSE:
                logger.info("=" * 80)
                logger.info("📤 [Stage 1] PROMPT REQUEST TO MEDGEMMA SPACE:")
                logger.info("=" * 80)
                logger.info(f"{claim_text}")
                logger.info("=" * 80)
            
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
            logger.info(f"✅ HF Space API success! Response: {result_str[:200]}...")
            
            # Log full response if verbose logging is enabled
            if LOG_STAGE1_VERBOSE:
                logger.info("=" * 80)
                logger.info("📥 [Stage 1] FULL RESPONSE FROM MEDGEMMA SPACE:")
                logger.info("=" * 80)
                logger.info(f"{result_str}")
                logger.info("=" * 80)
            
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
            parsed = self._parse_model_response(result_str, sector, data, is_clinical_stage=is_clinical_stage)
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
        
        stage1_prompt = self._build_stage1_clinical_prompt(data, rag_context)
        
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
        
        # Log parsed Stage 1 results if verbose logging is enabled
        if LOG_STAGE1_VERBOSE:
            logger.info("=" * 80)
            logger.info("📊 [Stage 1] PARSED RESULTS:")
            logger.info("=" * 80)
            logger.info(f"Clinical Score: {clinical_score}/100")
            logger.info(f"Clinical Reasoning: {clinical_reasoning[:500]}..." if len(clinical_reasoning) > 500 else f"Clinical Reasoning: {clinical_reasoning}")
            logger.info(f"Clinical Flags: {clinical_flags}")
            logger.info("=" * 80)
        
        # ============================================================
        # STAGE 2: FRAUD PATTERN ANALYSIS (Qwen)
        # ============================================================
        
        logger.info(f"🔍 [Stage 2] Starting {stage2_config['name']}")
        logger.info(f"   Model: {stage2_config['model']} ({stage2_config['provider']})")
        
        stage2_prompt = self._build_stage2_fraud_prompt(data, rag_context, clinical_score, clinical_reasoning, clinical_flags)
        
        # Log Stage 2 prompt if verbose logging is enabled
        if LOG_STAGE1_VERBOSE:
            logger.info("=" * 80)
            logger.info("📤 [Stage 2] PROMPT REQUEST TO QWEN:")
            logger.info("=" * 80)
            logger.info(f"{stage2_prompt}")
            logger.info("=" * 80)
        
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
        
        logger.info(f"✅ [Stage 2] Final fraud score: {fraud_score}/100 ({self._get_risk_level(fraud_score)})")
        
        # Log parsed Stage 2 results if verbose logging is enabled
        if LOG_STAGE1_VERBOSE:
            logger.info("=" * 80)
            logger.info("📊 [Stage 2] PARSED RESULTS:")
            logger.info("=" * 80)
            logger.info(f"Fraud Score: {fraud_score}/100")
            logger.info(f"Risk Level: {self._get_risk_level(fraud_score)}")
            logger.info(f"Fraud Reasoning: {fraud_reasoning[:1000]}..." if len(fraud_reasoning) > 1000 else f"Fraud Reasoning: {fraud_reasoning}")
            logger.info(f"Fraud Risk Factors: {fraud_risk_factors}")
            logger.info("=" * 80)
        
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
            "risk_level": self._get_risk_level(fraud_score),
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
        prompt = self._build_prompt(sector, data, rag_context)
        
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
    
    def _build_stage1_clinical_prompt(self, data: Dict[str, Any], rag_context: Optional[str] = None) -> str:
        """
        Build Stage 1 prompt for clinical legitimacy validation (MedGemma).
        Focuses on medical coherence, diagnosis-procedure compatibility, and clinical plausibility.
        """
        prompt = f"""You are a medical expert AI tasked with validating the CLINICAL LEGITIMACY of a medical claim.
Your job is to assess if the medical procedures, diagnoses, and treatments are medically coherent and clinically plausible.

**DO NOT** analyze fraud patterns or billing behavior - that will be done in Stage 2.
**FOCUS ONLY** on clinical validity, medical reasoning, and treatment appropriateness.

Medical Claim Details:
- Claim ID: {data.get('claim_id', 'Unknown')}
- Patient Age: {data.get('patient_age', 'Unknown')} years
- Patient Gender: {data.get('gender', 'Unknown')}
- Provider ID: {data.get('provider_id', 'Unknown')}
- Provider Specialty: {data.get('provider_specialty') or data.get('specialty', 'Unknown')}
- Diagnosis Codes (ICD-10): {', '.join(data.get('diagnosis_codes', [])) if isinstance(data.get('diagnosis_codes'), list) else (data.get('diagnosis_codes') or data.get('diagnosis_code', 'Unknown'))}
- Procedure Codes (CPT): {', '.join(data.get('procedure_codes', [])) if isinstance(data.get('procedure_codes'), list) else (data.get('procedure_codes') or data.get('procedure_code', 'Unknown'))}
- Claim Amount: ${data.get('claim_amount', 0):,.2f}
- Treatment Date: {data.get('treatment_date', 'Unknown')}
- Provider History: {data.get('provider_history', 'Unknown')}

Additional Medical Context:
{data.get('claim_details') or data.get('medical_notes', 'No additional notes provided')}

"""
        
        if rag_context:
            prompt += f"""
Similar Medical Claims (RAG Context):
{rag_context}

"""
        
        prompt += """
**Clinical Validation Checklist:**

1. **Diagnosis-Procedure Compatibility:**
   - Is the procedure appropriate for the diagnosis?
   - Are the ICD-10 and CPT codes medically aligned?

2. **Provider Specialty Match:**
   - Is the provider specialty appropriate for this procedure?
   - Example: Cardiologist for cardiac procedures, not appendectomies

3. **Treatment Timeline Plausibility:**
   - Does the treatment timeline make clinical sense?
   - Are follow-up procedures appropriately spaced?

4. **Age-Appropriate Care:**
   - Is the treatment appropriate for the patient's age?
   - Are there any age-related contraindications?

5. **Medical Necessity:**
   - Does the diagnosis justify the procedure?
   - Is the treatment medically necessary?

**Response Format (JSON):**
{
  "clinical_legitimacy_score": <0-100, where 0=medically impossible, 100=perfectly coherent>,
  "reasoning": "<Detailed clinical reasoning explaining the score>",
  "risk_factors": ["<List of clinical red flags, if any>"],
  "diagnosis_procedure_match": "<Compatible/Questionable/Incompatible>",
  "provider_specialty_appropriate": "<Yes/Questionable/No>",
  "medical_necessity": "<Clearly Justified/Uncertain/Unjustified>"
}

**Guidelines:**
- Score 80-100: Clinically coherent, medically appropriate
- Score 50-79: Some clinical concerns, needs review
- Score 0-49: Medically questionable or incompatible
- Focus ONLY on clinical validity, not fraud indicators

Provide your clinical assessment:"""

        return prompt
    
    def _build_stage2_fraud_prompt(self, data: Dict[str, Any], rag_context: Optional[str], 
                                   clinical_score: float, clinical_reasoning: str, 
                                   clinical_flags: List[str]) -> str:
        """
        Build Stage 2 prompt for fraud pattern analysis (Qwen).
        Uses Stage 1 clinical validation results to inform fraud analysis.
        Focuses on billing behavior, cost outliers, and peer deviation.
        """
        prompt = f"""You are a medical fraud detection AI expert. You have received a clinical legitimacy assessment from a medical expert AI (Stage 1).
Your job is to analyze this claim for FRAUD PATTERNS, BILLING ANOMALIES, and COST MANIPULATION.

**Stage 1 Clinical Validation Results:**
- Clinical Legitimacy Score: {clinical_score}/100
- Clinical Assessment: {clinical_reasoning}
- Clinical Red Flags: {', '.join(clinical_flags) if clinical_flags else 'None'}

**Medical Claim Details:**
- Claim ID: {data.get('claim_id', 'Unknown')}
- Patient Age: {data.get('patient_age', 'Unknown')} years
- Patient Gender: {data.get('gender', 'Unknown')}
- Provider ID: {data.get('provider_id', 'Unknown')}
- Provider Specialty: {data.get('provider_specialty') or data.get('specialty', 'Unknown')}
- Provider History: {data.get('provider_history', 'Unknown')}
- Diagnosis Codes (ICD-10): {', '.join(data.get('diagnosis_codes', [])) if isinstance(data.get('diagnosis_codes'), list) else (data.get('diagnosis_codes') or data.get('diagnosis_code', 'Unknown'))}
- Procedure Codes (CPT): {', '.join(data.get('procedure_codes', [])) if isinstance(data.get('procedure_codes'), list) else (data.get('procedure_codes') or data.get('procedure_code', 'Unknown'))}
- Claim Amount: ${data.get('claim_amount', 0):,.2f}
- Treatment Date: {data.get('treatment_date', 'Unknown')}
- Number of Services: {len(data.get('procedure_codes', [])) if isinstance(data.get('procedure_codes'), list) else (len(data.get('procedure_codes', '').split(',')) if isinstance(data.get('procedure_codes'), str) else data.get('num_services', 1))}
- Claim Details: {data.get('claim_details', 'No additional details')}

**Billing Context:**
- Average Peer Cost: ${data.get('peer_average_cost', 0):,.2f}
- Provider's Past Claims (last 30 days): {data.get('provider_claim_count_30d', 'Unknown')}
- Patient's Past Claims (last 90 days): {data.get('patient_claim_count_90d', 'Unknown')}
- Claim History: {data.get('claim_history', 'No history provided')}

"""
        
        if rag_context:
            prompt += f"""
**Similar Fraud Patterns (RAG Context):**
{rag_context}

"""
        
        prompt += """
**Fraud Pattern Analysis Checklist:**

1. **Clinical Legitimacy Impact:**
   - If Stage 1 score < 50: High likelihood of upcoding or unbundling
   - If Stage 1 score < 30: Critical - possible phantom billing or fabricated claims

2. **Cost Analysis:**
   - Compare claim amount to peer average
   - Flag if >200% above peer average (potential upcoding)
   - Flag if >>300% above average (critical overcharging)

3. **Billing Behavior:**
   - Provider claim frequency (>50 claims/month = potential mill)
   - Patient claim frequency (>10 claims/90 days = potential patient complicity)
   - Unusual service bundling or unbundling patterns

4. **Temporal Patterns:**
   - Rapid-fire claims (multiple in one day)
   - End-of-month billing spikes
   - Claims submitted after unusual delays

5. **Service Appropriateness:**
   - Unnecessary procedures based on diagnosis
   - Duplicate billing for same service
   - Phantom billing (services never rendered)

**Fraud Indicators:**
- Upcoding: Higher-level codes than clinically justified
- Unbundling: Separating bundled procedures for higher reimbursement
- Phantom Billing: Billing for services never performed
- Kickback Schemes: Referral patterns suggesting kickbacks
- Patient Steering: Unnecessary referrals to affiliated providers

**CRITICAL: You MUST respond in valid JSON format. The fraud_score MUST be a number between 0-100 (NOT a percentage).**

**Response Format (JSON):**
```json
{
  "fraud_score": <0-100, where 0=legitimate, 100=definite fraud>,
  "risk_level": "<LOW|MEDIUM|HIGH|CRITICAL>",
  "reasoning": "<Detailed fraud analysis considering clinical validation and billing patterns>",
  "risk_factors": ["<List of specific fraud indicators>"],
  "fraud_type": "<Primary fraud type: Upcoding/Unbundling/Phantom/Kickback/None>",
  "recommended_action": "<Approve/Flag for Review/Deny/Investigate>"
}
```

**Scoring Guidelines:**
- 0-25 (LOW): Legitimate claim, minor discrepancies
- 26-50 (MEDIUM): Some concerns, recommend review
- 51-75 (HIGH): Multiple fraud indicators, requires investigation
- 76-100 (CRITICAL): Clear fraud patterns, deny and investigate

**IMPORTANT SCORING RULES:**
- fraud_score MUST be a number between 0 and 100 (NOT a percentage like 300%)
- If you mention percentages in reasoning (e.g., "300% above average"), that's NOT the fraud_score
- The fraud_score is a risk assessment on a 0-100 scale, not a percentage deviation
- Factor in Stage 1 clinical score heavily
- Low clinical legitimacy (< 50) should raise fraud score significantly
- High peer cost deviation (>200%) is a major red flag (but fraud_score still 0-100)
- Multiple fraud indicators = compound the score (but keep it 0-100)

Provide your fraud analysis:"""

        return prompt
    
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
            # Check for OFAC countries
            ofac_warning = build_ofac_risk_warning(data, ['source_country', 'destination_country', 'location'])
            
            # Check for VPN/proxy
            ip_address = str(data.get('ip_address', '')).lower()
            vpn_risk = ""
            if 'vpn' in ip_address or 'proxy' in ip_address or 'tor' in ip_address:
                vpn_risk = "⚠️ WARNING: VPN/Proxy/TOR detected - This is a HIGH-RISK indicator for fraud!"
            
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

CRITICAL FRAUD INDICATORS TO EVALUATE:
{ofac_warning}{vpn_risk}

Transaction Details:
- Transaction ID: {data.get('transaction_id')}
- Type: {data.get('transaction_type')}
- Amount: ${data.get('amount')}
- Source Country: {data.get('source_country')}
- Destination Country: {data.get('destination_country')}
- Account Age: {data.get('account_age_days')} days (NEW accounts < 90 days are HIGH RISK)
- KYC Verified: {data.get('kyc_verified')} (FALSE = HIGH RISK)
- Previously Flagged: {data.get('previously_flagged')}
- Transaction Velocity: {data.get('transaction_velocity', 'N/A')} transactions in 24h
- IP Address: {data.get('ip_address', 'N/A')}
{wallet_info}

SCORING GUIDELINES (STRICT - be conservative and flag suspicious transactions):
- OFAC sanctioned/high-risk countries: Add 40-60 points (CRITICAL if combined with other flags)
- VPN/Proxy/TOR detected: Add 25-30 points
- Unverified KYC: Add 15-20 points
- New account (< 30 days): Add 20-30 points
- High transaction velocity (> 10/day): Add 15-20 points
- Large amounts (> $10,000): Add 15-25 points
- Multiple red flags combined: ALWAYS use HIGH (60-85) or CRITICAL (85-100) scores
- IMPORTANT: If 3+ red flags are present (e.g., OFAC country + VPN + unverified + new account), the score MUST be 70+ (HIGH) or 85+ (CRITICAL). Do NOT assign LOW scores when multiple risk indicators are present.

REQUIRED: Provide a comprehensive fraud analysis with:
1. FRAUD_SCORE: A number from 0-100 (be STRICT - multiple red flags should result in HIGH scores of 60-100)
2. RISK_LEVEL: LOW, MEDIUM, HIGH, or CRITICAL
3. RISK_FACTORS: List 3-5 specific red flags (e.g., OFAC country, VPN, unverified KYC, new account, high velocity)
4. REASONING: Write 3-4 complete sentences explaining:
   - WHY this transaction is flagged (cite ALL red flags: country, VPN, KYC, account age, velocity, amount)
   - WHAT patterns indicate fraud (be specific about the ${data.get('amount')} transaction and all risk indicators)
   - HOW severe the risk is (combine all factors - multiple red flags = HIGH/CRITICAL risk)
   
Format exactly as:
FRAUD_SCORE: [number]
RISK_LEVEL: [level]
RISK_FACTORS: [factor1, factor2, factor3, factor4, factor5]
REASONING: [Write your detailed analysis here. Reference ALL specific red flags: the source country ({data.get('source_country')}), destination country ({data.get('destination_country')}), the IP address ({data.get('ip_address', 'N/A')}), KYC status ({data.get('kyc_verified')}), account age ({data.get('account_age_days')} days), and transaction velocity. Be thorough and specific. If multiple red flags are present, assign a HIGH or CRITICAL score.]
"""
        
        elif sector == 'medical':
            # Check for OFAC countries in provider location, patient location, etc.
            ofac_warning = build_ofac_risk_warning(data, ['provider_location', 'patient_location', 'billing_address', 'service_location'])
            
            return f"""You are a senior healthcare fraud investigator with 15 years of experience in medical billing fraud. Analyze this claim and provide a detailed, professional assessment in plain English. Do NOT generate code or technical syntax.

{rag_section}

CRITICAL FRAUD INDICATORS TO EVALUATE:
{ofac_warning}

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

SCORING GUIDELINES (STRICT - be conservative and flag suspicious claims):
- OFAC sanctioned/high-risk countries: Add 40-60 points (CRITICAL if combined with other flags)
- Unbundling (separating procedures that should be billed together): Add 30-40 points
- Upcoding (billing for more expensive procedures): Add 25-35 points
- Procedure/diagnosis mismatch: Add 20-30 points
- Excessive claim amount (> $50,000): Add 15-25 points
- New provider (< 90 days): Add 15-20 points
- Multiple red flags combined: ALWAYS use HIGH (60-85) or CRITICAL (85-100) scores
- IMPORTANT: If 3+ red flags are present (e.g., OFAC country + upcoding + excessive amount), the score MUST be 70+ (HIGH) or 85+ (CRITICAL). Do NOT assign LOW scores when multiple risk indicators are present.

REQUIRED: Provide a comprehensive fraud analysis with:
1. FRAUD_SCORE: A number from 0-100 (be STRICT - multiple red flags should result in HIGH scores of 60-100)
2. RISK_LEVEL: LOW, MEDIUM, HIGH, or CRITICAL
3. RISK_FACTORS: List 3-5 specific red flags (e.g., OFAC country, unbundling, upcoding, procedure mismatch, excessive amount)
4. REASONING: Write 3-4 complete sentences explaining:
   - WHY this claim is suspicious (cite ALL red flags: country, procedure codes, diagnosis codes, billing patterns)
   - WHAT billing patterns indicate fraud (be specific about the ${data.get('claim_amount')} amount and procedure/diagnosis relationships)
   - HOW severe the fraud risk is (combine all factors - multiple red flags = HIGH/CRITICAL risk)
   
Format exactly as:
FRAUD_SCORE: [number]
RISK_LEVEL: [level]
RISK_FACTORS: [factor1, factor2, factor3, factor4, factor5]
REASONING: [Write your detailed analysis here. Reference ALL specific red flags: the claim amount (${data.get('claim_amount')}), the procedure codes ({data.get('procedure_codes')}), diagnosis codes ({data.get('diagnosis_codes')}), and any location-based risks. Be thorough and specific. If multiple red flags are present, assign a HIGH or CRITICAL score.]
"""
        
        elif sector == 'ecommerce':
            # Calculate price discrepancy for emphasis
            price = float(data.get('price', data.get('amount', 0)) or 0)
            amount = float(data.get('amount', data.get('price', 0)) or 0)
            market_price = float(data.get('market_price', 0) or 0)
            price_discrepancy = ""
            
            # Check listed price vs market price
            if market_price > 0 and price > 0:
                discount_pct = ((market_price - price) / market_price) * 100
                if discount_pct > 50:
                    price_discrepancy = f"⚠️ CRITICAL: Listed price is {discount_pct:.1f}% below market price (${price} vs ${market_price}) - MAJOR RED FLAG!"
                elif discount_pct > 30:
                    price_discrepancy = f"⚠️ WARNING: Listed price is {discount_pct:.1f}% below market price (${price} vs ${market_price})"
            
            # Check if listed price differs significantly from order amount (also suspicious)
            if price > 0 and amount > 0 and price != amount:
                price_diff_pct = abs((price - amount) / max(price, amount)) * 100
                if price_diff_pct > 50:
                    price_discrepancy += f"\n⚠️ CRITICAL: Listed price (${price}) differs significantly from order amount (${amount}) - This is suspicious and indicates potential price manipulation!"
            
            # Check for OFAC countries
            ofac_warning = build_ofac_risk_warning(data, ['shipping_location', 'shipping_address', 'billing_address', 'origin_country'])
            
            # Check for VPN/proxy
            ip_address = str(data.get('ip_address', '')).lower()
            vpn_risk = ""
            if 'vpn' in ip_address or 'proxy' in ip_address or 'tor' in ip_address:
                vpn_risk = "⚠️ WARNING: VPN/Proxy/TOR detected - This is a HIGH-RISK indicator for fraud!"
            
            # Check email verification
            email_verified = data.get('email_verified', False)
            email_risk = ""
            if not email_verified:
                email_risk = "⚠️ WARNING: Email NOT verified - Unverified accounts are HIGH-RISK for fraud!"
            
            # Check reviews for negative indicators
            reviews = str(data.get('reviews', ''))
            review_risk = ""
            negative_keywords = ['scam', 'fraud', 'illegal', 'fake', 'counterfeit', 'do not buy', 'sanction', 'warning']
            if any(keyword in reviews.lower() for keyword in negative_keywords):
                review_risk = "⚠️ CRITICAL: Reviews contain fraud warnings (scam, illegal, fake, etc.) - This is a MAJOR RED FLAG!"
            
            return f"""You are a senior e-commerce fraud prevention specialist with expertise in online marketplace scams. Analyze this transaction and provide a detailed, professional assessment in plain English. Do NOT generate code or technical syntax.

{rag_section}

CRITICAL FRAUD INDICATORS TO EVALUATE:
{ofac_warning}{price_discrepancy}
{vpn_risk}
{email_risk}
{review_risk}

Transaction Details:
- Order ID: {data.get('order_id')}
- Seller Age: {data.get('seller_age_days', 'N/A')} days (NEW sellers < 90 days are HIGH RISK)
- Listed Price: ${data.get('price', data.get('amount', 'N/A'))}
- Market Price: ${data.get('market_price', 'N/A')}
- Order Amount: ${data.get('amount', data.get('price', 'N/A'))}
- Shipping Address: {data.get('shipping_address', 'N/A')}
- Billing Address: {data.get('billing_address', 'N/A')}
- Payment Method: {data.get('payment_method', 'N/A')}
- IP Address: {data.get('ip_address', 'N/A')}
- Email Verified: {data.get('email_verified', False)} (FALSE = HIGH RISK)
- Reviews: {data.get('reviews', 'N/A')}
- Shipping Location: {data.get('shipping_location', 'N/A')}
- Product Details: {data.get('product_details', 'N/A')}

SCORING GUIDELINES (STRICT - be conservative and flag suspicious transactions):
- OFAC sanctioned/high-risk countries: Add 40-60 points (CRITICAL if combined with other flags)
- Price >50% below market: Add 40-50 points
- VPN/Proxy/TOR detected: Add 25-30 points
- Unverified email: Add 15-20 points
- Negative reviews (scam, fraud, illegal): Add 30-40 points
- New seller (< 30 days): Add 20-30 points
- Multiple red flags combined: ALWAYS use HIGH (60-85) or CRITICAL (85-100) scores
- IMPORTANT: If 3+ red flags are present (e.g., high-risk country + VPN + unverified + negative reviews), the score MUST be 70+ (HIGH) or 85+ (CRITICAL). Do NOT assign LOW scores when multiple risk indicators are present.

REQUIRED: Provide a comprehensive fraud analysis with:
1. FRAUD_SCORE: A number from 0-100 (be STRICT - multiple red flags should result in HIGH scores of 60-100)
2. RISK_LEVEL: LOW, MEDIUM, HIGH, or CRITICAL
3. RISK_FACTORS: List 3-5 specific red flags (e.g., high-risk country, price discrepancy, VPN, unverified email, negative reviews)
4. REASONING: Write 3-4 complete sentences explaining:
   - WHY this order is suspicious (cite ALL red flags: country, price, VPN, email, reviews, seller age)
   - WHAT fraud patterns are present (be specific about the ${data.get('amount')} purchase and all risk indicators)
   - HOW likely this is fraudulent (combine all factors - multiple red flags = HIGH/CRITICAL risk)
   
Format exactly as:
FRAUD_SCORE: [number]
RISK_LEVEL: [level]
RISK_FACTORS: [factor1, factor2, factor3, factor4, factor5]
REASONING: [Write your detailed analysis here. Reference ALL specific red flags: the shipping location ({data.get('shipping_location', 'N/A')}), the price discrepancy (${data.get('price', 'N/A')} vs ${data.get('market_price', 'N/A')}), the email verification status ({data.get('email_verified', False)}), the IP address ({data.get('ip_address', 'N/A')}), and any negative reviews. Be thorough and specific. If multiple red flags are present, assign a HIGH or CRITICAL score.]
"""
        
        elif sector == 'supply_chain':
            # Check for OFAC countries in supplier location, origin country, etc.
            ofac_warning = build_ofac_risk_warning(data, ['supplier_location', 'supplier_country', 'origin_country', 'shipping_location', 'billing_address'])
            
            # Check for documentation and compliance issues
            doc_complete = data.get('documentation_complete', False)
            reg_compliance = data.get('regulatory_compliance', False)
            compliance_risk = ""
            if not doc_complete:
                compliance_risk += "⚠️ WARNING: Documentation incomplete - Missing documentation is a HIGH-RISK indicator for fraud!\n"
            if not reg_compliance:
                compliance_risk += "⚠️ WARNING: Regulatory compliance issues - Non-compliance is a HIGH-RISK indicator!\n"
            
            return f"""You are a senior supply chain fraud investigator with expertise in procurement fraud, kickback schemes, and ghost suppliers. Analyze this order and provide a detailed, professional assessment in plain English. Do NOT generate code or technical syntax.

{rag_section}

CRITICAL FRAUD INDICATORS TO EVALUATE:
{ofac_warning}{compliance_risk}

Order Details:
- Supplier ID: {data.get('supplier_id', 'N/A')}
- Supplier Name: {data.get('supplier_name', 'N/A')}
- Order Amount: ${data.get('order_amount', 'N/A')}
- Order Frequency: {data.get('order_frequency', 'N/A')} per year
- Payment Terms: {data.get('payment_terms', 'N/A')}
- Supplier Age: {data.get('supplier_age_days', 'N/A')} days (NEW suppliers < 90 days are HIGH RISK)
- Price Variance: {data.get('price_variance', 'N/A')}% from market average
- Delivery Variance: {data.get('delivery_variance', 'N/A')}%
- Quality Issues: {data.get('quality_issues', 'N/A')}
- Documentation Complete: {data.get('documentation_complete', False)} (FALSE = HIGH RISK)
- Regulatory Compliance: {data.get('regulatory_compliance', False)} (FALSE = HIGH RISK)
- Order Details: {data.get('order_details', 'N/A')}

SCORING GUIDELINES (STRICT - be conservative and flag suspicious orders):
- OFAC sanctioned/high-risk countries: Add 40-60 points (CRITICAL if combined with other flags)
- Ghost supplier (new, no history): Add 30-40 points
- Price variance > 30%: Add 25-35 points
- Missing documentation: Add 20-30 points
- Regulatory non-compliance: Add 25-35 points
- Quality issues: Add 15-25 points
- Large order amount (> $100,000): Add 15-25 points
- Multiple red flags combined: ALWAYS use HIGH (60-85) or CRITICAL (85-100) scores
- IMPORTANT: If 3+ red flags are present (e.g., OFAC country + ghost supplier + missing docs + price variance), the score MUST be 70+ (HIGH) or 85+ (CRITICAL). Do NOT assign LOW scores when multiple risk indicators are present.

REQUIRED: Provide a comprehensive fraud analysis with:
1. FRAUD_SCORE: A number from 0-100 (be STRICT - multiple red flags should result in HIGH scores of 60-100)
2. RISK_LEVEL: LOW, MEDIUM, HIGH, or CRITICAL
3. RISK_FACTORS: List 3-5 specific red flags (e.g., OFAC country, ghost supplier, price variance, missing docs, compliance issues)
4. REASONING: Write 3-4 complete sentences explaining:
   - WHY this supplier is suspicious (cite ALL red flags: country, supplier age, price variance, documentation, compliance)
   - WHAT procurement fraud patterns are present (be specific about the ${data.get('order_amount')} amount and {data.get('price_variance')}% variance)
   - HOW severe the fraud risk is (combine all factors - multiple red flags = HIGH/CRITICAL risk)
   
Format exactly as:
FRAUD_SCORE: [number]
RISK_LEVEL: [level]
RISK_FACTORS: [factor1, factor2, factor3, factor4, factor5]
REASONING: [Write your detailed analysis here. Reference ALL specific red flags: the supplier location, the ${data.get('order_amount')} order from a {data.get('supplier_age_days')}-day-old supplier with {data.get('price_variance')}% price variance, documentation status ({data.get('documentation_complete', False)}), and compliance status ({data.get('regulatory_compliance', False)}). Explain specific kickback or ghost supplier indicators. Be thorough and specific. If multiple red flags are present, assign a HIGH or CRITICAL score.]
"""
        
        return ""
    
    def _parse_model_response(self, text: str, sector: str, data: Dict[str, Any], is_clinical_stage: bool = False) -> Dict[str, Any]:
        """
        Parse LLM response to extract structured fraud analysis or clinical validation.
        
        Args:
            is_clinical_stage: If True, parse as clinical legitimacy validation (Stage 1)
                             If False, parse as fraud detection (Stage 2 or single-stage)
        """
        import re
        import json
        
        # ============================================================
        # STAGE 1: CLINICAL LEGITIMACY PARSING (MedGemma)
        # ============================================================
        if is_clinical_stage:
            # Try to extract JSON response first
            json_match = re.search(r'\{[^}]*"clinical_legitimacy_score"[^}]*\}', text, re.DOTALL)
            if json_match:
                try:
                    parsed_json = json.loads(json_match.group(0))
                    return {
                        "clinical_legitimacy_score": parsed_json.get("clinical_legitimacy_score", 50),
                        "reasoning": parsed_json.get("reasoning", text),
                        "risk_factors": parsed_json.get("risk_factors", []),
                        "diagnosis_procedure_match": parsed_json.get("diagnosis_procedure_match", "Unknown"),
                        "provider_specialty_appropriate": parsed_json.get("provider_specialty_appropriate", "Unknown"),
                        "medical_necessity": parsed_json.get("medical_necessity", "Unknown")
                    }
                except json.JSONDecodeError:
                    pass
            
            # Fallback: regex extraction for structured format
            score_match = re.search(r'clinical[_\s]legitimacy[_\s]score["\']?\s*:\s*(\d+)', text, re.IGNORECASE)
            if score_match:
                clinical_score = int(score_match.group(1))
            else:
                # Try to find any number 0-100 that might be a score
                pct_match = re.search(r'(\d+)\s*(?:%|out of 100|/100)', text, re.IGNORECASE)
                if pct_match:
                    clinical_score = int(pct_match.group(1))
                else:
                    # Infer score from text sentiment (MedGemma returns free-form text)
                    text_lower = text.lower()
                    if any(word in text_lower for word in ['appropriate', 'coherent', 'standard', 'normal', 'typical', 'reasonable']):
                        if any(word in text_lower for word in ['highly', 'very', 'completely', 'fully']):
                            clinical_score = 85  # Highly appropriate
                        elif any(word in text_lower for word in ['somewhat', 'mostly', 'generally']):
                            clinical_score = 70  # Mostly appropriate
                        else:
                            clinical_score = 75  # Appropriate
                    elif any(word in text_lower for word in ['inappropriate', 'incompatible', 'unusual', 'concerning', 'red flag']):
                        if any(word in text_lower for word in ['highly', 'very', 'completely', 'definitely']):
                            clinical_score = 15  # Highly inappropriate
                        elif any(word in text_lower for word in ['somewhat', 'possibly', 'potentially']):
                            clinical_score = 40  # Somewhat inappropriate
                        else:
                            clinical_score = 30  # Inappropriate
                    elif any(word in text_lower for word in ['insufficient', 'limited', 'unclear', 'unknown', 'impossible']):
                        clinical_score = 25  # Cannot assess
                    else:
                        clinical_score = 50  # Neutral/unknown
            
            # Extract clinical reasoning
            reasoning_match = re.search(r'["\']?reasoning["\']?\s*:\s*["\'](.+?)["\']', text, re.IGNORECASE | re.DOTALL)
            if reasoning_match:
                reasoning = reasoning_match.group(1).strip()
            else:
                reasoning = text
            
            # Extract risk factors
            factors_match = re.search(r'["\']?risk[_\s]factors["\']?\s*:\s*\[([^\]]+)\]', text, re.IGNORECASE)
            if factors_match:
                risk_factors = [f.strip(' "\'') for f in factors_match.group(1).split(',')]
            else:
                risk_factors = []
            
            return {
                "clinical_legitimacy_score": clinical_score,
                "reasoning": self._clean_reasoning(reasoning),
                "risk_factors": risk_factors,
                "diagnosis_procedure_match": "Unknown",
                "provider_specialty_appropriate": "Unknown",
                "medical_necessity": "Unknown"
            }
        
        # ============================================================
        # STAGE 2 / SINGLE-STAGE: FRAUD DETECTION PARSING
        # ============================================================
        
        # Try to extract JSON response first (most reliable)
        # Look for JSON objects that might contain fraud_score (including code blocks)
        json_patterns = [
            r'```json\s*(\{.*?"fraud_score".*?\})\s*```',  # JSON in code block
            r'```\s*(\{.*?"fraud_score".*?\})\s*```',  # JSON in generic code block
            r'(\{.*?"fraud_score".*?\})',  # JSON object anywhere
        ]
        
        fraud_score = None
        for pattern in json_patterns:
            json_match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if json_match:
                try:
                    json_str = json_match.group(1).strip()
                    parsed_json = json.loads(json_str)
                    fraud_score = parsed_json.get("fraud_score", None)
                    if fraud_score is not None:
                        # Validate and clamp score to 0-100
                        fraud_score = max(0, min(100, int(fraud_score)))
                        logger.info(f"✅ Extracted fraud_score from JSON: {fraud_score}")
                        break
                except (json.JSONDecodeError, ValueError, TypeError) as e:
                    logger.debug(f"⚠️  Failed to parse JSON fraud_score from pattern {pattern}: {e}")
                    continue
        
        # If JSON parsing failed, try regex extraction
        if fraud_score is None:
            # Try explicit FRAUD_SCORE: pattern first
            score_match = re.search(r'FRAUD[_\s]SCORE["\']?\s*:\s*(\d+)', text, re.IGNORECASE)
            if score_match:
                fraud_score = int(score_match.group(1))
                logger.info(f"✅ Extracted fraud_score from FRAUD_SCORE pattern: {fraud_score}")
            else:
                # Fallback: look for percentage, but ONLY if it's in the 0-100 range
                # This prevents picking up "300%" from reasoning text
                pct_matches = re.findall(r'(\d+)\s*%', text)
                valid_scores = [int(m) for m in pct_matches if 0 <= int(m) <= 100]
                if valid_scores:
                    # Use the first valid score found (usually the fraud score)
                    fraud_score = valid_scores[0]
                    logger.info(f"✅ Extracted fraud_score from percentage: {fraud_score}")
                else:
                    # Last resort: look for "score: X" or "score X" where X is 0-100
                    score_patterns = [
                        r'["\']?score["\']?\s*:\s*(\d+)',
                        r'score\s+of\s+(\d+)',
                        r'score\s+(\d+)',
                    ]
                    for pattern in score_patterns:
                        match = re.search(pattern, text, re.IGNORECASE)
                        if match:
                            candidate = int(match.group(1))
                            if 0 <= candidate <= 100:
                                fraud_score = candidate
                                logger.info(f"✅ Extracted fraud_score from score pattern: {fraud_score}")
                                break
                    
                    if fraud_score is None:
                        fraud_score = 50  # Default fallback
                        logger.warning(f"⚠️  Could not extract fraud_score, using default: {fraud_score}")
        
        # CRITICAL: Always clamp score to 0-100 range (safety check)
        original_score = fraud_score
        fraud_score = max(0, min(100, int(fraud_score)))
        if original_score != fraud_score:
            logger.warning(f"⚠️  Clamped fraud_score from {original_score} to {fraud_score} (must be 0-100)")
        
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
    
    def _get_risk_level(self, fraud_score: float) -> str:
        """Calculate risk level from fraud score"""
        if fraud_score < 30:
            return "LOW"
        elif fraud_score < 60:
            return "MEDIUM"
        elif fraud_score < 85:
            return "HIGH"
        else:
            return "CRITICAL"
    
    def _fallback_analysis(self, sector: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Rule-based fallback when API fails"""
        logger.info(f"Using rule-based fallback for sector: {sector}")
        
        # Import the original rule-based logic
        from app.langgraph_router import analyze_fraud_rule_based
        return analyze_fraud_rule_based(sector, data)

