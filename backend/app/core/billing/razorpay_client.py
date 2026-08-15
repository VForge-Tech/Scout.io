"""Razorpay client wrapper and webhook signature verification.

Uses Razorpay's official SDK. Keys are read from Settings (provisioned via the
Vault wrapper in app/core/secrets.py). The codebase never hardcodes keys; only
test-mode keys should ever be configured for now.
"""

import base64
import hashlib
import hmac
import logging

import razorpay

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class RazorpayError(Exception):
    """Raised when a Razorpay API call fails."""


def get_client() -> razorpay.Client:
    """Build a Razorpay client from configured (Vault-backed) test keys."""
    settings = get_settings()
    if not settings.razorpay_key_id or not settings.razorpay_key_secret:
        raise RazorpayError(
            "Razorpay is not configured. Set razorpay_key_id / razorpay_key_secret "
            "via Vault or environment variables (test-mode keys)."
        )
    return razorpay.Client(
        auth=(settings.razorpay_key_id, settings.razorpay_key_secret)
    )


def verify_webhook_signature(
    payload: bytes, signature: str | None, webhook_secret: str | None = None
) -> bool:
    """Verify the X-Razorpay-Signature header (HMAC-SHA256 of the raw body).

    Razorpay signs the raw request body with the webhook secret using HMAC-SHA256
    and base64-encodes the digest into the X-Razorpay-Signature header. We never
    trust unsigned payloads.
    """
    if not signature:
        return False
    secret = webhook_secret or get_settings().razorpay_webhook_secret
    if not secret:
        logger.warning("Razorpay webhook secret not configured; rejecting signature")
        return False
    expected = hmac.new(
        secret.encode("utf-8"), payload, hashlib.sha256
    ).digest()
    provided = base64.b64decode(signature, validate=False)
    return hmac.compare_digest(expected, provided)


def create_customer(org_id: str, org_name: str, email: str | None = None) -> dict:
    """Create (or fetch by org id note) a Razorpay customer for the org."""
    client = get_client()
    try:
        return client.customer.create(
            {
                "name": org_name,
                "email": email,
                "notes": {"organization_id": org_id},
            }
        )
    except Exception as e:
        logger.exception("Razorpay customer.create failed")
        raise RazorpayError(f"Failed to create Razorpay customer: {e}") from e


def create_subscription(
    customer_id: str,
    plan_key: str,
    org_id: str,
    org_name: str,
    total_count: int = 12,
) -> dict:
    """Create a monthly Razorpay subscription for a plan key.

    Uses the plan's stable Razorpay Plan ID (test mode), a monthly billing period
    via period+interval, and attaches the org id in notes so the webhook can map
    the subscription back to the org.
    """
    from app.core.billing.plans import get_plan

    plan = get_plan(plan_key)
    if not plan.razorpay_plan_id:
        raise RazorpayError(
            f"Plan '{plan_key}' has no Razorpay plan configured. Create it in the "
            "Razorpay dashboard and set razorpay_plan_id."
        )
    client = get_client()
    try:
        return client.subscription.create(
            {
                "plan_id": plan.razorpay_plan_id,
                "customer_id": customer_id,
                "total_count": total_count,
                "notes": {
                    "organization_id": org_id,
                    "organization_name": org_name,
                    "plan": plan_key,
                },
            }
        )
    except Exception as e:
        logger.exception("Razorpay subscription.create failed")
        raise RazorpayError(f"Failed to create Razorpay subscription: {e}") from e


def fetch_subscription(subscription_id: str) -> dict:
    client = get_client()
    try:
        return client.subscription.fetch(subscription_id)
    except Exception as e:
        logger.exception("Razorpay subscription.fetch failed")
        raise RazorpayError(f"Failed to fetch Razorpay subscription: {e}") from e


def cancel_subscription(subscription_id: str) -> dict:
    client = get_client()
    try:
        return client.subscription.cancel(subscription_id)
    except Exception as e:
        logger.exception("Razorpay subscription.cancel failed")
        raise RazorpayError(f"Failed to cancel Razorpay subscription: {e}") from e


def create_addon(
    subscription_id: str,
    name: str,
    amount_paise: int,
    description: str | None = None,
    notes: dict | None = None,
) -> dict:
    """Charge a one-off add-on against a subscription (next invoice).

    Razorpay has no native usage-metering API, so we report token overage as an
    add-on on the upcoming invoice. ``amount_paise`` must be a positive integer
    amount in the subscription's currency (paise for INR).
    """
    client = get_client()
    item = {
        "name": name,
        "amount": int(amount_paise),
        "currency": "INR",
        "description": description,
    }
    if notes:
        item["notes"] = notes
    try:
        return client.subscription.createAddon(
            subscription_id,
            {
                "item": item,
                "quantity": 1,
            },
        )
    except Exception as e:
        logger.exception("Razorpay subscription.createAddon failed")
        raise RazorpayError(f"Failed to create Razorpay add-on: {e}") from e