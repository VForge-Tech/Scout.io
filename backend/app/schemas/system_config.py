from uuid import UUID

from pydantic import BaseModel


class SystemConfigRead(BaseModel):
    id: UUID
    key: str
    value: dict
    description: str

    model_config = {"from_attributes": True}


class SystemConfigUpdate(BaseModel):
    value: dict
