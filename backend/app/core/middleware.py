"""HTTP middleware: request ids, security headers, CSRF protection, CORS."""

import hmac
import logging
import re
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.config import Settings
from app.core.cookies import CSRF_COOKIE, CSRF_HEADER
from app.core.exceptions import error_body
from app.core.logging import request_id_ctx

logger = logging.getLogger("app.request")

CallNext = Callable[[Request], Awaitable[Response]]

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
_REQUEST_ID_RE = re.compile(r"[A-Za-z0-9-]{1,64}")
DOCS_PATHS = ("/docs", "/redoc", "/openapi.json")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assigns a request id, echoes it in X-Request-ID, and logs each request."""

    async def dispatch(self, request: Request, call_next: CallNext) -> Response:
        incoming = request.headers.get("X-Request-ID", "")
        # Only accept safe ids from upstream proxies; anything else could inject into logs.
        request_id = incoming if _REQUEST_ID_RE.fullmatch(incoming) else uuid.uuid4().hex
        token = request_id_ctx.set(request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            request_id_ctx.reset(token)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "%s %s -> %s (%.1f ms) [%s]",
            request.method,
            request.url.path,
            response.status_code,
            (time.perf_counter() - started) * 1000,
            request_id,
        )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, *, hsts: bool) -> None:
        super().__init__(app)
        self.hsts = hsts

    async def dispatch(self, request: Request, call_next: CallNext) -> Response:
        response = await call_next(request)
        headers = response.headers
        headers.setdefault("X-Content-Type-Options", "nosniff")
        headers.setdefault("X-Frame-Options", "DENY")
        headers.setdefault("Referrer-Policy", "no-referrer")
        headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        if not request.url.path.startswith(DOCS_PATHS):
            # The API only returns JSON, so it needs no scripts, styles or frames.
            headers.setdefault(
                "Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'"
            )
            headers.setdefault("Cache-Control", "no-store")
        if self.hsts:
            headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response


class CSRFMiddleware(BaseHTTPMiddleware):
    """Double-submit CSRF check for state-changing API requests.

    A malicious site can make the browser send our cookies, but it cannot
    read the csrf_token cookie, so it cannot put the matching header on the
    request.
    """

    def __init__(self, app: ASGIApp, *, api_prefix: str, exempt_paths: set[str]) -> None:
        super().__init__(app)
        self.api_prefix = api_prefix
        self.exempt_paths = exempt_paths

    async def dispatch(self, request: Request, call_next: CallNext) -> Response:
        path = request.url.path
        if (
            request.method in SAFE_METHODS
            or not path.startswith(self.api_prefix)
            or path in self.exempt_paths
        ):
            return await call_next(request)

        cookie = request.cookies.get(CSRF_COOKIE, "")
        header = request.headers.get(CSRF_HEADER, "")
        if not cookie or not header or not hmac.compare_digest(cookie, header):
            return JSONResponse(
                error_body("csrf_failed", "Missing or invalid CSRF token"),
                status_code=status.HTTP_403_FORBIDDEN,
            )
        return await call_next(request)


def register_middleware(app: FastAPI, settings: Settings) -> None:
    # Starlette runs the middleware added last first, so this list reads
    # innermost -> outermost.
    app.add_middleware(
        CSRFMiddleware,
        api_prefix=settings.api_prefix,
        exempt_paths={f"{settings.api_prefix}/auth/login"},
    )
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
            allow_headers=["Content-Type", CSRF_HEADER, "X-Request-ID"],
        )
    app.add_middleware(SecurityHeadersMiddleware, hsts=settings.is_production)
    app.add_middleware(RequestContextMiddleware)
