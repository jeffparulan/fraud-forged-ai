"""
API security: optional API-key auth and in-memory rate limiting.

Auth is opt-in: set FRAUDFORGE_API_KEY to require an X-API-Key header on
analysis endpoints. Leave it unset for open demo deployments.

Rate limiting is a per-IP sliding window held in process memory. That is
sufficient for a single Cloud Run instance / demo; swap for Redis or an API
gateway if you scale horizontally.
"""
import os
import time
import threading
import logging
from collections import defaultdict, deque

from fastapi import Header, HTTPException, Request

logger = logging.getLogger(__name__)

RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "10"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))


async def require_api_key(x_api_key: str = Header(default=None)) -> None:
    """Reject the request if an API key is configured and doesn't match."""
    configured_key = os.getenv("FRAUDFORGE_API_KEY")
    if not configured_key:
        return  # auth disabled (demo mode)
    if x_api_key != configured_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


class RateLimiter:
    """Per-client sliding-window rate limiter (in-memory, thread-safe)."""

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, client_id: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            hits = self._hits[client_id]
            while hits and hits[0] < cutoff:
                hits.popleft()
            if len(hits) >= self.max_requests:
                return False
            hits.append(now)
            return True


_rate_limiter = RateLimiter(RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW_SECONDS)


def _client_ip(request: Request) -> str:
    # Cloud Run puts the real client IP first in X-Forwarded-For
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def enforce_rate_limit(request: Request) -> None:
    """FastAPI dependency: throttle analysis requests per client IP."""
    client_id = _client_ip(request)
    if not _rate_limiter.check(client_id):
        logger.warning(f"Rate limit exceeded for {client_id}")
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {RATE_LIMIT_REQUESTS} requests per {RATE_LIMIT_WINDOW_SECONDS}s. Please slow down.",
        )
