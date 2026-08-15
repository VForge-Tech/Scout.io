from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_db_with_org
from app.core.billing import razorpay_client
from app.core.billing.limits import billing_enabled, usage_summary
from app.core.billing.plans import PLANS, PlanTier, get_plan
from app.models import Organization, User
from app.schemas.billing import (
    CancelSubscriptionRequest,
    CancelSubscriptionResponse,
    ChangePlanRequest,
    ChangePlanResponse,
    CheckoutSessionRequest,
    CheckoutSessionResponse,
    InvoiceRead,
    SubscriptionDetail,
    WebhookResponse,
)
from app.utils.audit import create_audit_log

router = APIRouter(tags=["billing"])


def _require_billing_enabled() -> None:
    if not billing_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Billing is not enabled in this environment",
        )


def _get_org(db: Session, org_id: UUID) -> Organization:
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )
    return org


def _plan_for_razorpay(plan_id: str | None) -> PlanTier | None:
    """Reverse-lookup a PlanTier from its Razorpay plan id."""
    if not plan_id:
        return None
    for plan in PLANS.values():
        if plan.razorpay_plan_id == plan_id:
            return plan
    return None


def _to_dt(ts: int | None) -> datetime | None:
    return datetime.fromtimestamp(ts, tz=timezone.utc) if ts else None


@router.get("/organizations/me/billing")
def get_billing(
    db: Session = Depends(get_db_with_org),
    user: User = Depends(get_current_user),
):
    org = _get_org(db, user.organization_id)
    return usage_summary(db, org)


@router.post(
    "/organizations/me/billing/checkout-session",
    response_model=CheckoutSessionResponse,
)
def create_checkout_session(
    payload: CheckoutSessionRequest,
    request: Request,
    db: Session = Depends(get_db_with_org),
    user: User = Depends(get_current_user),
):
    """Create a Razorpay Subscription for the plan the user selects.

    Ensures a Razorpay customer exists for the org, then creates a subscription
    against the plan's configured Razorpay Plan ID. The returned checkout/short
    URL is where the user completes payment (Razorpay-hosted).
    """
    _require_billing_enabled()
    plan = get_plan(payload.plan)
    if plan.price_inr <= 0 or payload.plan not in PLANS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported plan. Choose one of: starter, growth, scale.",
        )

    org = _get_org(db, user.organization_id)

    try:
        customer = razorpay_client.create_customer(
            org_id=str(org.id),
            org_name=org.name,
            email=user.email,
        )
        subscription = razorpay_client.create_subscription(
            customer_id=customer["id"],
            plan_key=plan.key,
            org_id=str(org.id),
            org_name=org.name,
        )
    except razorpay_client.RazorpayError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        ) from e

    org.razorpay_customer_id = customer["id"]
    org.razorpay_subscription_id = subscription["id"]
    db.commit()

    create_audit_log(
        db,
        action="billing.checkout_session_created",
        user_id=user.id,
        organization_id=org.id,
        details={
            "plan": plan.key,
            "customer_id": customer["id"],
            "subscription_id": subscription["id"],
        },
        ip_address=request.client.host if request.client else None,
    )

    return CheckoutSessionResponse(
        subscription_id=subscription["id"],
        checkout_url=subscription.get("short_url"),
        plan=plan.key,
        status=subscription.get("status", "created"),
    )


@router.get(
    "/organizations/me/billing/subscription",
    response_model=SubscriptionDetail,
)
def get_subscription_detail(
    db: Session = Depends(get_db_with_org),
    user: User = Depends(get_current_user),
):
    """Return the org's Razorpay subscription + invoice history.

    New signups with no active subscription return ``has_subscription=False`` so
    the frontend can render a clear trial/free state instead of an error.
    """
    _require_billing_enabled()
    org = _get_org(db, user.organization_id)

    if not org.razorpay_subscription_id:
        return SubscriptionDetail(has_subscription=False)

    try:
        sub = razorpay_client.fetch_subscription(org.razorpay_subscription_id)
    except razorpay_client.RazorpayError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        ) from e

    plan = _plan_for_razorpay(sub.get("plan_id"))
    invoices = []
    try:
        for inv in razorpay_client.list_subscription_invoices(org.razorpay_subscription_id):
            invoices.append(
                InvoiceRead(
                    id=inv.get("id"),
                    status=inv.get("status"),
                    amount_paise=inv.get("amount"),
                    currency=inv.get("currency"),
                    issued_at=_to_dt(inv.get("issued_at")),
                    paid_at=_to_dt(inv.get("paid_at")),
                )
            )
    except razorpay_client.RazorpayError:
        # Invoice history is best-effort; don't fail the whole detail view.
        invoices = []

    return SubscriptionDetail(
        has_subscription=True,
        subscription_id=org.razorpay_subscription_id,
        plan_id=sub.get("plan_id"),
        plan_key=plan.key if plan else org.plan,
        status=sub.get("status"),
        current_start=_to_dt(sub.get("current_start")),
        current_end=_to_dt(sub.get("current_end")),
        next_charge_on=_to_dt(sub.get("charge_at")),
        payment_method=sub.get("payment_method"),
        cancel_at_cycle_end=sub.get("cancel_at_cycle_end"),
        invoices=invoices,
    )


@router.post(
    "/organizations/me/billing/subscription/change-plan",
    response_model=ChangePlanResponse,
)
def change_plan(
    payload: ChangePlanRequest,
    request: Request,
    db: Session = Depends(get_db_with_org),
    user: User = Depends(get_current_user),
):
    """Upgrade/downgrade the org's existing subscription via Razorpay's API.

    Razorpay has no self-serve portal, so plan changes call ``subscription.edit``
    directly. ``schedule_change_at`` = ``now`` (immediate) or ``cycle_end``.
    """
    _require_billing_enabled()
    plan = get_plan(payload.plan)
    if plan.price_inr <= 0 or payload.plan not in PLANS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported plan. Choose one of: starter, growth, scale.",
        )
    if payload.schedule_change_at not in ("now", "cycle_end"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="schedule_change_at must be 'now' or 'cycle_end'.",
        )

    org = _get_org(db, user.organization_id)
    if not org.razorpay_subscription_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active subscription to change. Subscribe to a plan first.",
        )

    try:
        updated = razorpay_client.update_subscription(
            org.razorpay_subscription_id,
            plan_id=plan.razorpay_plan_id,
            schedule_change_at=payload.schedule_change_at,
        )
    except razorpay_client.RazorpayError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        ) from e

    # Reflect the new plan immediately so limits update right away (webhook
    # confirms the charge).
    org.plan = plan.key
    db.commit()

    create_audit_log(
        db,
        action="billing.plan_changed",
        user_id=user.id,
        organization_id=org.id,
        details={
            "plan": plan.key,
            "schedule_change_at": payload.schedule_change_at,
            "subscription_id": org.razorpay_subscription_id,
        },
        ip_address=request.client.host if request.client else None,
    )

    return ChangePlanResponse(
        subscription_id=org.razorpay_subscription_id,
        plan=plan.key,
        schedule_change_at=payload.schedule_change_at,
        status=updated.get("status"),
        next_charge_on=_to_dt(updated.get("charge_at")),
    )


@router.post(
    "/organizations/me/billing/subscription/cancel",
    response_model=CancelSubscriptionResponse,
)
def cancel_subscription(
    payload: CancelSubscriptionRequest,
    request: Request,
    db: Session = Depends(get_db_with_org),
    user: User = Depends(get_current_user),
):
    """Cancel the org's Razorpay subscription.

    Defaults to ``cancel_at_cycle_end=True`` so the customer keeps access until
    the paid period ends — the org keeps its plan until Razorpay fires
    ``subscription.cancelled`` at cycle end (which flips enforcement). An
    immediate cancel (``cancel_at_cycle_end=False``) flags the org as cancelled
    right away.
    """
    _require_billing_enabled()
    org = _get_org(db, user.organization_id)
    if not org.razorpay_subscription_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active subscription to cancel.",
        )

    try:
        cancelled = razorpay_client.cancel_subscription(
            org.razorpay_subscription_id,
            cancel_at_cycle_end=payload.cancel_at_cycle_end,
        )
    except razorpay_client.RazorpayError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        ) from e

    if not payload.cancel_at_cycle_end:
        org.plan_status = "cancelled"
        db.commit()

    create_audit_log(
        db,
        action="billing.plan_cancelled",
        user_id=user.id,
        organization_id=org.id,
        details={
            "subscription_id": org.razorpay_subscription_id,
            "cancel_at_cycle_end": payload.cancel_at_cycle_end,
        },
        ip_address=request.client.host if request.client else None,
    )

    return CancelSubscriptionResponse(
        subscription_id=org.razorpay_subscription_id,
        status=cancelled.get("status"),
        cancel_at_cycle_end=payload.cancel_at_cycle_end,
        current_end=_to_dt(cancelled.get("current_end")),
    )


@router.post(
    "/webhooks/razorpay",
    response_model=WebhookResponse,
)
async def razorpay_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Razorpay subscription webhooks.

    Verifies the X-Razorpay-Signature header (HMAC-SHA256 of the raw body) before
    trusting any event. Handles subscription.activated, subscription.charged,
    subscription.cancelled, and subscription.halted, updating the org's plan and
    status accordingly. Unsigned or invalidly-signed payloads are rejected.
    """
    _require_billing_enabled()
    raw_body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature")

    if not razorpay_client.verify_webhook_signature(raw_body, signature):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Razorpay webhook signature",
        )

    import json

    try:
        event = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        )

    event_type = event.get("event", "")
    entity = (event.get("payload") or {}).get("subscription") or {}
    subscription_data = entity.get("entity") or {}
    sub_id = subscription_data.get("id")
    notes = subscription_data.get("notes") or {}
    org_id = notes.get("organization_id")

    if not org_id:
        # Fall back to matching by stored subscription id
        org = (
            db.query(Organization)
            .filter(Organization.razorpay_subscription_id == sub_id)
            .first()
        ) if sub_id else None
    else:
        try:
            org = _get_org(db, UUID(str(org_id)))
        except HTTPException:
            org = None

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found for webhook event",
        )

    plan_key = notes.get("plan") or org.plan

    if event_type == "subscription.activated":
        org.plan = plan_key
        org.plan_status = "active"
        org.razorpay_subscription_id = sub_id or org.razorpay_subscription_id
        action = "billing.plan_activated"
    elif event_type == "subscription.charged":
        org.plan_status = "active"
        action = "billing.subscription_charged"
    elif event_type == "subscription.cancelled":
        org.plan_status = "cancelled"
        action = "billing.plan_cancelled"
    elif event_type == "subscription.halted":
        org.plan_status = "halted"
        action = "billing.plan_halted"
    else:
        # Acknowledge but ignore unknown subscription events
        db.rollback()
        return WebhookResponse(status="ignored", event=event_type)

    db.commit()

    create_audit_log(
        db,
        action=action,
        organization_id=org.id,
        details={
            "event": event_type,
            "subscription_id": sub_id,
            "plan": org.plan,
            "plan_status": org.plan_status,
        },
    )

    return WebhookResponse(status="ok", event=event_type)