from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.database import AsyncSessionLocal
from app.domain.auth import router as auth_router
from app.domain.bank import router as bank_router  # noqa: F401 — registers ORM models
from app.middleware.audit import AuditMiddleware
from app.routers import audit, users

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

app.add_middleware(AuditMiddleware)

app.include_router(users.router, prefix="/api/v1")
app.include_router(auth_router.router, prefix="/api/v1")
app.include_router(bank_router.router, prefix="/api/v1")
app.include_router(audit.router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/demo", include_in_schema=False)
async def demo_ui() -> FileResponse:
    """Serve the banking demo UI."""
    return FileResponse(str(_FRONTEND / "index.html"))
