from pydantic import BaseModel


class WidgetSessionCreate(BaseModel):
    chatbot_id: str
    customer_id: str | None = None
    metadata: dict = {}


class WidgetSessionResponse(BaseModel):
    session_id: str
    token: str


class WidgetMessageRequest(BaseModel):
    session_id: str
    content: str
    metadata: dict = {}


class WidgetMessageResponse(BaseModel):
    reply: str
    session_id: str
