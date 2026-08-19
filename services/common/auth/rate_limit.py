"""Per-tenant in-memory rate limiting (Phase 4.0 interim).

Fixed-window limiter keyed by the verified tenant_id from AuthContext.
Per-instance only — a horizontal scale-out gives each instance its own
window. This is a local-testable interim until Cloud Armor edge
throttling is deployed (Phase 16.0 / gated cloud step).
"""

from __future__ import annotations

import os
import threading
import time

from fastapi import HTTPException

DEFAULT_RATE_LIMIT_PER_MINUTE = 30


class FixedWindowRateLimiter:
    """Thread-safe fixed-window limiter keyed by tenant_id."""

    def __init__(self, limit: int | None = None) -> None:
        self.limit = limit or int(
            os.getenv("RATE_LIMIT_PER_MINUTE", DEFAULT_RATE_LIMIT_PER_MINUTE)
        )
        self._counts: dict[str, tuple[float, int]] = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        """Raise 429 if `key` has exceeded the window budget."""
        now = time.monotonic()
        with self._lock:
            window_start, count = self._counts.get(key, (0.0, 0))
            if now - window_start >= 60.0:
                window_start, count = now, 0
            if count >= self.limit:
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded: {self.limit} requests per minute",
                )
            self._counts[key] = (window_start, count + 1)

    def reset(self) -> None:
        with self._lock:
            self._counts.clear()


# Shared instance for the retrieval-api app.
limiter = FixedWindowRateLimiter()
