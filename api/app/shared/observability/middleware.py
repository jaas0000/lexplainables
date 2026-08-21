"""Pure-ASGI-middleware voor request-id-correlatie + één access-logregel per request.

Bewust pure ASGI (geen `BaseHTTPMiddleware`): dat zou SSE-streams bufferen en breken.
Leest/genereert `X-Request-Id`, bindt 'm in een `ContextVar` zodat álle logs binnen de request
'm dragen, echoot 'm in de response, en logt bij de eerste response-chunk method/path/status/duur.
"""

from __future__ import annotations

import contextvars
import logging
import time
import uuid
from typing import Any

# Per-request correlatie-id (leeg buiten een request). Log-formatter leest deze om `request_id`
# aan elke logregel binnen de request te hangen.
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")

_access_logger = logging.getLogger("lexplainables.access")


class RequestContextMiddleware:
    """Pure ASGI: X-Request-Id-correlatie + één access-logregel per HTTP-request.

    Niet-HTTP-scopes (websocket, lifespan) laten we ongewijzigd door — geen request-id nodig
    en de logregel zou daar niet passen. WebSocket-support kan later als het nodig blijkt.
    """

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = dict(scope.get("headers") or [])
        rid = headers.get(b"x-request-id", b"").decode() or uuid.uuid4().hex
        token = request_id_var.set(rid)
        start = time.perf_counter()
        status_code = 0

        async def send_wrapper(message: dict) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                resp_headers = message.setdefault("headers", [])
                resp_headers.append((b"x-request-id", rid.encode()))
                duur_ms = round((time.perf_counter() - start) * 1000, 1)
                _access_logger.info(
                    "%s %s -> %s",
                    scope.get("method", "?"),
                    scope.get("path", "?"),
                    status_code,
                    extra={
                        "categorie": "functioneel",
                        "http_method": scope.get("method"),
                        "http_path": scope.get("path"),
                        "http_status": status_code,
                        "duur_ms": duur_ms,
                    },
                )
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            request_id_var.reset(token)
