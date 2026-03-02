from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


class AuditLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        method: str,
        path: str,
        client_ip: str,
        status_code: int,
        user_id: int | None = None,
        reason: str | None = None,
    ) -> AuditLog:
        log = AuditLog(
            method=method,
            path=path,
            client_ip=client_ip,
            status_code=status_code,
            user_id=user_id,
            reason=reason,
        )
        self._session.add(log)
        await self._session.flush()
        return log

    async def get_recent(self, *, limit: int = 100, offset: int = 0) -> list[AuditLog]:
        result = await self._session.execute(
            select(AuditLog)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
