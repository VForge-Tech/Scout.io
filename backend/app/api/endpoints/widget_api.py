from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, optional_current_user
from app.core.billing.limits import assert_message_quota
from app.core.config import get_settings
from app.core.pipeline.response_pipeline import ResponsePipeline
from app.core.rate_limit import limiter, widget_org_key
from app.core.security import create_access_token, decode_token
from app.db.session import get_db as get_db_base
from app.models import ChatSession as SessionModel
from app.models import Chatbot, Message, Organization, Policy, User
from app.schemas.widget import (
    WidgetMessageRequest,
    WidgetMessageResponse,
    WidgetSessionCreate,
    WidgetSessionResponse,
)

router = APIRouter(prefix="/widget", tags=["widget"])


def _get_widget_session(db: Session, token: str) -> SessionModel:
    payload = decode_token(token)
    if payload is None or payload.get("type") != "widget":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired widget session",
        )
    session = (
        db.query(SessionModel)
        .filter(SessionModel.id == UUID(payload["sub"]))
        .first()
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    return session


def get_widget_session(
    request: Request,
    db: Session = Depends(get_db),
) -> SessionModel:
    """Dependency to get widget session from Authorization header and set RLS context."""
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing widget token",
        )

    session = _get_widget_session(db, token)

    # Set RLS context for this session's organization
    from app.db.session import get_db as get_db_base
    from sqlalchemy import text
    db.execute(text("SET LOCAL app.current_org_id = :oid"), {"oid": str(session.organization_id)})

    return session


@router.post("/sessions", response_model=WidgetSessionResponse)
def create_widget_session(
    payload: WidgetSessionCreate,
    db: Session = Depends(get_db),
):
    chatbot = db.query(Chatbot).filter(Chatbot.id == UUID(payload.chatbot_id)).first()
    if not chatbot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chatbot not found",
        )

    session = SessionModel(
        organization_id=chatbot.organization_id,
        chatbot_id=chatbot.id,
        customer_id=payload.customer_id,
        metadata_=payload.metadata,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    token = create_access_token(
        subject=str(session.id),
        organization_id=chatbot.organization_id,
        extra_claims={
            "type": "widget",
            "chatbot_id": str(chatbot.id),
        },
    )

    return WidgetSessionResponse(
        session_id=str(session.id),
        token=token,
    )


@router.post("/messages", response_model=WidgetMessageResponse)
@limiter.limit(lambda: get_settings().rate_limit_per_org, key_func=widget_org_key)
def send_widget_message(
    payload: WidgetMessageRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    session: SessionModel = Depends(get_widget_session),
):
    from app.models import Organization

    org = db.query(Organization).filter(Organization.id == session.organization_id).first()
    assert_message_quota(db, org)

    user_msg = Message(
        session_id=session.id,
        role="user",
        content=payload.content,
        metadata_=payload.metadata,
    )
    db.add(user_msg)
    db.commit()

    chatbot = db.query(Chatbot).filter(Chatbot.id == session.chatbot_id).first()
    policies = (
        db.query(Policy)
        .filter(
            Policy.organization_id == session.organization_id,
            (Policy.chatbot_id == session.chatbot_id) | (Policy.chatbot_id.is_(None)),
        )
        .all()
    ) if chatbot else []

    pipeline = ResponsePipeline()
    result = pipeline.run(
        query=payload.content,
        session_id=str(session.id),
        organization_id=str(session.organization_id),
        chatbot_id=str(session.chatbot_id) if session.chatbot_id else None,
        behaviour=chatbot.behaviour if chatbot else "balanced",
        db=db,
        policies=policies,
    )

    # Expose per-stage pipeline timing (ms) to load-test clients via a header.
    # Load tests read this to build p50/p95/p99 per stage without touching the API schema.
    timings = result.get("timings")
    if timings:
        import json

        response.headers["X-Pipeline-Timings"] = json.dumps(timings)

    bot_msg = Message(
        session_id=session.id,
        role="assistant",
        content=result["reply"],
    )
    db.add(bot_msg)
    db.commit()

    return WidgetMessageResponse(
        reply=result["reply"],
        session_id=str(session.id),
    )
