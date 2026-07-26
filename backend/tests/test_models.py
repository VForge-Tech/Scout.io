import uuid

import pytest
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import ChatSession, Chatbot, KnowledgeSource, Organization, Policy, User


def test_create_organization(db: Session):
    org = Organization(id=uuid.uuid4(), name="Test Org", configuration={"key": "val"})
    db.add(org)
    db.commit()
    db.refresh(org)
    assert org.id is not None
    assert org.name == "Test Org"
    assert org.configuration == {"key": "val"}
    assert org.created_at is not None


def test_create_user(db: Session):
    org = Organization(id=uuid.uuid4(), name="Org")
    db.add(org)
    db.commit()

    user = User(
        id=uuid.uuid4(),
        email="user@test.com",
        hashed_password=hash_password("secret"),
        organization_id=org.id,
        role="member",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    assert user.email == "user@test.com"
    assert user.organization_id == org.id


def test_create_chatbot(db: Session):
    org = Organization(id=uuid.uuid4(), name="Org")
    db.add(org)
    db.commit()

    chatbot = Chatbot(
        id=uuid.uuid4(),
        organization_id=org.id,
        name="Test Bot",
        behaviour="balanced",
    )
    db.add(chatbot)
    db.commit()
    db.refresh(chatbot)
    assert chatbot.name == "Test Bot"
    assert chatbot.organization_id == org.id


def test_create_policy(db: Session):
    org = Organization(id=uuid.uuid4(), name="Org")
    db.add(org)
    db.commit()

    policy = Policy(
        id=uuid.uuid4(),
        organization_id=org.id,
        name="Test Policy",
        policy_type="security",
        rules={"allow": ["*"]},
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    assert policy.name == "Test Policy"
    assert policy.policy_type == "security"


def test_create_knowledge_source(db: Session):
    org = Organization(id=uuid.uuid4(), name="Org")
    db.add(org)
    db.commit()

    ks = KnowledgeSource(
        id=uuid.uuid4(),
        organization_id=org.id,
        source_type="website",
        uri="https://example.com",
    )
    db.add(ks)
    db.commit()
    db.refresh(ks)
    assert ks.source_type == "website"
    assert ks.sync_status == "pending"


def test_create_session(db: Session):
    org = Organization(id=uuid.uuid4(), name="Org")
    db.add(org)
    db.commit()

    chatbot = Chatbot(
        id=uuid.uuid4(), organization_id=org.id, name="Bot"
    )
    db.add(chatbot)
    db.commit()

    session = ChatSession(
        id=uuid.uuid4(),
        organization_id=org.id,
        chatbot_id=chatbot.id,
        customer_id="cust_123",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    assert session.customer_id == "cust_123"
    assert session.started_at is not None
    assert session.ended_at is None


def test_organization_cascade_delete(db: Session):
    org = Organization(id=uuid.uuid4(), name="Org")
    db.add(org)
    db.commit()

    user = User(
        id=uuid.uuid4(),
        email="user@test.com",
        hashed_password="hash",
        organization_id=org.id,
    )
    db.add(user)
    db.commit()

    db.delete(org)
    db.commit()

    users = db.query(User).all()
    assert len(users) == 0
