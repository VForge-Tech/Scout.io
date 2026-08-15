"""Plan limit enforcement helpers.

These are called at the API layer before creating chatbots, knowledge sources,
or processing widget messages. All checks are scoped to the caller's own
organization, and raise HTTP 402 errors with a clear message the frontend can
surface (e.g. a banner linking to the billing page).
"""

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.billing.plans import PLANS, PlanTier, get_plan
from app.core.config import get_settings
from app.models import ChatSession, Chatbot, KnowledgeSource, Message, Organization


def _current_month_start() -> datetime:
    now = datetime.now(timezone.utc)
    return datetime(now.year, now.month, 1, tzinfo=timezone.utc)


def billing_enabled() -> bool:
    """Whether billing/plan enforcement is turned on for this deployment."""
    return get_settings().billing_enabled


def resolve_plan(org: Organization) -> PlanTier:
    """Return the effective plan for an org, respecting suspended plans."""
    plan = get_plan(org.plan)
    # A non-active status (cancelled/halted) downgrades the org to the free tier
    if org.plan_status not in ("active", "trialing"):
        plan = get_plan("free")
    return plan


def assert_chatbot_limit(db: Session, org: Organization) -> None:
    """Reject chatbot creation when the org is at its plan's chatbot limit.

    No-op when billing is disabled (testing/dev builds).
    """
    if not billing_enabled():
        return
    plan = resolve_plan(org)
    count = (
        db.query(func.count(Chatbot.id))
        .filter(Chatbot.organization_id == org.id)
        .scalar()
        or 0
    )
    if count >= plan.chatbot_limit:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                f"Your {plan.name} plan allows up to {plan.chatbot_limit} chatbots. "
                "Please upgrade your plan to create more."
            ),
        )


def assert_knowledge_source_limit(db: Session, org: Organization) -> None:
    """Reject knowledge source creation when the org is at its plan's limit.

    No-op when billing is disabled (testing/dev builds).
    """
    if not billing_enabled():
        return
    plan = resolve_plan(org)
    count = (
        db.query(func.count(KnowledgeSource.id))
        .filter(KnowledgeSource.organization_id == org.id)
        .scalar()
        or 0
    )
    if count >= plan.knowledge_source_limit:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                f"Your {plan.name} plan allows up to {plan.knowledge_source_limit} "
                "knowledge sources. Please upgrade your plan to add more."
            ),
        )


def assert_message_quota(db: Session, org: Organization) -> None:
    """Reject widget message processing when the org exceeds its monthly volume.

    No-op when billing is disabled (testing/dev builds).
    """
    if not billing_enabled():
        return
    plan = resolve_plan(org)
    month_start = _current_month_start()
    count = (
        db.query(func.count(Message.id))
        .join(ChatSession)
        .filter(
            ChatSession.organization_id == org.id,
            Message.created_at >= month_start,
        )
        .scalar()
        or 0
    )
    if count >= plan.monthly_message_limit:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                f"Your {plan.name} plan allows {plan.monthly_message_limit:,} "
                "messages per month. You've reached your limit. "
                "Please upgrade your plan to continue."
            ),
        )


def usage_summary(db: Session, org: Organization) -> dict:
    """Return current usage vs plan limits for the billing UI."""
    plan = resolve_plan(org)
    chatbot_count = (
        db.query(func.count(Chatbot.id))
        .filter(Chatbot.organization_id == org.id)
        .scalar()
        or 0
    )
    source_count = (
        db.query(func.count(KnowledgeSource.id))
        .filter(KnowledgeSource.organization_id == org.id)
        .scalar()
        or 0
    )
    message_count = (
        db.query(func.count(Message.id))
        .join(ChatSession)
        .filter(
            ChatSession.organization_id == org.id,
            Message.created_at >= _current_month_start(),
        )
        .scalar()
        or 0
    )
    return {
        "billing_enabled": billing_enabled(),
        "plan": plan.key,
        "plan_name": plan.name,
        "plan_status": org.plan_status,
        "limits": {
            "chatbots": plan.chatbot_limit,
            "monthly_messages": plan.monthly_message_limit,
            "knowledge_sources": plan.knowledge_source_limit,
        },
        "usage": {
            "chatbots": chatbot_count,
            "monthly_messages": message_count,
            "knowledge_sources": source_count,
        },
        "available_plans": [
            {
                "key": p.key,
                "name": p.name,
                "price_inr": p.price_inr,
                "description": p.description,
                "features": p.features,
                "limits": {
                    "chatbots": p.chatbot_limit,
                    "monthly_messages": p.monthly_message_limit,
                    "knowledge_sources": p.knowledge_source_limit,
                },
            }
            for p in PLANS.values()
        ],
    }