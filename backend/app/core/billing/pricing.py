"""Per-model token cost estimation (used for usage-based billing).

Prices are expressed in **paise per 1,000 tokens** (1 INR = 100 paise) so they
align with Razorpay's integer-amount convention. These are internal estimates
used to (a) populate ``LLMUsage.cost`` when recording a generation and (b) price
usage overage as a Razorpay add-on on the org's subscription.

They are intentionally approximate; update them to match your negotiated model
pricing before enabling live usage billing.
"""

from typing import Optional

# model substring -> (input_paise_per_1k, output_paise_per_1k)
MODEL_PRICING: dict[str, tuple[int, int]] = {
    "gpt-3.5-turbo": (10, 20),
    "gpt-4o-mini": (5, 20),
    "gpt-4o": (30, 120),
    "gpt-4": (30, 120),
    "claude-3-haiku": (5, 25),
    "claude-3-5-haiku": (5, 25),
    "claude-3-sonnet": (40, 160),
    "claude-3-5-sonnet": (40, 160),
    "claude-3-opus": (200, 800),
    "gemini-pro": (15, 60),
    "llama-3.1-8b": (5, 10),
}

# Fallback used when a model isn't listed (conservative "medium" pricing).
DEFAULT_PRICING: tuple[int, int] = (15, 60)

MAX_OVERAGE_TOKENS_PER_ADDON = 5_000_000


def get_model_pricing(model: str) -> tuple[int, int]:
    """Return (input, output) price in paise per 1K tokens for a model.

    Matching is substring-based and case-insensitive so provider prefixes like
    ``openai/`` are ignored.
    """
    if not model:
        return DEFAULT_PRICING
    lowered = model.lower()
    for key, prices in MODEL_PRICING.items():
        if key in lowered:
            return prices
    return DEFAULT_PRICING


def estimate_cost_paise(
    model: str, prompt_tokens: int, completion_tokens: int
) -> int:
    """Estimate the cost of a generation in paise."""
    input_price, output_price = get_model_pricing(model)
    cost = (
        (prompt_tokens or 0) * input_price / 1000
        + (completion_tokens or 0) * output_price / 1000
    )
    return round(cost)


def overage_amount_paise(
    overage_tokens: int, price_paise_per_1k: int
) -> int:
    """Convert overage tokens into a paise amount for a Razorpay add-on."""
    return round(overage_tokens * price_paise_per_1k / 1000)


def trim_overage_for_addon(overage_tokens: int) -> tuple[int, int]:
    """Split overage tokens into (billable_now, deferred).

    Razorpay add-ons are capped at a reasonable token batch per charge so a
    single enormous period doesn't produce one giant add-on. The remainder is
    deferred and can be billed in a follow-up add-on.
    """
    if overage_tokens <= MAX_OVERAGE_TOKENS_PER_ADDON:
        return overage_tokens, 0
    return MAX_OVERAGE_TOKENS_PER_ADDON, overage_tokens - MAX_OVERAGE_TOKENS_PER_ADDON


def format_estimate_paise(paise: int) -> str:
    """Human readable INR from a paise integer (e.g. 12345 -> ₹123.45)."""
    rupees = paise / 100
    if paise % 100 == 0:
        return f"₹{rupees:,.0f}"
    return f"₹{rupees:,.2f}"