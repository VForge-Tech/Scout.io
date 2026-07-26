from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AuditLogRead(BaseModel):
    id: UUID
    user_id: UUID | None
    organization_id: UUID | None
    action: str
    details: dict
    ip_address: str | None
    timestamp: datetime

    model_config = {"from_attributes": True}
