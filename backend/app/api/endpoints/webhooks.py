from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import User, Webhook
from app.schemas.webhook import WebhookCreate, WebhookRead
from app.utils.audit import create_audit_log

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("", response_model=WebhookRead, status_code=status.HTTP_201_CREATED)
def create_webhook(
    payload: WebhookCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    webhook = Webhook(
        organization_id=user.organization_id,
        url=payload.url,
        events=payload.events,
    )
    db.add(webhook)
    db.commit()
    db.refresh(webhook)

    create_audit_log(
        db, action="webhook.created", user_id=user.id,
        organization_id=user.organization_id,
        details={"webhook_id": str(webhook.id), "url": payload.url},
    )

    return webhook


@router.get("", response_model=list[WebhookRead])
def list_webhooks(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return (
        db.query(Webhook)
        .filter(
            Webhook.organization_id == user.organization_id,
            Webhook.is_active.is_(True),
        )
        .all()
    )


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_webhook(
    webhook_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    webhook = (
        db.query(Webhook)
        .filter(
            Webhook.id == webhook_id,
            Webhook.organization_id == user.organization_id,
        )
        .first()
    )
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )
    webhook.is_active = False
    db.commit()

    create_audit_log(
        db, action="webhook.deleted", user_id=user.id,
        organization_id=user.organization_id,
        details={"webhook_id": str(webhook_id)},
    )
    return None
