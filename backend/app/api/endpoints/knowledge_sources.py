from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db_with_org
from app.core.billing.limits import assert_knowledge_source_limit
from app.core.config import get_settings
from app.models import Chatbot, KnowledgeSource, User
from app.schemas.knowledge_source import (
    KnowledgeSourceCreate,
    KnowledgeSourceRead,
    KnowledgeSourceUpdate,
)

router = APIRouter(tags=["knowledge-sources"])


def _get_chatbot(db: Session, chatbot_id: UUID, user: User) -> Chatbot:
    chatbot = (
        db.query(Chatbot)
        .filter(
            Chatbot.id == chatbot_id,
            Chatbot.organization_id == user.organization_id,
        )
        .first()
    )
    if not chatbot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chatbot not found",
        )
    return chatbot


def _get_source(db: Session, source_id: UUID, org_id: UUID) -> KnowledgeSource:
    source = (
        db.query(KnowledgeSource)
        .filter(
            KnowledgeSource.id == source_id,
            KnowledgeSource.organization_id == org_id,
        )
        .first()
    )
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge source not found",
        )
    return source


@router.get(
    "/chatbots/{chatbot_id}/knowledge-sources",
    response_model=list[KnowledgeSourceRead],
)
def list_knowledge_sources(
    chatbot_id: UUID,
    db: Session = Depends(get_db_with_org),
    user: User = Depends(get_current_user),
):
    _get_chatbot(db, chatbot_id, user)
    return (
        db.query(KnowledgeSource)
        .filter(
            KnowledgeSource.organization_id == user.organization_id,
            KnowledgeSource.chatbot_id == chatbot_id,
        )
        .all()
    )


@router.post(
    "/chatbots/{chatbot_id}/knowledge-sources",
    response_model=KnowledgeSourceRead,
    status_code=status.HTTP_201_CREATED,
)
def create_knowledge_source(
    chatbot_id: UUID,
    payload: KnowledgeSourceCreate,
    db: Session = Depends(get_db_with_org),
    user: User = Depends(get_current_user),
):
    _get_chatbot(db, chatbot_id, user)
    from app.models import Organization

    org = db.query(Organization).filter(Organization.id == user.organization_id).first()
    assert_knowledge_source_limit(db, org)
    config = payload.config or {}
    if payload.connector_type:
        config["_connector_type"] = payload.connector_type
    source = KnowledgeSource(
        organization_id=user.organization_id,
        chatbot_id=chatbot_id,
        source_type=payload.source_type,
        uri=payload.uri,
        config=config,
    )
    db.add(source)
    db.commit()
    db.refresh(source)

    return source


@router.get(
    "/chatbots/{chatbot_id}/knowledge-sources/{source_id}",
    response_model=KnowledgeSourceRead,
)
def get_knowledge_source(
    chatbot_id: UUID,
    source_id: UUID,
    db: Session = Depends(get_db_with_org),
    user: User = Depends(get_current_user),
):
    _get_chatbot(db, chatbot_id, user)
    return _get_source(db, source_id, user.organization_id)


@router.put(
    "/chatbots/{chatbot_id}/knowledge-sources/{source_id}",
    response_model=KnowledgeSourceRead,
)
def update_knowledge_source(
    chatbot_id: UUID,
    source_id: UUID,
    payload: KnowledgeSourceUpdate,
    db: Session = Depends(get_db_with_org),
    user: User = Depends(get_current_user),
):
    _get_chatbot(db, chatbot_id, user)
    source = _get_source(db, source_id, user.organization_id)
    update_data = payload.model_dump(exclude_unset=True)
    if "connector_type" in update_data:
        cfg = dict(source.config or {})
        if update_data["connector_type"]:
            cfg["_connector_type"] = update_data.pop("connector_type")
        else:
            cfg.pop("_connector_type", None)
            update_data.pop("connector_type")
        source.config = cfg
    for field, value in update_data.items():
        setattr(source, field, value)
    db.commit()
    db.refresh(source)
    return source


@router.delete(
    "/chatbots/{chatbot_id}/knowledge-sources/{source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_knowledge_source(
    chatbot_id: UUID,
    source_id: UUID,
    db: Session = Depends(get_db_with_org),
    user: User = Depends(get_current_user),
):
    _get_chatbot(db, chatbot_id, user)
    source = _get_source(db, source_id, user.organization_id)
    db.delete(source)
    db.commit()
    return None


@router.post(
    "/chatbots/{chatbot_id}/knowledge-sources/{source_id}/sync",
    response_model=dict,
)
def sync_knowledge_source(
    chatbot_id: UUID,
    source_id: UUID,
    request: Request,
    db: Session = Depends(get_db_with_org),
    user: User = Depends(get_current_user),
):
    """Trigger a re-sync of a knowledge source using the existing ingestion pipeline.

    This dispatches the existing Celery ingestion task (process_knowledge_source),
    which sets sync_status="processing" then "completed"/"failed" with retry support.
    """
    _get_chatbot(db, chatbot_id, user)
    source = _get_source(db, source_id, user.organization_id)

    if not get_settings().celery_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Celery ingestion is disabled; cannot trigger sync",
        )

    from app.tasks.embedding_tasks import process_knowledge_source

    source.sync_status = "pending"
    db.commit()

    task = process_knowledge_source.delay(str(source.id))
    return {
        "status": "dispatched",
        "source_id": str(source.id),
        "task_id": task.id,
    }
