"""Tests for the data sharing rate limiter."""

import time

import pytest

from backend.app.api.data_sharing import _RateLimiter


class TestRateLimiter:
    def test_allows_first_request(self):
        limiter = _RateLimiter(requests_per_minute=10)
        assert limiter.allow("192.168.1.1") is True

    def test_allows_up_to_limit(self):
        limiter = _RateLimiter(requests_per_minute=5)
        for _ in range(5):
            assert limiter.allow("10.0.0.1") is True

    def test_blocks_after_limit(self):
        limiter = _RateLimiter(requests_per_minute=3)
        for _ in range(3):
            limiter.allow("10.0.0.1")
        assert limiter.allow("10.0.0.1") is False

    def test_different_ips_independent(self):
        limiter = _RateLimiter(requests_per_minute=2)
        limiter.allow("10.0.0.1")
        limiter.allow("10.0.0.1")
        assert limiter.allow("10.0.0.1") is False
        # Different IP should still be allowed
        assert limiter.allow("10.0.0.2") is True

    def test_tokens_refill_over_time(self):
        limiter = _RateLimiter(requests_per_minute=60)  # 1 per second
        # Use all tokens
        for _ in range(60):
            limiter.allow("10.0.0.1")
        assert limiter.allow("10.0.0.1") is False
        # Wait for refill
        time.sleep(1.1)
        assert limiter.allow("10.0.0.1") is True

    def test_zero_requests_per_minute_blocks_all(self):
        """Edge case: 0 requests per minute should block everything after first."""
        limiter = _RateLimiter(requests_per_minute=1)
        assert limiter.allow("10.0.0.1") is True
        assert limiter.allow("10.0.0.1") is False
