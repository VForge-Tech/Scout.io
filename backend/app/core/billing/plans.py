"""Plan tier definitions and limits.

Plan tiers are enforced at the API layer (see app/core/billing/limits.py).
Razorpay plan IDs are created in the Razorpay dashboard (test mode for now) and
referenced by their stable keys below.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PlanTier:
    key: str
    name: str
    price_inr: int  # monthly price in INR (paise will be derived by Razorpay)
    chatbot_limit: int
    monthly_message_limit: int
    knowledge_source_limit: int
    description: str
    razorpay_plan_id: str = ""
    features: list[str] = field(default_factory=list)
    # Usage-based component: tokens included each month and the per-1K-token
    # overage price in paise (used by the billing beat task).
    included_monthly_tokens: int = 0
    overage_price_paise_per_1k: int = 0


PLANS: dict[str, PlanTier] = {
    "free": PlanTier(
        key="free",
        name="Free",
        price_inr=0,
        chatbot_limit=1,
        monthly_message_limit=1_000,
        knowledge_source_limit=5,
        description="For individuals exploring Scout.io.",
        features=["1 chatbot", "1,000 messages / month", "5 knowledge sources"],
        included_monthly_tokens=100_000,
    ),
    "starter": PlanTier(
        key="starter",
        name="Starter",
        price_inr=2_999,
        chatbot_limit=3,
        monthly_message_limit=10_000,
        knowledge_source_limit=20,
        description="For small teams getting started with AI knowledge bases.",
        razorpay_plan_id="plan_starter",
        features=["3 chatbots", "10,000 messages / month", "20 knowledge sources"],
        included_monthly_tokens=1_000_000,
        overage_price_paise_per_1k=40,
    ),
    "growth": PlanTier(
        key="growth",
        name="Growth",
        price_inr=9_999,
        chatbot_limit=10,
        monthly_message_limit=100_000,
        knowledge_source_limit=100,
        description="For growing teams with active production chatbots.",
        razorpay_plan_id="plan_growth",
        features=["10 chatbots", "100,000 messages / month", "100 knowledge sources"],
        included_monthly_tokens=5_000_000,
        overage_price_paise_per_1k=30,
    ),
    "scale": PlanTier(
        key="scale",
        name="Scale",
        price_inr=29_999,
        chatbot_limit=50,
        monthly_message_limit=1_000_000,
        knowledge_source_limit=500,
        description="For large organizations at high volume.",
        razorpay_plan_id="plan_scale",
        features=["50 chatbots", "1,000,000 messages / month", "500 knowledge sources"],
        included_monthly_tokens=25_000_000,
        overage_price_paise_per_1k=20,
    ),
}

FREE_PLAN = PLANS["free"]


def get_plan(key: str | None) -> PlanTier:
    """Resolve a plan key, falling back to the free plan for unknown/None values."""
    if not key:
        return FREE_PLAN
    return PLANS.get(key, FREE_PLAN)


def is_paid_plan(key: str | None) -> bool:
    return get_plan(key).price_inr > 0