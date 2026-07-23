"""
LLM configuration loader.

Single source of truth: app/llm/models.yaml
This module only loads + exposes typed helpers — do not hardcode model IDs here.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)

_MODELS_YAML = Path(__file__).with_name("models.yaml")

# OFAC / high-risk country list (domain data, not model routing)
OFAC_SANCTIONED_COUNTRIES = [
    "cuba", "iran", "north korea", "syria", "crimea", "donetsk", "luhansk",
    "russia", "belarus", "venezuela", "myanmar", "burma", "sudan", "south sudan",
    "libya", "yemen", "somalia", "central african republic", "democratic republic of congo",
    "congo", "zimbabwe", "mali", "burkina faso", "niger",
    "nigeria", "ghana", "cameroon", "ivory coast", "senegal", "togo", "benin",
    "philippines", "indonesia", "malaysia", "thailand", "vietnam", "pakistan",
    "bangladesh", "romania", "bulgaria", "ukraine", "moldova", "albania",
    "serbia", "bosnia", "macedonia", "montenegro", "kosovo",
    "west africa", "east africa", "balkans", "eastern europe",
]


@lru_cache(maxsize=1)
def load_models_config() -> Dict[str, Any]:
    """Load and cache models.yaml."""
    if not _MODELS_YAML.exists():
        raise FileNotFoundError(f"Missing model config: {_MODELS_YAML}")
    with _MODELS_YAML.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not data.get("catalog") or not data.get("sectors"):
        raise ValueError("models.yaml must define 'catalog' and 'sectors'")
    return data


def _resolve_ref(ref: str, catalog: Dict[str, Any]) -> Dict[str, Any]:
    entry = catalog.get(ref)
    if not entry:
        raise KeyError(f"Unknown model ref '{ref}' in models.yaml catalog")
    resolved: Dict[str, Any] = {
        "provider": entry["provider"],
        "model": entry["id"],
        "display": entry.get("display") or entry["id"],
        "brand": entry.get("brand", ""),
        "ref": ref,
    }
    # Optional HF Inference Providers partner (e.g. featherless-ai for MedGemma)
    if entry.get("hf_provider"):
        resolved["hf_provider"] = entry["hf_provider"]
    # Optional Gradio Space API path (e.g. /analyze_claim)
    if entry.get("space_api_name"):
        resolved["space_api_name"] = entry["space_api_name"]
    return resolved


def _build_sector_models(raw: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    catalog = raw["catalog"]
    sectors: Dict[str, Dict[str, Any]] = {}

    for sector, cfg in (raw.get("sectors") or {}).items():
        fallbacks = []
        for ref in cfg.get("fallbacks") or []:
            r = _resolve_ref(ref, catalog)
            fb: Dict[str, Any] = {"provider": r["provider"], "model": r["model"]}
            if r.get("hf_provider"):
                fb["hf_provider"] = r["hf_provider"]
            if r.get("display"):
                fb["display"] = r["display"]
            fallbacks.append(fb)

        if cfg.get("two_stage"):
            s1 = cfg["stage1"]
            s2 = cfg["stage2"]
            r1 = _resolve_ref(s1["ref"], catalog)
            r2 = _resolve_ref(s2["ref"], catalog)
            sectors[sector] = {
                "two_stage": True,
                # When true, Stage 1 failure continues to Stage 2 instead of
                # jumping straight to catalog fallbacks.
                "stage1_optional": bool(cfg.get("stage1_optional", False)),
                "label": cfg.get("label", sector),
                "route_display": cfg.get("route_display", ""),
                "ui_model": cfg.get("ui_model") or cfg.get("route_display", ""),
                "blurb": cfg.get("blurb", ""),
                "stage1": {
                    "name": s1.get("name", "Stage 1"),
                    "provider": r1["provider"],
                    "model": r1["model"],
                    "display": r1["display"],
                    "purpose": s1.get("purpose", ""),
                    **({"hf_provider": r1["hf_provider"]} if r1.get("hf_provider") else {}),
                    **({"space_api_name": r1["space_api_name"]} if r1.get("space_api_name") else {}),
                },
                "stage2": {
                    "name": s2.get("name", "Stage 2"),
                    "provider": r2["provider"],
                    "model": r2["model"],
                    "display": r2["display"],
                    "purpose": s2.get("purpose", ""),
                    **({"hf_provider": r2["hf_provider"]} if r2.get("hf_provider") else {}),
                    **({"space_api_name": r2["space_api_name"]} if r2.get("space_api_name") else {}),
                },
                "fallbacks": fallbacks,
            }
        else:
            primary = _resolve_ref(cfg["primary"], catalog)
            primary_cfg: Dict[str, Any] = {
                "provider": primary["provider"],
                "model": primary["model"],
                "display": primary["display"],
            }
            if primary.get("hf_provider"):
                primary_cfg["hf_provider"] = primary["hf_provider"]
            sectors[sector] = {
                "two_stage": False,
                "label": cfg.get("label", sector),
                "route_display": cfg.get("route_display", primary["display"]),
                "ui_model": cfg.get("ui_model") or cfg.get("route_display", primary["display"]),
                "blurb": cfg.get("blurb", ""),
                "primary": primary_cfg,
                "fallbacks": fallbacks,
            }
    return sectors


# Eager load so import failures surface at startup
_RAW = load_models_config()
SECTOR_MODELS: Dict[str, Dict[str, Any]] = _build_sector_models(_RAW)
SECTOR_LOCATION_FIELDS: Dict[str, list] = dict(_RAW.get("location_fields") or {})
INFERENCE_DEFAULTS: Dict[str, Any] = dict(_RAW.get("inference") or {})
MODEL_CATALOG: Dict[str, Any] = dict(_RAW.get("catalog") or {})


def get_inference_defaults(provider: str) -> Dict[str, Any]:
    """Return inference knobs for a provider from models.yaml."""
    return dict(INFERENCE_DEFAULTS.get(provider) or {})


def get_sector_route_display(sector: str) -> str:
    """Human-readable model label for decision-trace routing."""
    cfg = SECTOR_MODELS.get(sector) or {}
    return cfg.get("route_display") or "Nemotron-Super (OpenRouter FREE fallback)"


def format_model_name(
    model_name: str,
    provider: str,
    is_fallback: bool = False,
    fallback_number: Optional[int] = None,
) -> str:
    """Map a provider model id to a display name using the YAML catalog."""
    display_name = model_name
    for entry in MODEL_CATALOG.values():
        if entry.get("id") == model_name:
            display_name = entry.get("display") or model_name
            break
    else:
        # Soft fallback for legacy / unexpected ids
        mn = model_name.lower()
        if "qwen3-32b" in mn:
            display_name = "Qwen3-32B"
        elif "medgemma-4b" in mn or "google-medgemma-4b" in mn:
            display_name = "MedGemma-4B"
        elif "medgemma-27b" in mn:
            display_name = "MedGemma-27B"
        elif "nemotron-3-ultra" in mn:
            display_name = "Nemotron-Ultra-550B"
        elif "nemotron-3-super" in mn:
            display_name = "Nemotron-Super-120B"
        elif "nemotron-3-nano-30b" in mn:
            display_name = "Nemotron-3-Nano-30B"
        elif "nemotron-nano-9b" in mn:
            display_name = "Nemotron-Nano-9B"
        else:
            display_name = model_name.split("/")[-1]

    provider_display = {
        "hf": "HF Inference",
        "openrouter": "OpenRouter FREE",
        "hf_space": "HF Space",
        "vertex": "Vertex AI",
        "medgemma_local": "Local",
    }.get(provider, provider)

    if is_fallback and fallback_number is not None:
        return f"{display_name} (Fallback #{fallback_number} - {provider_display})"
    if provider in ("hf", "openrouter", "hf_space", "medgemma_local"):
        return f"{display_name} ({provider_display})"
    return display_name


def get_sector_model_candidates(sector: str) -> List[Dict[str, str]]:
    """Ordered model candidates for a sector (primary/stages + fallbacks)."""
    model_config = SECTOR_MODELS.get(sector, {})
    candidates: List[Dict[str, str]] = []

    if model_config.get("two_stage"):
        for role in ("stage1", "stage2"):
            stage = model_config.get(role)
            if stage:
                candidates.append(
                    {
                        "provider": stage.get("provider", ""),
                        "model": stage.get("model", ""),
                        "display": stage.get("display", ""),
                        "role": role,
                    }
                )
    else:
        primary = model_config.get("primary")
        if primary:
            candidates.append(
                {
                    "provider": primary.get("provider", ""),
                    "model": primary.get("model", ""),
                    "display": primary.get("display", ""),
                    "role": "primary",
                }
            )

    for fallback in model_config.get("fallbacks", []):
        candidates.append(
            {
                "provider": fallback.get("provider", ""),
                "model": fallback.get("model", ""),
                "display": format_model_name(
                    fallback.get("model", ""), fallback.get("provider", "")
                ),
                "role": "fallback",
            }
        )

    return [c for c in candidates if c.get("provider") and c.get("model")]


def build_models_summary() -> Dict[str, Any]:
    """API-ready summary for /api/models (frontend source of truth)."""
    summary: Dict[str, Any] = {}
    for sector, cfg in SECTOR_MODELS.items():
        if cfg.get("two_stage"):
            primary_display = (
                f"{cfg['stage1'].get('display')} → {cfg['stage2'].get('display')}"
            )
            pipeline = "two-stage"
        else:
            primary_display = cfg.get("primary", {}).get("display", "")
            pipeline = "single-stage"

        fallback_displays = [
            format_model_name(f["model"], f["provider"], True, i + 1)
            for i, f in enumerate(cfg.get("fallbacks", []))
        ]
        summary[sector] = {
            "label": cfg.get("label", sector),
            "pipeline": pipeline,
            "primary": cfg.get("ui_model") or primary_display,
            "route_display": cfg.get("route_display") or primary_display,
            "blurb": cfg.get("blurb", ""),
            "fallbacks": fallback_displays,
        }
    return summary
