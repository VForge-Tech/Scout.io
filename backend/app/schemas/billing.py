from datetime import datetime
from typing import Any

from pydantic import BaseModel


class CheckoutSessionRequest(BaseModel):
    plan: str


class CheckoutSessionResponse(BaseModel):
    subscription_id: str
    checkout_url: str | None = None
    plan: str
    status: str


class InvoiceRead(BaseModel):
    id: str
    status: str | None = None
    amount_paise: int | None = None
    currency: str | None = None
    issued_at: datetime | None = None
    paid_at: datetime | None = None


class SubscriptionDetail(BaseModel):
    has_subscription: bool
    subscription_id: str | None = None
    plan_id: str | None = None
    plan_key: str | None = None
    status: str | None = None
    current_start: datetime | None = None
    current_end: datetime | None = None
    next_charge_on: datetime | None = None
    payment_method: str | None = None
    cancel_at_cycle_end: bool | None = None
    invoices: list[InvoiceRead] = []


class ChangePlanRequest(BaseModel):
    plan: str
    schedule_change_at: str = "now"  # "now" | "cycle_end"


class ChangePlanResponse(BaseModel):
    subscription_id: str
    plan: str
    schedule_change_at: str
    status: str | None = None
    next_charge_on: datetime | None = None


class CancelSubscriptionRequest(BaseModel):
    cancel_at_cycle_end: bool = True


class CancelSubscriptionResponse(BaseModel):
    subscription_id: str
    status: str | None = None
    cancel_at_cycle_end: bool
    current_end: datetime | None = None


class WebhookResponse(BaseModel):
    status: str
    event: str | None = None