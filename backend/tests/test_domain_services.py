import uuid

import pytest
from sqlalchemy.orm import Session

from app.db.base import Base
from app.domain.chatbot.service import ChatbotDomainService
from app.domain.knowledge.service import KnowledgeDomainService
from app.domain.analytics.service import AnalyticsDomainService
from app.domain.event_bus import DomainEvent
from app.domain import event_bus
from app.models import Message, Organization, Chatbot, ChatSession


@pytest.fixture(autouse=True)
def reset_event_bus():
    event_bus.clear()
    yield
    event_bus.clear()


def test_chatbot_domain_service_records_message(db: Session):
    org = Organization(id=uuid.uuid4(), name="Org")
    db.add(org)
    db.commit()

    chatbot = Chatbot(id=uuid.uuid4(), organization_id=org.id, name="Bot")
    db.add(chatbot)
    db.commit()

    session = ChatSession(
        id=uuid.uuid4(), organization_id=org.id, chatbot_id=chatbot.id, customer_id="c1"
    )
    db.add(session)
    db.commit()

    events = []

    def handler(e: DomainEvent):
        events.append(e)

    event_bus.subscribe("message.created", handler)

    svc = ChatbotDomainService(db)
    msg = svc.record_message(chatbot.id, session.id, "user", "Hello")

    assert msg.id is not None
    assert msg.content == "Hello"
    assert msg.role == "user"
    assert len(events) == 1
    assert events[0].payload["role"] == "user"


def test_knowledge_domain_service_publishes_events():
    events = []

    def handler(e: DomainEvent):
        events.append(e)

    event_bus.subscribe("knowledge_source.created", handler)
    event_bus.subscribe("knowledge_source.synced", handler)

    svc = KnowledgeDomainService()
    svc.on_source_created(str(uuid.uuid4()))
    svc.on_source_synced(str(uuid.uuid4()), 10)

    assert len(events) == 2


def test_analytics_domain_service_publishes_event():
    events = []

    def handler(e: DomainEvent):
        events.append(e)

    event_bus.subscribe("analytics.updated", handler)

    svc = AnalyticsDomainService()
    svc.record_event(str(uuid.uuid4()), "page_view", {"page": "/home"})

    assert len(events) == 1
    assert events[0].payload["event_type"] == "page_view"
