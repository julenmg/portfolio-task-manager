import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.domain.auth import router as auth_router
from app.domain.bank import router as bank_router  # noqa: F401 — registers ORM models
from app.middleware.audit import AuditMiddleware
from app.routers import audit, users

logger = logging.getLogger(__name__)


# ── Security headers ──────────────────────────────────────────────────────────

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Inject defensive HTTP headers on every response."""

    _STATIC_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        # Tight CSP: same-origin only; inline styles allowed for the demo UI
        "Content-Security-Policy": (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "frame-ancestors 'none';"
        ),
    }

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        for header, value in self._STATIC_HEADERS.items():
            response.headers[header] = value
        if settings.environment == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        return response


# ── Application ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="Secure Banking API",
    version="1.0.0",
    description="Atomic transfers, compound interest, and full audit ledger.",
)

_FRONTEND = Path(__file__).parent.parent / "frontend"
if _FRONTEND.exists():
    app.mount("/static", StaticFiles(directory=str(_FRONTEND)), name="static")

# Inject the real session factory (tests override this via app.state).
app.state.session_factory = AsyncSessionLocal

# ── Middleware stack (outermost first) ────────────────────────────────────────

app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.allowed_origins.split(",")],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

app.add_middleware(AuditMiddleware)

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(users.router, prefix="/api/v1")
app.include_router(auth_router.router, prefix="/api/v1")
app.include_router(bank_router.router, prefix="/api/v1")
app.include_router(audit.router, prefix="/api/v1")


# ── Health & demo ─────────────────────────────────────────────────────────────

@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/demo", include_in_schema=False)
async def demo_ui() -> FileResponse:
    """Serve the banking demo UI."""
    return FileResponse(str(_FRONTEND / "index.html"))
