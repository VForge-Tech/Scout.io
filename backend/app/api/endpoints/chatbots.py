from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db_with_org
from app.core.billing.limits import assert_chatbot_limit, assert_message_quota
from app.models import Chatbot, User
from app.schemas.chatbot import ChatMessageRequest, ChatbotCreate, ChatbotRead, ChatbotUpdate
from app.utils.audit import create_audit_log

router = APIRouter(prefix="/chatbots", tags=["chatbots"])


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


@router.get("", response_model=list[ChatbotRead])
def list_chatbots(
    db: Session = Depends(get_db_with_org),
    user: User = Depends(get_current_user),
):
    return (
        db.query(Chatbot)
        .filter(Chatbot.organization_id == user.organization_id)
        .all()
    )


@router.post("", response_model=ChatbotRead, status_code=status.HTTP_201_CREATED)
def create_chatbot(
    payload: ChatbotCreate,
    request: Request,
    db: Session = Depends(get_db_with_org),
    user: User = Depends(get_current_user),
):
    from app.models import Organization

    org = db.query(Organization).filter(Organization.id == user.organization_id).first()
    assert_chatbot_limit(db, org)

    chatbot = Chatbot(
        organization_id=user.organization_id,
        name=payload.name,
        description=payload.description,
        behaviour=payload.behaviour,
        config=payload.config,
    )
    db.add(chatbot)
    db.commit()
    db.refresh(chatbot)
    create_audit_log(
        db, action="chatbot.created", user_id=user.id,
        organization_id=user.organization_id,
        details={"chatbot_id": str(chatbot.id), "name": chatbot.name},
        ip_address=request.client.host if request.client else None,
    )
    return chatbot


@router.get("/{chatbot_id}", response_model=ChatbotRead)
def get_chatbot(
    chatbot_id: UUID,
    db: Session = Depends(get_db_with_org),
    user: User = Depends(get_current_user),
):
    return _get_chatbot(db, chatbot_id, user)


@router.put("/{chatbot_id}", response_model=ChatbotRead)
def update_chatbot(
    chatbot_id: UUID,
    payload: ChatbotUpdate,
    db: Session = Depends(get_db_with_org),
    user: User = Depends(get_current_user),
):
    chatbot = _get_chatbot(db, chatbot_id, user)
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(chatbot, field, value)
    db.commit()
    db.refresh(chatbot)
    return chatbot


@router.delete("/{chatbot_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chatbot(
    chatbot_id: UUID,
    request: Request,
    db: Session = Depends(get_db_with_org),
    user: User = Depends(get_current_user),
):
    chatbot = _get_chatbot(db, chatbot_id, user)
    db.delete(chatbot)
    db.commit()
    create_audit_log(
        db, action="chatbot.deleted", user_id=user.id,
        organization_id=user.organization_id,
        details={"chatbot_id": str(chatbot_id)},
        ip_address=request.client.host if request.client else None,
    )
    return None


@router.post("/{chatbot_id}/messages/stream")
def stream_chatbot_message(
    chatbot_id: UUID,
    payload: ChatMessageRequest,
    request: Request,
    db: Session = Depends(get_db_with_org),
    user: User = Depends(get_current_user),
):
    """Streaming playground endpoint for org users.

    Runs the same ResponsePipeline as the public widget (same token-by-token
    behavior end users see) under the caller's org RLS context, returning a
    Server-Sent-Events stream. Used by the dashboard Streaming Playground.
    """
    from fastapi.responses import StreamingResponse

    from app.core.pipeline.response_pipeline import ResponsePipeline, sse_wrap
    from app.models import ChatSession, Organization, Policy

    chatbot = _get_chatbot(db, chatbot_id, user)
    org = db.query(Organization).filter(Organization.id == user.organization_id).first()
    assert_message_quota(db, org)

    session = ChatSession(
        organization_id=chatbot.organization_id,
        chatbot_id=chatbot.id,
        customer_id=None,
        metadata_={"channel": "playground"},
    )
    db.add(session)
    db.commit()

    policies = (
        db.query(Policy)
        .filter(
            Policy.organization_id == chatbot.organization_id,
            (Policy.chatbot_id == chatbot.id) | (Policy.chatbot_id.is_(None)),
        )
        .all()
    )
    reranker_enabled = (
        chatbot.config.get("reranker_enabled") if chatbot and chatbot.config else None
    )

    pipeline = ResponsePipeline()
    return StreamingResponse(
        sse_wrap(
            pipeline.run_stream(
                query=payload.content,
                session_id=str(session.id),
                organization_id=str(user.organization_id),
                chatbot_id=str(chatbot.id),
                behaviour=chatbot.behaviour,
                db=db,
                policies=policies,
                reranker_enabled=reranker_enabled,
            )
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
