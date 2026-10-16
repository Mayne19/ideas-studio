"""Limiteur de débit en mémoire pour les routes d'authentification.

Fenêtre glissante par clé (IP + email, et IP seule). Suffisant pour le
déploiement actuel (une seule réplique Railway, --workers 1, voir
railway.toml) : avec plusieurs processus, chaque processus aurait son propre
compteur et il faudrait passer à un stockage partagé (Redis, Postgres).

L'IP vient de request.client.host, déjà corrigée par uvicorn
--proxy-headers derrière le proxy Railway.
"""
from __future__ import annotations

import threading
import time
from collections import deque

from fastapi import HTTPException, Request


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def hit(self, key: str, limit: int, window_seconds: float, now: float | None = None) -> float | None:
        """Enregistre une tentative. Retourne None si elle est autorisée,
        sinon le nombre de secondes avant la prochaine tentative possible."""
        now = time.monotonic() if now is None else now
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and hits[0] <= now - window_seconds:
                hits.popleft()
            if len(hits) >= limit:
                return max(1.0, hits[0] + window_seconds - now)
            hits.append(now)
            if len(self._hits) > 10_000:
                self._purge(now, window_seconds)
            return None

    def _purge(self, now: float, window_seconds: float) -> None:
        for key in [k for k, v in self._hits.items() if not v or v[-1] <= now - window_seconds]:
            self._hits.pop(key, None)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


auth_limiter = SlidingWindowLimiter()

# (tentatives max, fenêtre en secondes) par (IP + email) puis par IP seule.
AUTH_LIMITS: dict[str, tuple[tuple[int, int], tuple[int, int]]] = {
    "login": ((10, 300), (30, 300)),
    "register": ((3, 3600), (10, 3600)),
    "forgot-password": ((3, 900), (10, 900)),
}


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def enforce_auth_rate_limit(request: Request, action: str, email: str | None) -> None:
    """Lève HTTPException(429) si la limite de l'action est atteinte, pour ce
    couple IP + email ou pour l'IP toutes adresses confondues."""
    per_email, per_ip = AUTH_LIMITS[action]
    ip = client_ip(request)
    normalized_email = (email or "").strip().lower()
    for key, (limit, window) in (
        (f"{action}:{ip}:{normalized_email}", per_email),
        (f"{action}:{ip}", per_ip),
    ):
        retry_after = auth_limiter.hit(key, limit, window)
        if retry_after is not None:
            raise HTTPException(
                status_code=429,
                detail="Trop de tentatives. Réessayez dans quelques minutes.",
                headers={"Retry-After": str(int(retry_after))},
            )
