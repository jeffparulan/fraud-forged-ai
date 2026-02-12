"""
LLM configuration: sector model mappings and constants.

MODEL ALIGNMENT (Cost-Optimized Strategy):
- Banking: Qwen2.5-72B-Instruct (HF Pro) - Financial reasoning, AML patterns
- Medical: TWO-STAGE PIPELINE (HF Inference API)
  ├─ Stage 1: MedGemma-4B-IT (Clinical legitimacy validation)
  └─ Stage 2: Qwen2.5-72B-Instruct (Fraud pattern analysis)
- E-commerce: Nemotron-2 (12B VL) (OpenRouter FREE) - Refund abuse, seller manipulation
- Supply Chain: Nemotron-2 (12B VL) (OpenRouter FREE) - Temporal reasoning, logistics
"""
from typing import Dict, Any

# OFAC (Office of Foreign Assets Control) Sanctioned Countries and High-Risk Fraud Countries
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

# Sector model configuration (provider-aware)
# provider: "hf" | "openrouter" | "hf_space" | "vertex"
SECTOR_MODELS: Dict[str, Dict[str, Any]] = {
    "banking": {
        "primary": {"provider": "hf", "model": "Qwen/Qwen2.5-72B-Instruct"},
        "fallbacks": [
            {"provider": "openrouter", "model": "nvidia/nemotron-3-nano-30b-a3b:free"},
            {"provider": "openrouter", "model": "meta-llama/llama-3.1-70b-instruct:free"},
        ],
    },
    "medical": {
        "two_stage": True,
        "stage1": {
            "name": "Clinical Legitimacy Validation",
            "provider": "hf_space",
            "model": "ironjeffe/google-medgemma-4b-it",
            "purpose": "Validate medical coherence, diagnosis-procedure compatibility, clinical plausibility"
        },
        "stage2": {
            "name": "Fraud Pattern Analysis",
            "provider": "hf",
            "model": "Qwen/Qwen2.5-72B-Instruct",
            "purpose": "Analyze billing behavior, cost outliers, peer deviation, fraud patterns"
        },
        "fallbacks": [
            {"provider": "openrouter", "model": "nvidia/nemotron-3-nano-30b-a3b:free"},
        ],
    },
    "ecommerce": {
        "primary": {"provider": "openrouter", "model": "nvidia/nemotron-nano-12b-v2-vl:free"},
        "fallbacks": [
            {"provider": "hf", "model": "Qwen/Qwen2.5-72B-Instruct"},
            {"provider": "openrouter", "model": "nvidia/nemotron-3-nano-30b-a3b:free"},
        ],
    },
    "supply_chain": {
        "primary": {"provider": "openrouter", "model": "nvidia/nemotron-nano-12b-v2-vl:free"},
        "fallbacks": [
            {"provider": "hf", "model": "Qwen/Qwen2.5-72B-Instruct"},
            {"provider": "openrouter", "model": "nvidia/nemotron-3-nano-30b-a3b:free"},
        ],
    },
}

# Sector-specific location fields for OFAC checks
SECTOR_LOCATION_FIELDS: Dict[str, list] = {
    "banking": ["source_country", "destination_country", "location"],
    "medical": ["provider_location", "patient_location", "billing_address", "service_location"],
    "ecommerce": ["shipping_location", "shipping_address", "billing_address", "origin_country"],
    "supply_chain": ["supplier_location", "supplier_country", "origin_country", "shipping_location", "billing_address"],
}
