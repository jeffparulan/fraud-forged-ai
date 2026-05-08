"""
LLM configuration: sector model mappings and constants.

MODEL ALIGNMENT (Updated May 2026):
- Banking:      Qwen3-32B (HF Inference via Novita/Together/Fireworks) - Financial reasoning, AML patterns
- Medical:      TWO-STAGE PIPELINE
  ├─ Stage 1:  MedGemma-27B (HF Inference via Featherless AI) - Clinical legitimacy validation
  │            Google's medical-specialist 27B, trained on PMC-OA + clinical reasoning benchmarks
  │            GATED: user must accept Health AI Developer Foundation terms at
  │            huggingface.co/google/medgemma-27b-text-it before first use.
  │            Fallback if gated/unavailable: GPT-OSS-120B (OpenRouter FREE)
  └─ Stage 2:  Qwen3-32B (HF Inference) - Fraud pattern analysis
- E-commerce:   Nemotron-Super-120B (OpenRouter FREE, Finance #24) - Calibrated marketplace fraud scoring
- Supply Chain: Nemotron-Super-120B (OpenRouter FREE, Finance #24) - Calibrated logistics fraud scoring
  NOTE: Tencent Hy3 Preview was replaced because it consistently returns neutral/medium scores
        (~50) regardless of risk level, making it unreliable for fraud detection.
        Nemotron-Super-120B provides properly calibrated risk scores.

FALLBACK CHAIN (OpenRouter FREE tier only):
1. OpenAI GPT-OSS-120B  (Finance #20) - 120B MoE, high reasoning (also Medical Stage 1 fallback)
2. Tencent Hy3 Preview  (Finance #4)  - Fallback only (neutral scoring bias noted)
3. Google Gemma-4-31B / Meta Llama-3.3-70B  - broad general fallback
"""
from typing import Dict, Any, List

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
    # ──────────────────────────────────────────────────────────────────────────
    # BANKING / CRYPTO
    # Primary: Qwen3-32B via HF Inference (Novita / Together / Fireworks)
    #   → Dense 32B, Qwen's 2026 flagship, strong financial reasoning & AML
    # Fallbacks: fully-free OpenRouter models ranked by Finance leaderboard
    # ──────────────────────────────────────────────────────────────────────────
    "banking": {
        "primary": {"provider": "hf", "model": "Qwen/Qwen3-32B"},
        "fallbacks": [
            # Finance #20 — 120B MoE, configurable reasoning depth
            {"provider": "openrouter", "model": "openai/gpt-oss-120b:free"},
            # Finance #4  — Tencent Hy3, highest free Finance ranking
            {"provider": "openrouter", "model": "tencent/hy3-preview:free"},
            # Solid general fallback (updated from 3.1 → 3.3)
            {"provider": "openrouter", "model": "meta-llama/llama-3.3-70b-instruct:free"},
        ],
    },

    # ──────────────────────────────────────────────────────────────────────────
    # HEALTHCARE / MEDICAL CLAIMS  — Two-stage pipeline
    # Stage 1 (Clinical): MedGemma-27B (HF Inference via Featherless AI)
    #   → Google's medical-specialist LLM trained on PMC-OA + clinical benchmarks
    #   → GATED: must accept Health AI Developer Foundation terms at
    #     huggingface.co/google/medgemma-27b-text-it (access granted immediately)
    #   → If gated/unavailable, orchestrator falls through to GPT-OSS-120B fallback
    # Stage 2 (Fraud):    Qwen3-32B (HF Inference) - Fraud pattern analysis
    # ──────────────────────────────────────────────────────────────────────────
    "medical": {
        "two_stage": True,
        "stage1": {
            "name": "Clinical Legitimacy Validation",
            "provider": "hf",
            "model": "google/medgemma-27b-text-it",
            "purpose": "Validate medical coherence, diagnosis-procedure compatibility, clinical plausibility"
        },
        "stage2": {
            "name": "Fraud Pattern Analysis",
            "provider": "hf",
            "model": "Qwen/Qwen3-32B",
            "purpose": "Analyze billing behavior, cost outliers, peer deviation, fraud patterns"
        },
        "fallbacks": [
            # Stage 1 fallback if MedGemma is gated/unavailable — Finance #20, 120B MoE
            {"provider": "openrouter", "model": "openai/gpt-oss-120b:free"},
            # Finance #4, Health #34
            {"provider": "openrouter", "model": "tencent/hy3-preview:free"},
            # Finance #24 — NVIDIA 120B hybrid MoE, 1M context
            {"provider": "openrouter", "model": "nvidia/nemotron-3-super-120b-a12b:free"},
        ],
    },

    # ──────────────────────────────────────────────────────────────────────────
    # E-COMMERCE
    # Primary: Nemotron-Super-120B (Finance #24 free) — replaces Tencent Hy3 Preview
    #   → Tencent Hy3 consistently returned neutral/medium scores (~50) regardless
    #     of fraud severity. Nemotron-Super-120B delivers properly calibrated
    #     fraud risk scores across the full severity spectrum.
    #   → 120B hybrid MoE (A12B active), 1M context window, strong instruction following
    # ──────────────────────────────────────────────────────────────────────────
    "ecommerce": {
        "primary": {"provider": "openrouter", "model": "nvidia/nemotron-3-super-120b-a12b:free"},
        "fallbacks": [
            # Finance #20 — 120B MoE, high reasoning
            {"provider": "openrouter", "model": "openai/gpt-oss-120b:free"},
            # Finance #4 — kept as fallback only
            {"provider": "openrouter", "model": "tencent/hy3-preview:free"},
            # 30.7B dense multimodal, 262K context
            {"provider": "openrouter", "model": "google/gemma-4-31b-it:free"},
        ],
    },

    # ──────────────────────────────────────────────────────────────────────────
    # SUPPLY CHAIN / LOGISTICS
    # Primary: Nemotron-Super-120B — 1M context ideal for long logistics documents
    #   → Same reasoning for replacing Tencent Hy3 as E-commerce (neutral bias)
    # ──────────────────────────────────────────────────────────────────────────
    "supply_chain": {
        "primary": {"provider": "openrouter", "model": "nvidia/nemotron-3-super-120b-a12b:free"},
        "fallbacks": [
            {"provider": "openrouter", "model": "openai/gpt-oss-120b:free"},
            {"provider": "openrouter", "model": "tencent/hy3-preview:free"},
            {"provider": "openrouter", "model": "google/gemma-4-31b-it:free"},
        ],
    },
}


def get_sector_model_candidates(sector: str) -> List[Dict[str, str]]:
    """
    Return ordered model candidates for a sector.

    For single-stage sectors this is primary + fallbacks.
    For two-stage sectors this is stage1 + stage2 + fallbacks.
    """
    model_config = SECTOR_MODELS.get(sector, {})
    candidates: List[Dict[str, str]] = []

    if model_config.get("two_stage"):
        stage1 = model_config.get("stage1")
        stage2 = model_config.get("stage2")
        if stage1:
            candidates.append(
                {
                    "provider": stage1.get("provider", ""),
                    "model": stage1.get("model", ""),
                    "role": "stage1",
                }
            )
        if stage2:
            candidates.append(
                {
                    "provider": stage2.get("provider", ""),
                    "model": stage2.get("model", ""),
                    "role": "stage2",
                }
            )
    else:
        primary = model_config.get("primary")
        if primary:
            candidates.append(
                {
                    "provider": primary.get("provider", ""),
                    "model": primary.get("model", ""),
                    "role": "primary",
                }
            )

    for fallback in model_config.get("fallbacks", []):
        candidates.append(
            {
                "provider": fallback.get("provider", ""),
                "model": fallback.get("model", ""),
                "role": "fallback",
            }
        )

    return [c for c in candidates if c.get("provider") and c.get("model")]

# Sector-specific location fields for OFAC checks
SECTOR_LOCATION_FIELDS: Dict[str, list] = {
    "banking": ["source_country", "destination_country", "location"],
    "medical": ["provider_location", "patient_location", "billing_address", "service_location"],
    "ecommerce": ["shipping_location", "shipping_address", "billing_address", "origin_country"],
    "supply_chain": ["supplier_location", "supplier_country", "origin_country", "shipping_location", "billing_address"],
}
