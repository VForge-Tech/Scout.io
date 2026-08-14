from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db_admin, get_db_with_org, require_platform_admin
from app.models import (
    AnalyticsEvent,
    ChatSession,
    Chatbot,
    DailyAnalytics,
    KnowledgeSource,
    LLMUsage,
    Message,
    Organization,
    User,
)
from app.schemas.analytics import (
    ChatbotAnalyticsResponse,
    OrgAnalyticsResponse,
    PlatformAnalyticsResponse,
    SourceAnalyticsResponse,
)

router = APIRouter(tags=["analytics"])


@router.get("/analytics/chatbot/{chatbot_id}", response_model=ChatbotAnalyticsResponse)
def get_chatbot_analytics(
    chatbot_id: UUID,
    db: Session = Depends(get_db_with_org),
    user: User = Depends(get_current_user),
):
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

    total_sessions = (
        db.query(func.count(ChatSession.id))
        .filter(ChatSession.chatbot_id == chatbot_id)
        .scalar()
        or 0
    )
    total_messages = (
        db.query(func.count(Message.id))
        .join(ChatSession)
        .filter(ChatSession.chatbot_id == chatbot_id)
        .scalar()
        or 0
    )
    total_tokens = (
        db.query(func.coalesce(func.sum(LLMUsage.total_tokens), 0))
        .filter(LLMUsage.chatbot_id == chatbot_id)
        .scalar()
        or 0
    )
    avg_latency = (
        db.query(func.coalesce(func.avg(DailyAnalytics.avg_latency_ms), 0.0))
        .filter(DailyAnalytics.chatbot_id == chatbot_id)
        .scalar()
        or 0.0
    )
    fb_positive = (
        db.query(func.coalesce(func.sum(DailyAnalytics.feedback_positive), 0))
        .filter(DailyAnalytics.chatbot_id == chatbot_id)
        .scalar()
        or 0
    )
    fb_negative = (
        db.query(func.coalesce(func.sum(DailyAnalytics.feedback_negative), 0))
        .filter(DailyAnalytics.chatbot_id == chatbot_id)
        .scalar()
        or 0
    )

    return ChatbotAnalyticsResponse(
        chatbot_id=chatbot_id,
        total_sessions=total_sessions,
        total_messages=total_messages,
        total_tokens=total_tokens,
        avg_latency_ms=float(avg_latency),
        feedback_positive=fb_positive,
        feedback_negative=fb_negative,
    )


@router.get("/analytics/organization", response_model=OrgAnalyticsResponse)
def get_org_analytics(
    db: Session = Depends(get_db_with_org),
    user: User = Depends(get_current_user),
):
    org_id = user.organization_id

    total_sessions = (
        db.query(func.count(ChatSession.id))
        .filter(ChatSession.organization_id == org_id)
        .scalar()
        or 0
    )
    total_messages = (
        db.query(func.count(Message.id))
        .join(ChatSession)
        .filter(ChatSession.organization_id == org_id)
        .scalar()
        or 0
    )
    total_tokens = (
        db.query(func.coalesce(func.sum(LLMUsage.total_tokens), 0))
        .filter(LLMUsage.organization_id == org_id)
        .scalar()
        or 0
    )
    total_chatbots = (
        db.query(func.count(Chatbot.id))
        .filter(Chatbot.organization_id == org_id)
        .scalar()
        or 0
    )
    active_chatbots = (
        db.query(func.count(Chatbot.id))
        .filter(
            Chatbot.organization_id == org_id,
            Chatbot.id.in_(
                db.query(ChatSession.chatbot_id)
                .filter(ChatSession.organization_id == org_id)
                .distinct()
                .subquery()
            ),
        )
        .scalar()
        or 0
    )

    return OrgAnalyticsResponse(
        organization_id=org_id,
        total_sessions=total_sessions,
        total_messages=total_messages,
        total_tokens=total_tokens,
        total_chatbots=total_chatbots,
        active_chatbots=active_chatbots,
    )


@router.get("/analytics/source/{source_id}", response_model=SourceAnalyticsResponse)
def get_source_analytics(
    source_id: UUID,
    db: Session = Depends(get_db_with_org),
    user: User = Depends(get_current_user),
):
    source = (
        db.query(KnowledgeSource)
        .filter(
            KnowledgeSource.id == source_id,
            KnowledgeSource.organization_id == user.organization_id,
        )
        .first()
    )
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge source not found",
        )

    row = (
        db.query(
            func.coalesce(func.sum(DailyAnalytics.retrieval_count), 0),
            func.coalesce(func.sum(DailyAnalytics.sync_success_count), 0),
            func.coalesce(func.sum(DailyAnalytics.sync_failure_count), 0),
        )
        .filter(DailyAnalytics.source_id == source_id)
        .first()
    )

    return SourceAnalyticsResponse(
        source_id=source_id,
        retrieval_count=row[0] or 0,
        sync_success_count=row[1] or 0,
        sync_failure_count=row[2] or 0,
    )


@router.get("/admin/analytics/platform", response_model=PlatformAnalyticsResponse)
def get_platform_analytics(
    db: Session = Depends(get_db_admin),
    admin: User = Depends(require_platform_admin),
):
    return PlatformAnalyticsResponse(
        total_organizations=db.query(func.count(Organization.id)).scalar() or 0,
        total_chatbots=db.query(func.count(Chatbot.id)).scalar() or 0,
        total_sessions=db.query(func.count(ChatSession.id)).scalar() or 0,
        total_messages=db.query(func.count(Message.id)).scalar() or 0,
        total_tokens=db.query(func.coalesce(func.sum(LLMUsage.total_tokens), 0)).scalar() or 0,
        total_api_calls=db.query(func.count(AnalyticsEvent.id)).scalar() or 0,
    )


@router.post("/analytics/events")
def track_event(
    event_type: str,
    entity_id: str | None = None,
    chatbot_id: str | None = None,
    source_id: str | None = None,
    payload: dict = {},
    db: Session = Depends(get_db_with_org),
    user: User = Depends(get_current_user),
):
    event = AnalyticsEvent(
        event_type=event_type,
        entity_id=UUID(entity_id) if entity_id else None,
        organization_id=user.organization_id,
        chatbot_id=UUID(chatbot_id) if chatbot_id else None,
        source_id=UUID(source_id) if source_id else None,
        payload=payload,
    )
    db.add(event)
    db.commit()
    return {"status": "tracked"}
