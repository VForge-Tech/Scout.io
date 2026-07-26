from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr


class UserRead(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: str
    organization_id: UUID
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
