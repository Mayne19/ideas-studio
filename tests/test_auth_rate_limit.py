"""Limiteur de débit des routes d'authentification (hors ligne)."""
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.core.rate_limit import SlidingWindowLimiter, auth_limiter, enforce_auth_rate_limit


def test_sliding_window_blocks_then_recovers():
    limiter = SlidingWindowLimiter()
    assert limiter.hit("k", 2, 60, now=0) is None
    assert limiter.hit("k", 2, 60, now=1) is None
    assert limiter.hit("k", 2, 60, now=2) is not None
    assert limiter.hit("k", 2, 60, now=61) is None


def test_login_limited_per_ip_and_email():
    auth_limiter.reset()
    request = SimpleNamespace(client=SimpleNamespace(host="203.0.113.7"))
    for _ in range(10):
        enforce_auth_rate_limit(request, "login", "a@example.com")
    with pytest.raises(HTTPException) as exc:
        enforce_auth_rate_limit(request, "login", "A@example.com ")
    assert exc.value.status_code == 429
    assert "Retry-After" in exc.value.headers
    # Une autre adresse depuis la même IP reste autorisée (limite IP plus haute).
    enforce_auth_rate_limit(request, "login", "b@example.com")
    auth_limiter.reset()
