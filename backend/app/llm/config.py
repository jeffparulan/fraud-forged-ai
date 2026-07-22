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


def reload_models_config() -> Dict[str, Any]:
    """Clear cache and reload (tests / hot-edit)."""
    load_models_config.cache_clear()
    return load_models_config()


def _resolve_ref(ref: str, catalog: Dict[str, Any]) -> Dict[str, str]:
    entry = catalog.get(ref)
    if not entry:
        raise KeyError(f"Unknown model ref '{ref}' in models.yaml catalog")
    return {
        "provider": entry["provider"],
        "model": entry["id"],
        "display": entry.get("display") or entry["id"],
        "brand": entry.get("brand", ""),
        "ref": ref,
    }


def _build_sector_models(raw: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    catalog = raw["catalog"]
    sectors: Dict[str, Dict[str, Any]] = {}

    for sector, cfg in (raw.get("sectors") or {}).items():
        fallbacks = [
            {"provider": r["provider"], "model": r["model"]}
            for ref in cfg.get("fallbacks") or []
            for r in [_resolve_ref(ref, catalog)]
        ]

        if cfg.get("two_stage"):
            s1 = cfg["stage1"]
            s2 = cfg["stage2"]
            r1 = _resolve_ref(s1["ref"], catalog)
            r2 = _resolve_ref(s2["ref"], catalog)
            sectors[sector] = {
                "two_stage": True,
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
                },
                "stage2": {
                    "name": s2.get("name", "Stage 2"),
                    "provider": r2["provider"],
                    "model": r2["model"],
                    "display": r2["display"],
                    "purpose": s2.get("purpose", ""),
                },
                "fallbacks": fallbacks,
            }
        else:
            primary = _resolve_ref(cfg["primary"], catalog)
            sectors[sector] = {
                "two_stage": False,
                "label": cfg.get("label", sector),
                "route_display": cfg.get("route_display", primary["display"]),
                "ui_model": cfg.get("ui_model") or cfg.get("route_display", primary["display"]),
                "blurb": cfg.get("blurb", ""),
                "primary": {
                    "provider": primary["provider"],
                    "model": primary["model"],
                    "display": primary["display"],
                },
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
    return cfg.get("route_display") or "Llama-3.3-70B (OpenRouter FREE fallback)"


def get_sector_ui_model(sector: str) -> str:
    """Short UI label for sector cards."""
    cfg = SECTOR_MODELS.get(sector) or {}
    return cfg.get("ui_model") or get_sector_route_display(sector)


def get_sector_label(sector: str) -> str:
    cfg = SECTOR_MODELS.get(sector) or {}
    return cfg.get("label") or sector


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
    }.get(provider, provider)

    if is_fallback and fallback_number is not None:
        return f"{display_name} (Fallback #{fallback_number} - {provider_display})"
    return f"{display_name} ({provider_display})" if provider in ("hf", "openrouter") else display_name


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
