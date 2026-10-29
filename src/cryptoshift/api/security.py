"""Authentication, sessions, CSRF, rate limits and HTTP hardening.

- Passwords: stdlib scrypt (n=2**14, r=8, p=1) with a random 16-byte salt.
- Sessions: itsdangerous-signed cookie `cs_session` (HttpOnly, SameSite=Strict) holding {uid, csrf}; max age 8 h.
- CSRF: double submit. `cs_csrf` cookie (readable by JS) must equal the `X-CSRF-Token` header on mutating requests.
- Rate limits: in-memory token buckets per (bucket, session or client IP).
- Headers: strict CSP without inline scripts, no framing, no sniffing, no referrer, minimal permissions.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import threading
import time
import uuid
from collections.abc import Callable
from typing import Any, ClassVar

from itsdangerous import BadSignature, URLSafeTimedSerializer
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

ROLES = ("viewer", "analyst", "approver")
ROLE_RANK = {r: i for i, r in enumerate(ROLES)}
SESSION_COOKIE, CSRF_COOKIE, CSRF_HEADER = "cs_session", "cs_csrf", "x-csrf-token"
MUTATING = {"POST", "PUT", "PATCH", "DELETE"}
# The single style hash is Cytoscape's fixed container rule ".__________cytoscape_container { position: relative; }".
CSP = ("default-src 'self'; script-src 'self'; style-src 'self' 'sha256-pgvDUBa4IjFA2yuSJ2cqcyxmNYJMborsd0ORcRv9vw8='; img-src 'self' data:; font-src 'self'; "
       "connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'")
DOCS_CSP = CSP.replace("script-src 'self'", "script-src 'self' 'unsafe-inline'").replace(
    "style-src 'self'", "style-src 'self' 'unsafe-inline'")  # only for /api/docs (Swagger UI), never for the app


# ------------------------------------------------------------------ passwords
def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return "scrypt$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(dk).decode()


def verify_password(password: str, stored: str) -> bool:
    try:
        _, s, d = stored.split("$")
        dk = hashlib.scrypt(password.encode(), salt=base64.b64decode(s), n=2**14, r=8, p=1, dklen=32)
        return hmac.compare_digest(dk, base64.b64decode(d))
    except (ValueError, TypeError):
        return False


# ------------------------------------------------------------------ sessions
class Sessions:
    def __init__(self, secret: bytes, max_age_s: int) -> None:
        self._s = URLSafeTimedSerializer(secret, salt="cryptoshift-session")
        self.max_age_s = max_age_s

    def issue(self, uid: int) -> tuple[str, str]:
        csrf = secrets.token_urlsafe(32)
        return self._s.dumps({"uid": uid, "csrf": csrf}), csrf

    def read(self, token: str | None) -> dict[str, Any] | None:
        if not token:
            return None
        try:
            data = self._s.loads(token, max_age=self.max_age_s)
        except BadSignature:
            return None
        return data if isinstance(data, dict) and "uid" in data and "csrf" in data else None


def csrf_ok(request: Request, session: dict[str, Any]) -> bool:
    header = request.headers.get(CSRF_HEADER, "")
    cookie = request.cookies.get(CSRF_COOKIE, "")
    return bool(header) and hmac.compare_digest(header, cookie) and hmac.compare_digest(header, session["csrf"])


# ------------------------------------------------------------------ rate limits
class RateLimiter:
    """Token bucket: `capacity` requests, refilled evenly over `per_s` seconds."""

    LIMITS: ClassVar[dict[str, tuple[int, int]]] = {"login": (5, 60), "assistant": (10, 60), "jobs": (6, 60), "approvals": (6, 60), "settings": (6, 60), "scans": (6, 60)}

    def __init__(self) -> None:
        self._b: dict[tuple[str, str], tuple[float, float]] = {}
        self._lock = threading.Lock()

    def allow(self, bucket: str, key: str) -> bool:
        cap, per = self.LIMITS[bucket]
        now = time.monotonic()
        with self._lock:
            tokens, last = self._b.get((bucket, key), (float(cap), now))
            tokens = min(cap, tokens + (now - last) * cap / per)
            if tokens < 1:
                self._b[(bucket, key)] = (tokens, now)
                return False
            self._b[(bucket, key)] = (tokens - 1, now)
            return True


# ------------------------------------------------------------------ middleware
def error(code: str, message: str, status: int, request_id: str = "") -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message, "request_id": request_id}}, status_code=status)


class HardeningMiddleware(BaseHTTPMiddleware):
    """Request id, body-size limit and security headers on every response."""

    def __init__(self, app: Any, max_body: int, max_upload: int) -> None:
        super().__init__(app)
        self.max_body, self.max_upload = max_body, max_upload

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        rid = str(uuid.uuid4())
        request.state.request_id = rid
        limit = self.max_upload if request.url.path.startswith(("/api/v1/scans", "/api/v1/runs")) else self.max_body
        length = request.headers.get("content-length")
        if length and length.isdigit() and int(length) > limit:
            resp: Response = error("payload_too_large", f"request body over {limit} bytes", 413, rid)
        else:
            resp = await call_next(request)
        resp.headers["X-Request-ID"] = rid
        resp.headers["Content-Security-Policy"] = DOCS_CSP if request.url.path.startswith("/api/docs") else CSP
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "no-referrer"
        resp.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        resp.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        resp.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), usb=(), payment=()"
        if request.url.path.startswith("/api/"):
            resp.headers["Cache-Control"] = "no-store"
        return resp
