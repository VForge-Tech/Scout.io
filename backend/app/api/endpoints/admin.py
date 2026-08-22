from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_db_admin, get_db_with_org, require_admin, require_platform_admin
from app.domain.offboarding import OffboardingService
from app.scripts.seed_demo import seed_demo
from app.models import (
    ApiKey,
    Chatbot,
    ChatSession,
    KnowledgeSource,
    LLMUsage,
    Message,
    Organization,
    Policy,
    User,
)
from app.schemas.audit_log import AuditLogRead
from app.schemas.llm_usage import LLMUsageRead
from app.schemas.offboarding import OffboardConfirm, OffboardPreview, OffboardReport
from app.schemas.organization import OrganizationRead
from app.utils.audit import create_audit_log

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/organizations", response_model=list[OrganizationRead])
def list_organizations(
    db: Session = Depends(get_db_admin),
    admin: User = Depends(require_platform_admin),
):
    return db.query(Organization).all()


@router.get("/organizations/{org_id}", response_model=OrganizationRead)
def get_organization(
    org_id: UUID,
    db: Session = Depends(get_db_admin),
    admin: User = Depends(require_platform_admin),
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )
    return org


@router.patch("/organizations/{org_id}")
def update_organization(
    org_id: UUID,
    payload: dict,
    request: Request,
    db: Session = Depends(get_db_admin),
    admin: User = Depends(require_platform_admin),
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    current_config = org.configuration or {}
    current_config.update(payload)
    org.configuration = current_config
    db.commit()

    create_audit_log(
        db,
        action="org_updated",
        user_id=admin.id,
        organization_id=org_id,
        details={"changes": payload},
        ip_address=request.client.host if request.client else None,
    )

    return {"status": "updated", "organization_id": str(org.id)}


@router.delete("/organizations/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_organization(
    org_id: UUID,
    request: Request,
    db: Session = Depends(get_db_admin),
    admin: User = Depends(require_platform_admin),
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    create_audit_log(
        db,
        action="org_deleted",
        user_id=admin.id,
        organization_id=org_id,
        ip_address=request.client.host if request.client else None,
    )

    db.delete(org)
    db.commit()
    return None


@router.post("/organizations/{org_id}/offboard", response_model=OffboardPreview)
def begin_org_offboard(
    org_id: UUID,
    request: Request,
    db: Session = Depends(get_db_admin),
    admin: User = Depends(require_platform_admin),
):
    """Step 1 of offboarding: return a signed confirmation token + deletion preview.

    Nothing is deleted by this call. The token is short-lived (15 min) and bound
    to this org and this admin; it must be echoed to the confirm endpoint.
    """
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    service = OffboardingService(db)
    token = service.create_confirmation_token(org.id, admin.id)
    preview = service.preview(org)
    preview["confirmation_token"] = token

    create_audit_log(
        db,
        action="org_offboard_requested",
        user_id=admin.id,
        organization_id=org_id,
        details={"organization_name": org.name},
        ip_address=request.client.host if request.client else None,
    )

    return preview


@router.post("/organizations/{org_id}/offboard/confirm", response_model=OffboardReport)
def confirm_org_offboard(
    org_id: UUID,
    payload: OffboardConfirm,
    request: Request,
    db: Session = Depends(get_db_admin),
    admin: User = Depends(require_platform_admin),
):
    """Step 2 of offboarding: verify the signed token, then purge everything.

    Permanently deletes all org-scoped Postgres rows, Qdrant/pgvector vectors,
    org Redis caches and uploaded files. The purge itself is recorded in
    audit_logs (platform-level proof of deletion, kept as an exception).
    """
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    service = OffboardingService(db)
    if not service.verify_confirmation_token(payload.confirmation_token, org.id, admin.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired confirmation token",
        )

    return service.execute(
        org,
        admin_id=admin.id,
        ip_address=request.client.host if request.client else None,
    )


@router.get("/stats")
def get_platform_stats(
    db: Session = Depends(get_db_admin),
    admin: User = Depends(require_platform_admin),
):
    return {
        "total_organizations": db.query(Organization).count(),
        "total_users": db.query(User).count(),
        "total_chatbots": db.query(Chatbot).count(),
        "total_policies": db.query(Policy).count(),
        "total_knowledge_sources": db.query(KnowledgeSource).count(),
        "total_sessions": db.query(ChatSession).count(),
        "total_messages": db.query(Message).count(),
        "total_api_keys": db.query(ApiKey).count(),
        "total_llm_calls": db.query(LLMUsage).count(),
        "total_tokens_used": db.query(func.sum(LLMUsage.total_tokens)).scalar() or 0,
    }


@router.get("/system-config", response_model=list[dict])
def list_system_config(
    db: Session = Depends(get_db_admin),
    admin: User = Depends(require_platform_admin),
):
    from app.models import SystemConfig
    configs = db.query(SystemConfig).all()
    return [{"id": str(c.id), "key": c.key, "value": c.value, "description": c.description} for c in configs]


@router.put("/system-config/{key}")
def update_system_config(
    key: str,
    payload: dict,
    request: Request,
    db: Session = Depends(get_db_admin),
    admin: User = Depends(require_platform_admin),
):
    from app.models import SystemConfig
    config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    if not config:
        config = SystemConfig(key=key, value=payload)
        db.add(config)
    else:
        config.value = payload
    db.commit()

    create_audit_log(
        db, action="system_config.updated", user_id=admin.id,
        details={"key": key, "value": payload},
        ip_address=request.client.host if request.client else None,
    )

    return {"key": key, "value": payload}


@router.get("/audit-logs", response_model=list[AuditLogRead])
def list_audit_logs(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db_admin),
    admin: User = Depends(require_platform_admin),
):
    from app.models.audit_log import AuditLog

    return (
        db.query(AuditLog)
        .order_by(AuditLog.timestamp.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get("/llm-usage", response_model=list[LLMUsageRead])
def list_llm_usage(
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db_admin),
    admin: User = Depends(require_platform_admin),
):
    return (
        db.query(LLMUsage)
        .order_by(LLMUsage.timestamp.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get("/health")
def system_health(
    db: Session = Depends(get_db_admin),
    admin: User = Depends(require_platform_admin),
):
    import redis

    from app.core.config import get_settings

    settings = get_settings()
    services = {}

    # Database
    try:
        db.execute(db.bind.text("SELECT 1"))
        services["database"] = {"status": "healthy"}
    except Exception as e:
        services["database"] = {"status": "unhealthy", "error": str(e)}

    # Redis
    try:
        r = redis.from_url(settings.redis_url)
        r.ping()
        r.close()
        services["redis"] = {"status": "healthy"}
    except Exception as e:
        services["redis"] = {"status": "unhealthy", "error": str(e)}

    # Qdrant
    try:
        from qdrant_client import QdrantClient

        qdrant = QdrantClient(url=settings.qdrant_url)
        qdrant.get_collections()
        services["qdrant"] = {"status": "healthy"}
    except Exception as e:
        services["qdrant"] = {"status": "unhealthy", "error": str(e)}

    all_healthy = all(s["status"] == "healthy" for s in services.values())

    return {"status": "healthy" if all_healthy else "degraded", "services": services}


@router.post("/seed")
def seed_demo_data(
    request: Request,
    admin: User = Depends(require_platform_admin),
):
    """Run demo data seeding (platform admin only)."""
    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        result = seed_demo(db)
        return {"status": "seeded", "details": result}
    finally:
        db.close()
