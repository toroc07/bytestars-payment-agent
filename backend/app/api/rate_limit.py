"""Per-IP sliding-window limit for the public endpoints that can spend LLM quota.

It lives in the process memory, so on Vercel each instance counts on its own: it stops one browser or
script from burning the daily Gemini quota, and the Vercel Firewall rule in docs/DEPLOY.md covers the rest.
"""

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from app.config import settings


def client_ip(request: Request) -> str:
    """Vercel puts the caller's address first in x-forwarded-for; locally it is the socket address."""
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded.strip():
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class SlidingWindowLimiter:
    def __init__(self, max_calls: int, window_s: float, clock=time.monotonic):
        self.max_calls = max_calls
        self.window_s = window_s
        self._clock = clock
        self._calls: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> None:
        now = self._clock()
        calls = self._calls[key]
        while calls and now - calls[0] >= self.window_s:
            calls.popleft()
        if len(calls) >= self.max_calls:
            wait = int(self.window_s - (now - calls[0])) + 1
            raise HTTPException(
                status_code=429,
                detail=f"Enviaste demasiadas facturas seguidas. Espera {wait} s y vuelve a intentarlo.",
                headers={"Retry-After": str(wait)},
            )
        calls.append(now)


# Two dataset batches (2 x 50 invoices) fit in the window; a script uploading images in a loop does not.
MESSAGES_LIMITER = SlidingWindowLimiter(max_calls=120, window_s=600)


def limit_messages(request: Request) -> None:
    if settings.APP_ENV in ("test", "testing"):
        return
    MESSAGES_LIMITER.check(client_ip(request))
