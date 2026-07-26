import uuid

from sqlalchemy.orm import Session

from app.models import Organization, Chatbot, ChatSession, Message


def test_message_type_default(db: Session):
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

    msg = Message(
        id=uuid.uuid4(),
        session_id=session.id,
        role="user",
        content="Hello",
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    assert msg.message_type == "text"
    assert msg.attachments == []


def test_message_with_attachments(db: Session):
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

    msg = Message(
        id=uuid.uuid4(),
        session_id=session.id,
        role="user",
        content="Check this image",
        message_type="image",
        attachments=[{"type": "image", "url": "/uploads/img.png"}],
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    assert msg.message_type == "image"
    assert len(msg.attachments) == 1
    assert msg.attachments[0]["type"] == "image"
