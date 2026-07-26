from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PolicyCreate(BaseModel):
    name: str
    policy_type: str
    rules: dict = {}


class PolicyUpdate(BaseModel):
    name: str | None = None
    rules: dict | None = None


class PolicyRead(BaseModel):
    id: UUID
    organization_id: UUID
    chatbot_id: UUID | None
    name: str
    policy_type: str
    rules: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
