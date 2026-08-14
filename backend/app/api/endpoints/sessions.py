from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db_with_org
from app.models import ChatSession, Message, User

router = APIRouter(prefix="/organizations/me/sessions", tags=["sessions"])


@router.get("")
def list_sessions(
    db: Session = Depends(get_db_with_org),
    user: User = Depends(get_current_user),
):
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.organization_id == user.organization_id)
        .order_by(ChatSession.started_at.desc())
        .limit(50)
        .all()
    )
    result = []
    for s in sessions:
        msg_count = (
            db.query(Message).filter(Message.session_id == s.id).count()
        )
        result.append(
            {
                "id": str(s.id),
                "chatbot_id": str(s.chatbot_id),
                "customer_id": s.customer_id,
                "message_count": msg_count,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "ended_at": s.ended_at.isoformat() if s.ended_at else None,
            }
        )
    return result
