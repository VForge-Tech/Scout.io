from uuid import UUID

from pydantic import BaseModel


class WebhookCreate(BaseModel):
    url: str
    events: str = "sync.completed"


class WebhookRead(BaseModel):
    id: UUID
    organization_id: UUID
    url: str
    events: str
    is_active: bool
    created_at: str

    model_config = {"from_attributes": True}
