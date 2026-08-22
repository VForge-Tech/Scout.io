"""Seed a demo organization, admin user, chatbot, and knowledge source.

Runnable in the backend container or on the host:

    # in-container (quick-start):
    docker compose -f docker/docker-compose.quickstart.yml --profile quick-start \
        exec -T backend python scripts/seed_demo.py

    # host-side (requires backend/.env with a reachable DATABASE_URL):
    cd backend && python scripts/seed_demo.py

Idempotent: if the demo user already exists, it prints existing credentials and
re-indexes any knowledge source that has not completed sync.
"""

import os
import sys

# Allow running as `python scripts/seed_demo.py` from the backend dir OR as
# `python scripts/seed_test_data.py` / `python backend/scripts/seed_demo.py`
# from the repo root / container.
if os.path.dirname(os.path.dirname(os.path.abspath(__file__))) not in sys.path:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DEMO_EMAIL = "demo@scout.io"
DEMO_PASSWORD = "DemoPass123!"
DEMO_ORG = "Acme Demo"
DEMO_CHATBOT = "Scout Demo Bot"

DEMO_KNOWLEDGE_TEXT = (
    "Scout.io is an AI customer-support assistant platform. Organizations can "
    "create chatbots, connect them to knowledge sources, and embed their help "
    "content so the assistant answers from org-specific context. The platform "
    "supports RLS-based multi-tenancy, role-based access, session memory, and "
    "background sync of knowledge sources via Celery. Quick-start runs with the "
    "pgvector fallback store and deterministic mock embeddings, so it works "
    "fully offline without Qdrant or API keys."
)


def _dialect(db) -> str:
    return db.bind.dialect.name


def _set_admin_context(db) -> None:
    """Bypass RLS for bootstrap rows (Postgres only; SQLite has no RLS)."""
    if _dialect(db) == "postgresql":
        from sqlalchemy import text

        db.execute(text("SET LOCAL app.is_platform_admin = 'true'"))


def seed_demo(db) -> dict:
    """Core seeding logic using provided db session. Returns result dict."""
    from sqlalchemy import func

    from app.core.config import get_settings
    from app.core.security import hash_password
    from app.models import Chatbot, KnowledgeSource, Organization, User
    from app.utils.audit import create_audit_log

    get_settings()
    _set_admin_context(db)

    org = db.query(Organization).filter(Organization.name == DEMO_ORG).first()
    user = db.query(User).filter(User.email == DEMO_EMAIL).first()
    chatbot = (
        db.query(Chatbot)
        .join(Organization)
        .filter(Organization.name == DEMO_ORG, Chatbot.name == DEMO_CHATBOT)
        .first()
    )
    source = None

    if user is not None and org is not None:
        msg = f"Demo user already exists: {DEMO_EMAIL} / {DEMO_PASSWORD}"
        print(msg)
        chatbot = chatbot or db.query(Chatbot).filter(
            Chatbot.organization_id == org.id
        ).first()
    else:
        org = org or Organization(name=DEMO_ORG)
        db.add(org)
        db.flush()

        user = User(
            email=DEMO_EMAIL,
            hashed_password=hash_password(DEMO_PASSWORD),
            full_name="Demo Admin",
            organization_id=org.id,
            role="admin",
        )
        db.add(user)
        db.flush()

        chatbot = Chatbot(
            organization_id=org.id,
            name=DEMO_CHATBOT,
            description="Demo chatbot seeded by quick-start",
            behaviour="balanced",
        )
        db.add(chatbot)
        db.flush()

        create_audit_log(
            db,
            action="seed.demo",
            user_id=user.id,
            organization_id=org.id,
            details={"script": "seed_demo"},
        )

    source = db.query(KnowledgeSource).filter(
        KnowledgeSource.organization_id == org.id
    ).first()

    if source is None and chatbot is not None:
        source = KnowledgeSource(
            organization_id=org.id,
            chatbot_id=chatbot.id,
            source_type="text",
            uri=DEMO_KNOWLEDGE_TEXT,
            sync_status="pending",
        )
        db.add(source)
        db.commit()
        print(f"Created knowledge source {source.id}")

    db.commit()
    print(f"Demo organization: {org.name}")
    print(f"Demo chatbot: {chatbot.name if chatbot else '(none)'}")

    if source is not None and source.sync_status != "completed":
        print("Indexing demo knowledge source (in-process, no broker needed)...")
        from app.tasks.embedding_tasks import process_knowledge_source

        try:
            result = process_knowledge_source.apply(args=[str(source.id)])
            print(f"Ingestion result: {result.get()}")
        except Exception as exc:  # noqa: BLE001
            print(
                f"Warning: knowledge-source indexing failed ({exc}). "
                "You can retry sync later from the dashboard.",
                file=sys.stderr,
            )

    print("Seed complete.")
    return {"status": "seeded", "org": org.name, "chatbot": chatbot.name if chatbot else None}


def main() -> int:
    """CLI entry point - creates its own session."""
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        result = seed_demo(db)
        print(f"Result: {result}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"Seed failed: {exc}", file=sys.stderr)
        db.rollback()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())