"""Audit middleware — logs security-relevant HTTP events.

Events recorded
---------------
- 401 Unauthorized  → failed / missing authentication
- 403 Forbidden     → authenticated but lacking permission
- 200 on /auth/login → successful login (compliance requirement)

Failures writing to the audit log are logged at ERROR level and never
propagated to the client so that audit issues don't break service.
"""

import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.database import AsyncSessionLocal
from app.core.security import extract_user_id_from_header
from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)

_AUTH_LOGIN_PATH = "/api/v1/auth/login"

_REASONS: dict[int, str] = {
    200: "Successful login",
    401: "Unauthenticated access attempt",
    403: "Unauthorized access attempt",
}


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        should_log = response.status_code in {401, 403} or (
            response.status_code == 200
            and request.url.path == _AUTH_LOGIN_PATH
            and request.method == "POST"
        )

        if should_log:
            await self._write_audit_log(request, response.status_code)

        return response

    def _extract_user_id(self, request: Request) -> int | None:
        auth_header = request.headers.get("Authorization", "")
        return extract_user_id_from_header(auth_header)

    async def _write_audit_log(self, request: Request, status_code: int) -> None:
        user_id = self._extract_user_id(request)
        reason = _REASONS.get(status_code, "Security event")
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
            # Never let audit failures surface to the client, but DO log them
            # so that on-call engineers are alerted.
            logger.error(
                "Failed to write audit log for %s %s (status=%s)",
                request.method,
                request.url.path,
                status_code,
                exc_info=True,
            )
