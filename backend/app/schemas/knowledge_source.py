from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class KnowledgeSourceCreate(BaseModel):
    source_type: str
    uri: str
    config: dict = {}


class KnowledgeSourceUpdate(BaseModel):
    config: dict | None = None
    uri: str | None = None


class KnowledgeSourceRead(BaseModel):
    id: UUID
    organization_id: UUID
    chatbot_id: UUID | None
    source_type: str
    uri: str
    config: dict
    sync_status: str
    last_sync_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
