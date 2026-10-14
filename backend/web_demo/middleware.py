"""
HTTP middleware for the hosted web demo.

Two small pure-ASGI middlewares (pure ASGI, not BaseHTTPMiddleware, so the
NDJSON progress stream is passed through untouched and request context
reaches the background processing job):

DemoMiddleware
    * Identifies each browser with an anonymous, random, HttpOnly cookie so
      its workspaces stay private (no accounts or sign-in).
    * Rejects oversized request bodies, including chunked uploads that do not
      declare a length.
    * Caps how many dataset-processing requests run at once, so one visitor
      cannot starve the others.
    * Adds standard security headers, sensible cache headers, and HSTS on
      HTTPS.

SelectiveGZipMiddleware
    * Compresses static files and the workspace JSON, but never the live
      progress stream (compression would hold back the progress events).
"""

from fastapi import HTTPException
from starlette.datastructures import Headers, MutableHeaders
from starlette.middleware.gzip import GZipMiddleware
from starlette.requests import cookie_parser
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from web_demo.settings import WebSettings
from web_demo.visitors import (
    COOKIE_NAME,
    current_visitor,
    is_valid_visitor_id,
    new_visitor_id,
)

# Room for the multipart boundaries and form fields around an uploaded file.
_MULTIPART_OVERHEAD_BYTES = 256 * 1024

_BODY_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

_CONTENT_SECURITY_POLICY = "; ".join(
    (
        "default-src 'self'",
        "script-src 'self'",
        # React sets inline style attributes on some elements.
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: blob:",
        "font-src 'self' data:",
        "connect-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    )
)

_SECURITY_HEADERS = {
    "content-security-policy": _CONTENT_SECURITY_POLICY,
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "no-referrer",
    "permissions-policy": "camera=(), microphone=(), geolocation=()",
    # The demo link is meant for the client, not for search engines.
    "x-robots-tag": "noindex, nofollow",
}

_HSTS = "max-age=15552000"


def _is_https(scope: Scope, headers: Headers) -> bool:
    if scope.get("scheme") == "https":
        return True
    forwarded = headers.get("x-forwarded-proto", "")
    return forwarded.split(",")[0].strip().lower() == "https"


def _wants_cookie(path: str, headers: Headers) -> bool:
    """Only API calls and page loads need a visitor; static assets do not."""
    if path == "/api/health":
        return False
    if path.startswith("/api/"):
        return True
    return "text/html" in headers.get("accept", "")


def _cookie_header(visitor_id: str, max_age: int, secure: bool) -> str:
    parts = [
        f"{COOKIE_NAME}={visitor_id}",
        "Path=/",
        f"Max-Age={max_age}",
        "HttpOnly",
        "SameSite=Lax",
    ]
    if secure:
        parts.append("Secure")
    return "; ".join(parts)


def _default_cache_control(path: str) -> str:
    if path.startswith("/assets/"):
        # Vite fingerprints these filenames, so they never change.
        return "public, max-age=31536000, immutable"
    if path.startswith("/api/"):
        # Workspace data belongs to one visitor; never cache it.
        return "no-store"
    # The app shell must be revalidated so a new deploy is picked up.
    return "no-cache"


class DemoMiddleware:
    def __init__(self, app: ASGIApp, settings: WebSettings) -> None:
        self.app = app
        self.settings = settings
        # Touched only from the event loop thread, so no lock is needed.
        self._active_jobs = 0

    def _body_limit(self, path: str) -> int:
        if path.startswith("/api/dataset/"):
            return self.settings.max_upload_bytes + _MULTIPART_OVERHEAD_BYTES
        return self.settings.max_api_body_bytes

    def _too_large_message(self, path: str) -> str:
        if path.startswith("/api/dataset/"):
            return (
                f"That file is larger than the "
                f"{self.settings.max_upload_mb:g} MB limit of the web demo. "
                "Use a smaller file, or the desktop application for "
                "large datasets."
            )
        return "The request is too large."

    async def __call__(
            self,
            scope: Scope,
            receive: Receive,
            send: Send,
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path: str = scope["path"]
        method: str = scope["method"]
        headers = Headers(scope=scope)
        secure = _is_https(scope, headers)

        # ---- visitor identity ------------------------------------------
        cookies = cookie_parser(headers.get("cookie", ""))
        visitor_id: str | None = cookies.get(COOKIE_NAME)
        issue_cookie = False
        if not is_valid_visitor_id(visitor_id):
            visitor_id = None
            if _wants_cookie(path, headers):
                visitor_id = new_visitor_id()
                issue_cookie = True

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                response_headers = MutableHeaders(scope=message)
                for name, value in _SECURITY_HEADERS.items():
                    response_headers.setdefault(name, value)
                response_headers.setdefault(
                    "cache-control", _default_cache_control(path)
                )
                if secure:
                    response_headers.setdefault(
                        "strict-transport-security", _HSTS
                    )
                if issue_cookie and visitor_id is not None:
                    response_headers.append(
                        "set-cookie",
                        _cookie_header(
                            visitor_id,
                            self.settings.cookie_max_age_seconds,
                            secure,
                        ),
                    )
            await send(message)

        # ---- request size ----------------------------------------------
        app_receive = receive
        if method in _BODY_METHODS:
            limit = self._body_limit(path)

            declared = headers.get("content-length")
            if declared is not None:
                try:
                    declared_bytes = int(declared)
                except ValueError:
                    declared_bytes = 0
                if declared_bytes > limit:
                    response = JSONResponse(
                        {"detail": self._too_large_message(path)},
                        status_code=413,
                    )
                    await response(scope, receive, send_with_headers)
                    return

            received = 0
            message_too_large = self._too_large_message(path)

            async def limited_receive() -> Message:
                nonlocal received
                message = await receive()
                if message["type"] == "http.request":
                    received += len(message.get("body", b""))
                    if received > limit:
                        # FastAPI re-raises HTTPException from body parsing,
                        # so this becomes a clean 413 JSON response.
                        raise HTTPException(
                            status_code=413,
                            detail=message_too_large,
                        )
                return message

            app_receive = limited_receive

        # ---- concurrency cap for processing requests -------------------
        counts_as_job = method == "POST" and path.startswith("/api/dataset/")
        if counts_as_job:
            if self._active_jobs >= self.settings.max_concurrent_jobs:
                response = JSONResponse(
                    {
                        "detail": (
                            "The demo is busy processing other files. "
                            "Please try again in a few seconds."
                        )
                    },
                    status_code=503,
                    headers={"Retry-After": "5"},
                )
                await response(scope, receive, send_with_headers)
                return
            self._active_jobs += 1

        token = current_visitor.set(visitor_id)
        try:
            await self.app(scope, app_receive, send_with_headers)
        finally:
            current_visitor.reset(token)
            if counts_as_job:
                self._active_jobs -= 1


def _is_compressible_path(path: str) -> bool:
    if not path.startswith("/api/"):
        return True  # the app shell, scripts, styles, fonts
    return path.startswith("/api/workspaces")


class SelectiveGZipMiddleware:
    def __init__(self, app: ASGIApp, minimum_size: int = 1024) -> None:
        self.app = app
        self._gzip = GZipMiddleware(app, minimum_size=minimum_size)

    async def __call__(
            self,
            scope: Scope,
            receive: Receive,
            send: Send,
    ) -> None:
        if scope["type"] == "http" and _is_compressible_path(scope["path"]):
            await self._gzip(scope, receive, send)
            return
        await self.app(scope, receive, send)