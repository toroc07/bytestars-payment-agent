"""Per-IP limit on sending invoices (it protects the LLM quota of the public demo)."""

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.api.rate_limit import SlidingWindowLimiter, client_ip


def test_limit_blocks_after_max_calls_and_frees_after_the_window():
    now = [0.0]
    limiter = SlidingWindowLimiter(max_calls=2, window_s=60, clock=lambda: now[0])
    limiter.check("1.1.1.1")
    limiter.check("1.1.1.1")
    with pytest.raises(HTTPException) as exc:
        limiter.check("1.1.1.1")
    assert exc.value.status_code == 429 and exc.value.headers["Retry-After"] == "61"
    limiter.check("2.2.2.2")  # other callers are not affected
    now[0] = 60.0
    limiter.check("1.1.1.1")


def test_client_ip_prefers_the_forwarded_address():
    def request(headers, client=("10.0.0.1", 1)):
        return Request({"type": "http", "headers": [(k.encode(), v.encode()) for k, v in headers], "client": client})

    assert client_ip(request([("x-forwarded-for", "203.0.113.7, 10.0.0.2")])) == "203.0.113.7"
    assert client_ip(request([])) == "10.0.0.1"
