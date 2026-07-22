"""Tests for API-key auth and rate limiting."""
import pytest
from fastapi import HTTPException

from app.api.security import RateLimiter, require_api_key


class TestRateLimiter:
    def test_allows_up_to_limit(self):
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        assert limiter.check("1.2.3.4") is True
        assert limiter.check("1.2.3.4") is True
        assert limiter.check("1.2.3.4") is True

    def test_blocks_over_limit(self):
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        limiter.check("1.2.3.4")
        limiter.check("1.2.3.4")
        assert limiter.check("1.2.3.4") is False

    def test_clients_are_independent(self):
        limiter = RateLimiter(max_requests=1, window_seconds=60)
        assert limiter.check("1.1.1.1") is True
        assert limiter.check("2.2.2.2") is True
        assert limiter.check("1.1.1.1") is False

    def test_window_expiry(self, monkeypatch):
        import app.api.security as sec

        limiter = RateLimiter(max_requests=1, window_seconds=10)
        fake_now = [1000.0]
        monkeypatch.setattr(sec.time, "monotonic", lambda: fake_now[0])

        assert limiter.check("1.2.3.4") is True
        assert limiter.check("1.2.3.4") is False
        fake_now[0] += 11  # advance past the window
        assert limiter.check("1.2.3.4") is True


class TestRequireApiKey:
    @pytest.mark.asyncio
    async def test_auth_disabled_when_no_key_configured(self, monkeypatch):
        monkeypatch.delenv("FRAUDFORGE_API_KEY", raising=False)
        # Should not raise even without a header
        await require_api_key(x_api_key=None)

    @pytest.mark.asyncio
    async def test_rejects_missing_key(self, monkeypatch):
        monkeypatch.setenv("FRAUDFORGE_API_KEY", "secret-key")
        with pytest.raises(HTTPException) as exc:
            await require_api_key(x_api_key=None)
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_rejects_wrong_key(self, monkeypatch):
        monkeypatch.setenv("FRAUDFORGE_API_KEY", "secret-key")
        with pytest.raises(HTTPException) as exc:
            await require_api_key(x_api_key="wrong")
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_accepts_correct_key(self, monkeypatch):
        monkeypatch.setenv("FRAUDFORGE_API_KEY", "secret-key")
        await require_api_key(x_api_key="secret-key")
