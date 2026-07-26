from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class OrganizationRead(BaseModel):
    id: UUID
    name: str
    configuration: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrganizationUpdate(BaseModel):
    name: str | None = None
    configuration: dict | None = None
