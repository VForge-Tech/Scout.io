from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db_with_org
from app.core.knowledge.engine import KnowledgeEngine
from app.models import Chatbot, Policy, User

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/retrieve")
def debug_retrieve(
    query: str = Query(..., description="Search query"),
    chatbot_id: UUID | None = Query(None, description="Optional chatbot ID filter"),
    top_k: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db_with_org),
    user: User = Depends(get_current_user),
):
    chatbot = None
    if chatbot_id:
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

    policies = (
        db.query(Policy)
        .filter(
            Policy.organization_id == user.organization_id,
        )
        .all()
    )

    engine = KnowledgeEngine()
    results = engine.retrieve(
        query=query,
        organization_id=str(user.organization_id),
        chatbot_id=str(chatbot.id) if chatbot else None,
        policies=policies,
        top_k=top_k,
    )

    return {
        "query": query,
        "organization_id": str(user.organization_id),
        "chatbot_id": str(chatbot.id) if chatbot else None,
        "results_count": len(results),
        "results": results,
    }
