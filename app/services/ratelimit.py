from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException, Request


class RateLimiter:
    """Janela deslizante em memória. Suficiente para uma instância única."""

    def __init__(self) -> None:
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def allow(self, key: str, limit: int, window_s: float = 60.0) -> bool:
        now = time.monotonic()
        with self._lock:
            hits = [hit for hit in self._hits.get(key, []) if now - hit < window_s]
            if len(hits) >= limit:
                self._hits[key] = hits
                return False
            hits.append(now)
            self._hits[key] = hits
            return True


def enforce(request: Request, name: str, limit: int) -> None:
    settings = request.app.state.settings
    if not settings.rate_limit_enabled:
        return
    host = request.client.host if request.client else "desconhecido"
    key = f"{name}:{host}"
    if not request.app.state.limiter.allow(key, limit):
        raise HTTPException(
            status_code=429,
            detail="Muitas tentativas em pouco tempo. Espere um minuto.",
            headers={"Retry-After": "60"},
        )
