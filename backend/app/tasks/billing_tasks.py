"""Usage-based billing aggregation Celery beat task.

Runs daily (see ``beat_schedule``) and, for each organization that consumed
tokens in the current billing period:

- Aggregates LLMUsage rows into total prompt/completion tokens + estimated cost.
- Upserts a ``UsageBillingRecord`` (one per org per "YYYY-MM" period).
- When a paid plan's included monthly token allowance is exceeded, reports the
  overage to Razorpay as a subscription add-on (billed on the next invoice).
  Razorpay has no native usage-metering API, so if the add-on cannot be created
  (no subscription, no overage price configured, or API failure) we fall back to
  tracking the overage internally (``reported_to_razorpay=False``) and expose it
  on the billing page so it can be invoiced manually at period end.
- Fires a ``billing.usage_soft_limit`` AnalyticsEvent once per period when usage
  crosses 80% of the plan's included tokens, which the billing UI surfaces as a
  warning banner.
"""

import logging
from datetime import date, datetime, timezone

from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

celery_app = Celery(
    "scout-billing",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    broker_connection_retry_on_startup=False,
    include=["app.tasks.billing_tasks", "app.tasks.analytics_tasks"],
)
celery_app.conf.broker_connection_timeout = 2
celery_app.conf.result_backend_timeout = 2

celery_app.conf.beat_schedule = {
    "aggregate-usage-billing-daily": {
        "task": "app.tasks.billing_tasks.aggregate_usage_billing",
        "schedule": crontab(hour=3, minute=0),
    },
}

SOFT_LIMIT_RATIO = 0.8


def _month_bounds(period: str | None) -> tuple[datetime, datetime, str]:
    """Resolve a "YYYY-MM" period into (start, end, key).

    Defaults to the current calendar month when no period is given.
    """
    now = datetime.now(timezone.utc)
    if period:
        year_str, month_str = period.split("-")
        start = datetime(int(year_str), int(month_str), 1, tzinfo=timezone.utc)
    else:
        start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

    if start.month == 12:
        end = datetime(start.year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(start.year, start.month + 1, 1, tzinfo=timezone.utc)

    return start, end, start.strftime("%Y-%m")


def _report_overage_to_razorpay(
    org, overage_tokens: int, overage_cost: int, period_key: str
) -> tuple[bool, str | None]:
    """Attempt a Razorpay add-on for the overage. Returns (reported, addon_id)."""
    from app.core.billing import razorpay_client
    from app.core.billing.limits import billing_enabled
    from app.core.billing.pricing import overage_amount_paise, trim_overage_for_addon

    if not billing_enabled():
        return False, None
    if not org.razorpay_subscription_id or overage_cost <= 0:
        return False, None

    from app.core.billing.plans import get_plan

    plan = get_plan(org.plan)
    billable, _deferred = trim_overage_for_addon(overage_tokens)
    amount_paise = overage_amount_paise(billable, plan.overage_price_paise_per_1k)
    if amount_paise <= 0:
        return False, None

    try:
        addon = razorpay_client.create_addon(
            subscription_id=org.razorpay_subscription_id,
            name=f"Token overage — {period_key}",
            amount_paise=amount_paise,
            description=(
                f"{billable:,} tokens over the {plan.name} plan's included "
                f"allowance for {period_key}."
            ),
            notes={"organization_id": str(org.id), "period": period_key},
        )
        addon_id = addon.get("id") if isinstance(addon, dict) else None
        logger.info(
            "Reported %d paise token overage to Razorpay add-on %s for org %s",
            amount_paise,
            addon_id,
            org.id,
        )
        return True, addon_id
    except razorpay_client.RazorpayError as e:
        logger.warning(
            "Razorpay add-on failed for org %s (tracking internally): %s", org.id, e
        )
        return False, None


@celery_app.task
def aggregate_usage_billing(period: str | None = None):
    """Aggregate LLMUsage per org for a billing period and report overages."""
    from sqlalchemy import func

    from app.core.billing.limits import resolve_plan
    from app.core.billing.pricing import overage_amount_paise
    from app.db.session import SessionLocal
    from app.models import AnalyticsEvent, LLMUsage, Organization, UsageBillingRecord

    period_start, period_end, period_key = _month_bounds(period)

    db = SessionLocal()
    try:
        org_ids = db.query(LLMUsage.organization_id).distinct().all()
        results = []

        for (org_id,) in org_ids:
            org = (
                db.query(Organization).filter(Organization.id == org_id).first()
            )
            if not org:
                continue

            agg = (
                db.query(
                    func.coalesce(func.sum(LLMUsage.prompt_tokens), 0),
                    func.coalesce(func.sum(LLMUsage.completion_tokens), 0),
                    func.coalesce(func.sum(LLMUsage.total_tokens), 0),
                    func.coalesce(func.sum(LLMUsage.cost), 0),
                )
                .filter(
                    LLMUsage.organization_id == org_id,
                    LLMUsage.timestamp >= period_start,
                    LLMUsage.timestamp < period_end,
                )
                .first()
            )
            prompt_tokens, completion_tokens, total_tokens, estimated_cost = (
                int(agg[0]),
                int(agg[1]),
                int(agg[2]),
                int(agg[3]),
            )

            plan = resolve_plan(org)
            included = plan.included_monthly_tokens
            overage_tokens = max(0, total_tokens - included)
            overage_cost = overage_amount_paise(
                overage_tokens, plan.overage_price_paise_per_1k
            )

            record = (
                db.query(UsageBillingRecord)
                .filter(
                    UsageBillingRecord.organization_id == org_id,
                    UsageBillingRecord.period == period_key,
                )
                .first()
            )
            if not record:
                record = UsageBillingRecord(
                    organization_id=org_id,
                    period=period_key,
                )
                db.add(record)

            record.prompt_tokens = prompt_tokens
            record.completion_tokens = completion_tokens
            record.total_tokens = total_tokens
            record.estimated_cost = estimated_cost
            record.overage_tokens = overage_tokens
            record.overage_cost = overage_cost

            # Report overage to Razorpay once per period.
            if (
                overage_tokens > 0
                and not record.reported_to_razorpay
                and plan.price_inr > 0
            ):
                reported, addon_id = _report_overage_to_razorpay(
                    org, overage_tokens, overage_cost, period_key
                )
                record.reported_to_razorpay = reported
                record.razorpay_addon_id = addon_id

            # Soft-limit warning (once per period).
            if included > 0 and total_tokens >= int(included * SOFT_LIMIT_RATIO):
                existing = (
                    db.query(AnalyticsEvent.id)
                    .filter(
                        AnalyticsEvent.organization_id == org_id,
                        AnalyticsEvent.event_type == "billing.usage_soft_limit",
                        AnalyticsEvent.timestamp >= period_start,
                        AnalyticsEvent.timestamp < period_end,
                    )
                    .first()
                )
                if not existing:
                    db.add(
                        AnalyticsEvent(
                            event_type="billing.usage_soft_limit",
                            entity_id=org_id,
                            organization_id=org_id,
                            payload={
                                "period": period_key,
                                "total_tokens": total_tokens,
                                "included_tokens": included,
                                "ratio": round(total_tokens / included, 3)
                                if included
                                else 0,
                                "plan": plan.key,
                            },
                        )
                    )

            results.append(
                {
                    "organization_id": str(org_id),
                    "period": period_key,
                    "tokens": total_tokens,
                    "cost": estimated_cost,
                    "reported_to_razorpay": record.reported_to_razorpay,
                }
            )

            db.commit()

        return {
            "status": "completed",
            "period": period_key,
            "organizations": len(results),
            "records": results,
        }
    except Exception as e:
        logger.exception("Usage billing aggregation failed")
        db.rollback()
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()