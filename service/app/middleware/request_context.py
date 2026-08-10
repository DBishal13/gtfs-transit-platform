"""Assigns a request ID to every request (returned as an X-Request-ID response header)
and logs one structured JSON line per request (method, path, status_code, latency_ms).

Deliberately simple: org/user context isn't attached here because auth resolution
happens downstream in route dependencies (service/app/deps.py::get_current_principal),
not in ASGI middleware, and re-deriving it here would duplicate that logic. Per-turn LLM
token usage is logged/recorded separately in service/app/routers/agent.py, where the
authenticated principal is already available.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from service.app.logging_config import get_logger

log = get_logger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = str(uuid.uuid4())
        start = time.monotonic()
        response = await call_next(request)
        latency_ms = round((time.monotonic() - start) * 1000, 1)
        response.headers["X-Request-ID"] = request_id
        log.info(
            "request",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            latency_ms=latency_ms,
        )
        return response
