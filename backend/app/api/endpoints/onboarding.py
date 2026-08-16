from collections import defaultdict
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db_admin, get_db_with_org, require_platform_admin
from app.models import (
    AnalyticsEvent,
    ChatSession,
    Chatbot,
    KnowledgeSource,
    Organization,
    User,
)
from app.schemas.analytics import (
    FeedbackCreate,
    FeedbackItem,
    FunnelOrgRow,
    OnboardingChecklistResponse,
    OnboardingFunnelResponse,
    OnboardingStepInfo,
)

router = APIRouter(tags=["onboarding", "feedback"])

ONBOARDING_STEPS = [
    {"step": "create_chatbot", "label": "Create your first chatbot"},
    {"step": "add_knowledge_source", "label": "Add your first knowledge source"},
    {"step": "test_widget", "label": "Test your widget"},
    {"step": "invite_teammate", "label": "Invite a teammate"},
]


def _compute_steps(db: Session, org_id: UUID) -> dict[str, bool]:
    has_chatbot = (
        db.query(Chatbot.id).filter(Chatbot.organization_id == org_id).first() is not None
    )
    has_source = (
        db.query(KnowledgeSource.id)
        .filter(KnowledgeSource.organization_id == org_id)
        .first()
        is not None
    )
    has_session = (
        db.query(ChatSession.id).filter(ChatSession.organization_id == org_id).first() is not None
    )
    user_count = (
        db.query(func.count(User.id)).filter(User.organization_id == org_id).scalar() or 0
    )
    return {
        "create_chatbot": has_chatbot,
        "add_knowledge_source": has_source,
        "test_widget": has_session,
        "invite_teammate": user_count >= 2,
    }


def _record_completed_steps(db: Session, org_id: UUID, state: dict[str, bool]) -> None:
    recorded: set[str] = set()
    for ev in (
        db.query(AnalyticsEvent)
        .filter(
            AnalyticsEvent.organization_id == org_id,
            AnalyticsEvent.event_type == "onboarding.step",
        )
        .all()
    ):
        step = (ev.payload or {}).get("step")
        if step:
            recorded.add(step)

    for item in ONBOARDING_STEPS:
        step = item["step"]
        if state[step] and step not in recorded:
            db.add(
                AnalyticsEvent(
                    event_type="onboarding.step",
                    organization_id=org_id,
                    payload={"step": step, "label": item["label"]},
                )
            )
    db.commit()


@router.get("/analytics/onboarding", response_model=OnboardingChecklistResponse)
def get_onboarding_checklist(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_with_org),
):
    state = _compute_steps(db, user.organization_id)
    _record_completed_steps(db, user.organization_id, state)
    steps = [
        OnboardingStepInfo(step=item["step"], label=item["label"], completed=state[item["step"]])
        for item in ONBOARDING_STEPS
    ]
    return OnboardingChecklistResponse(
        steps=steps,
        completed_count=sum(1 for s in steps if s.completed),
    )


@router.post("/analytics/feedback")
def submit_feedback(
    payload: FeedbackCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_with_org),
):
    event = AnalyticsEvent(
        event_type="feedback",
        organization_id=user.organization_id,
        chatbot_id=UUID(payload.chatbot_id) if payload.chatbot_id else None,
        source_id=UUID(payload.source_id) if payload.source_id else None,
        payload={
            "rating": payload.rating,
            "message": payload.message,
            "context": payload.context,
        },
    )
    db.add(event)
    db.commit()
    return {"status": "tracked"}


@router.get("/admin/onboarding/funnel", response_model=OnboardingFunnelResponse)
def get_onboarding_funnel(
    admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db_admin),
):
    orgs = db.query(Organization).order_by(Organization.created_at).all()
    org_names = {org.id: org.name for org in orgs}

    steps_by_org: dict[UUID, list[str]] = defaultdict(list)
    for ev in (
        db.query(AnalyticsEvent)
        .filter(AnalyticsEvent.event_type == "onboarding.step")
        .all()
    ):
        step = (ev.payload or {}).get("step")
        if step:
            steps_by_org[ev.organization_id].append(step)

    feedback_events = (
        db.query(AnalyticsEvent)
        .filter(AnalyticsEvent.event_type == "feedback")
        .order_by(AnalyticsEvent.timestamp.desc())
        .all()
    )

    funnel = []
    for org in orgs:
        state = _compute_steps(db, org.id)
        funnel.append(
            FunnelOrgRow(
                organization_id=org.id,
                name=org.name,
                created_at=org.created_at,
                steps_completed=sorted(steps_by_org.get(org.id, [])),
                has_chatbot=state["create_chatbot"],
                has_knowledge_source=state["add_knowledge_source"],
                has_widget_session=state["test_widget"],
                has_teammate=state["invite_teammate"],
            )
        )

    feedback = [
        FeedbackItem(
            id=ev.id,
            organization_id=ev.organization_id,
            org_name=org_names.get(ev.organization_id),
            chatbot_id=ev.chatbot_id,
            source_id=ev.source_id,
            rating=(ev.payload or {}).get("rating"),
            message=(ev.payload or {}).get("message"),
            context=(ev.payload or {}).get("context"),
            timestamp=ev.timestamp,
        )
        for ev in feedback_events
    ]

    summary = {
        "total_organizations": len(funnel),
        "with_chatbot": sum(1 for row in funnel if row.has_chatbot),
        "with_knowledge_source": sum(1 for row in funnel if row.has_knowledge_source),
        "with_widget_session": sum(1 for row in funnel if row.has_widget_session),
        "with_teammate": sum(1 for row in funnel if row.has_teammate),
        "feedback_up": sum(1 for item in feedback if item.rating == "up"),
        "feedback_down": sum(1 for item in feedback if item.rating == "down"),
    }

    return OnboardingFunnelResponse(summary=summary, funnel=funnel, feedback=feedback)