"""
DEPRECATED: Use app.core.security instead.

Re-export for backward compatibility.
"""
from app.core.security import get_secret, get_huggingface_token

__all__ = ["get_secret", "get_huggingface_token"]
