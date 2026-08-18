from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ChatbotCreate(BaseModel):
    name: str
    description: str = ""
    behaviour: str = "balanced"
    config: dict = {}


class ChatbotUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    behaviour: str | None = None
    config: dict | None = None


class ChatbotRead(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    description: str
    behaviour: str
    config: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatMessageRequest(BaseModel):
    content: str
