from pydantic import BaseModel


class CheckoutSessionRequest(BaseModel):
    plan: str


class CheckoutSessionResponse(BaseModel):
    subscription_id: str
    checkout_url: str | None = None
    plan: str
    status: str


class WebhookResponse(BaseModel):
    status: str
    event: str | None = None