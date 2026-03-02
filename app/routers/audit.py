from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domain.auth.dependencies import require_roles
from app.domain.bank.schemas import AuditLogResponse
from app.models.user import Role, User
from app.repositories.audit_repository import AuditLogRepository

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/logs", response_model=list[AuditLogResponse])
async def get_audit_logs(
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(Role.ADMIN)),
) -> list[AuditLogResponse]:
    """Return recent audit log entries. Admin only."""
    repo = AuditLogRepository(db)
    logs = await repo.get_recent(limit=limit, offset=offset)
    return [AuditLogResponse.model_validate(log) for log in logs]
