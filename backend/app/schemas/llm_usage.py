from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class LLMUsageRead(BaseModel):
    id: UUID
    organization_id: UUID
    chatbot_id: UUID | None
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: int
    timestamp: datetime

    model_config = {"from_attributes": True}
