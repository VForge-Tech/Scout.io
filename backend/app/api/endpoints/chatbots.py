from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db_with_org
from app.models import Chatbot, User
from app.schemas.chatbot import ChatbotCreate, ChatbotRead, ChatbotUpdate
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
