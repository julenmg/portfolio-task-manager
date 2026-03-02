"""Audit middleware — logs every 401 / 403 response for fraud detection."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.database import AsyncSessionLocal
from app.core.security import extract_user_id_from_header
from app.models.audit_log import AuditLog


class AuditMiddleware(BaseHTTPMiddleware):
    """Record failed authentication / authorisation attempts in the audit_logs table.

    Reasons logged:
    - 401 Unauthorized  → "Unauthenticated access attempt"
    - 403 Forbidden     → "Unauthorized access attempt"

    The write is intentionally synchronous with the response so that tests
    can query audit rows immediately after the HTTP call returns.

    The session factory is read from ``request.app.state.session_factory`` so
    that tests can inject ``TestSessionLocal`` before the app starts serving.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        if response.status_code in {401, 403}:
            await self._write_audit_log(request, response.status_code)
        return response

    def _extract_user_id(self, request: Request) -> int | None:
        auth_header = request.headers.get("Authorization", "")
        return extract_user_id_from_header(auth_header)

    async def _write_audit_log(self, request: Request, status_code: int) -> None:
        user_id = self._extract_user_id(request)
        reason = (
            "Unauthenticated access attempt"
            if status_code == 401
            else "Unauthorized access attempt"
        )
        client_ip = request.client.host if request.client else "unknown"

        session_factory = getattr(
            request.app.state, "session_factory", AsyncSessionLocal
        )

        try:
            async with session_factory() as session:
                async with session.begin():
                    session.add(
                        AuditLog(
                            method=request.method,
                            path=request.url.path,
                            client_ip=client_ip,
                            user_id=user_id,
                            status_code=status_code,
                            reason=reason,
                        )
                    )
        except Exception:
            # Never let audit failures propagate back to the client.
            pass
