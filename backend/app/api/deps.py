"""Dependency injection for API endpoints."""
from typing import Dict, Any

# app_state is set by main.py lifespan - endpoints receive it via get_app_state
_app_state: Dict[str, Any] = {}

# Kill switch - set by budget alert handler in main
KILL_SWITCH_ACTIVE = False


def set_kill_switch(active: bool) -> None:
    """Set kill switch state (called from budget alert handler)."""
    global KILL_SWITCH_ACTIVE
    KILL_SWITCH_ACTIVE = active


def set_app_state(state: Dict[str, Any]) -> None:
    """Set the shared app state (called from main.py)."""
    global _app_state
    _app_state = state


def get_app_state() -> Dict[str, Any]:
    """Get the shared app state for dependency injection."""
    return _app_state


def get_router():
    """Get LangGraph router from app state."""
    state = get_app_state()
    if "router" not in state:
        return None
    return state["router"]
