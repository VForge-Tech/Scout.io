from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import ChatSession, Message, User

router = APIRouter(prefix="/organizations/me/analytics", tags=["analytics"])


@router.get("/summary")
def get_org_analytics(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    org_id = user.organization_id
    total_sessions = (
        db.query(ChatSession)
        .filter(ChatSession.organization_id == org_id)
        .count()
    )
    active_sessions = (
        db.query(ChatSession)
        .filter(
            ChatSession.organization_id == org_id,
            ChatSession.ended_at.is_(None),
        )
        .count()
    )
    total_messages = (
        db.query(Message)
        .join(ChatSession)
        .filter(ChatSession.organization_id == org_id)
        .count()
    )
    return {
        "total_sessions": total_sessions,
        "active_sessions": active_sessions,
        "total_messages": total_messages,
    }
