from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class AnalyticsEventCreate(BaseModel):
    event_type: str
    entity_id: str | None = None
    chatbot_id: str | None = None
    source_id: str | None = None
    payload: dict = {}


class OnboardingStepInfo(BaseModel):
    step: str
    label: str
    completed: bool


class OnboardingChecklistResponse(BaseModel):
    steps: list[OnboardingStepInfo]
    completed_count: int


class FeedbackCreate(BaseModel):
    rating: Literal["up", "down"]
    message: str | None = None
    context: str | None = None
    chatbot_id: str | None = None
    source_id: str | None = None


class FunnelOrgRow(BaseModel):
    organization_id: UUID
    name: str
    created_at: datetime | None = None
    steps_completed: list[str] = []
    has_chatbot: bool
    has_knowledge_source: bool
    has_widget_session: bool
    has_teammate: bool


class FeedbackItem(BaseModel):
    id: UUID
    organization_id: UUID
    org_name: str | None = None
    chatbot_id: UUID | None = None
    source_id: UUID | None = None
    rating: str | None = None
    message: str | None = None
    context: str | None = None
    timestamp: datetime | None = None


class OnboardingFunnelResponse(BaseModel):
    summary: dict
    funnel: list[FunnelOrgRow]
    feedback: list[FeedbackItem]


class DailyAnalyticsRead(BaseModel):
    id: UUID
    date: date
    organization_id: UUID
    chatbot_id: UUID | None
    source_id: UUID | None
    entity_type: str
    sessions_count: int
    messages_count: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    avg_latency_ms: float
    feedback_positive: int
    feedback_negative: int
    retrieval_count: int
    sync_success_count: int
    sync_failure_count: int

    model_config = {"from_attributes": True}


class ChatbotAnalyticsResponse(BaseModel):
    chatbot_id: UUID
    total_sessions: int
    total_messages: int
    total_tokens: int
    avg_latency_ms: float
    feedback_positive: int
    feedback_negative: int


class OrgAnalyticsResponse(BaseModel):
    organization_id: UUID
    total_sessions: int
    total_messages: int
    total_tokens: int
    total_chatbots: int
    active_chatbots: int


class SourceAnalyticsResponse(BaseModel):
    source_id: UUID
    retrieval_count: int
    sync_success_count: int
    sync_failure_count: int


class PlatformAnalyticsResponse(BaseModel):
    total_organizations: int
    total_chatbots: int
    total_sessions: int
    total_messages: int
    total_tokens: int
    total_api_calls: int
