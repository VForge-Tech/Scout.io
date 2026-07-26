from uuid import UUID

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def create_audit_log(
    db: Session,
    action: str,
    user_id: UUID | None = None,
    organization_id: UUID | None = None,
    details: dict | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        user_id=user_id,
        organization_id=organization_id,
        action=action,
        details=details or {},
        ip_address=ip_address,
    )
    db.add(entry)
    db.commit()
    return entry
