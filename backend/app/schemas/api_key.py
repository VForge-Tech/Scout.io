from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ApiKeyCreate(BaseModel):
    name: str
    expires_in_days: int = 365


class ApiKeyRead(BaseModel):
    id: UUID
    name: str
    key_prefix: str
    is_active: bool
    last_used_at: datetime | None
    expires_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyCreated(BaseModel):
    id: UUID
    name: str
    key_prefix: str
    full_key: str
    expires_at: datetime
    created_at: datetime
