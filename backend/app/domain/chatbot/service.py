from uuid import UUID

from sqlalchemy.orm import Session

from app.domain import event_bus
from app.domain.event_bus import DomainEvent
from app.models import Chatbot, Message


class ChatbotDomainService:
    def __init__(self, db: Session):
        self.db = db

    def record_message(self, chatbot_id: UUID, session_id: UUID, role: str, content: str) -> Message:
        msg = Message(
            session_id=session_id,
            role=role,
            content=content,
        )
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)

        event_bus.publish_sync(
            DomainEvent(
                event_type="message.created",
                payload={
                    "message_id": str(msg.id),
                    "session_id": str(session_id),
                    "role": role,
                    "chatbot_id": str(chatbot_id),
                },
            )
        )
        return msg
