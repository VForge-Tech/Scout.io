"""Seed script for the Scout.io load-test suite.

Connects to the SAME Postgres the backend uses (DATABASE_URL from the backend
.env / Vault) and provisions:
  - N organizations, each with one admin user
  - One chatbot per org (behaviour=balanced)
  - M widget sessions per chatbot (each with a pre-minted widget JWT)
  - K knowledge sources per chatbot (plain-text `uri` so the default chunker
    works without network fetch)

Then writes load-tests/seed_state.json, which the Locust files consume.

Run from the backend directory so `app.*` imports resolve:
    cd backend
    MOCK_LLM=true python ../load-tests/seed.py --orgs 20 --sessions 10 --sources 5

Seeding happens through the ORM directly (no HTTP), which is fast and avoids
tripping the per-org rate limiter during setup. No real LLM/embedding calls.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

# Load the backend's .env into os.environ so the SecretManager (which reads
# os.environ, not pydantic's env_file) can resolve DATABASE_URL etc. when the
# backend is run via Vault/env fallback in development.
_env_path = Path(__file__).resolve().parents[1] / "backend" / ".env"
if _env_path.exists():
    for _line in _env_path.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
            continue
        _key, _, _val = _line.partition("=")
        _key = _key.strip()
        _val = _val.strip().strip('"').strip("'")
        os.environ.setdefault(_key, _val)

import sqlalchemy
from sqlalchemy import text

from app.core.config import get_settings
from app.core.security import create_access_token, hash_password
from app.db.session import SessionLocal
from app.models import ChatSession, Chatbot, KnowledgeSource, Message, Organization, User

SAMPLE_DOC = (
    "Scout.io is a support copilot platform. The free plan allows up to 1,000 "
    "messages per month. The starter plan costs $29 per month and allows 10,000 "
    "messages. The growth plan costs $99 per month and allows 100,000 messages. "
    "All plans include the web widget, Slack integration, and REST API access. "
    "Refunds are issued within 7 business days for unused subscription time. "
    "You can invite unlimited teammates on the growth plan and above. "
) * 20  # ~2000 words -> ~4 chunks at 1000-word chunks with 100 overlap


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Seed Scout.io load-test data.")
    p.add_argument("--orgs", type=int, default=20, help="Number of organizations")
    p.add_argument("--sessions", type=int, default=10, help="Widget sessions per chatbot")
    p.add_argument("--sources", type=int, default=5, help="Knowledge sources per chatbot")
    p.add_argument("--output", type=str, default=str(Path(__file__).resolve().parent / "seed_state.json"))
    return p.parse_args()


def main() -> int:
    args = parse_args()
    settings = get_settings()
    if not settings.database_url:
        print("DATABASE_URL is empty; set backend/.env secrets (Vault/env) first.")
        return 2

    db = SessionLocal()
    try:
        # Sanity-check connectivity (RLS is handled by the backend at runtime; the
        # seed session writes without RLS since it is not going through the API).
        try:
            db.execute(text("SELECT 1"))
        except sqlalchemy.exc.OperationalError as exc:
            print(f"Could not reach database: {exc}")
            return 2

        orgs_out = []
        for i in range(args.orgs):
            org = Organization(
                name=f"LoadTest Org {i:03d}",
                configuration={"load_test": True},
                plan="growth",  # 100k msgs/mo => ingestion quota is per-org and generous
                plan_status="active",
            )
            db.add(org)
            db.flush()

            user = User(
                email=f"loadtest-{i:03d}@example.com",
                hashed_password=hash_password("loadtest-pass"),
                full_name=f"Load Test {i:03d}",
                organization_id=org.id,
                role="admin",
                is_active=True,
            )
            db.add(user)
            db.flush()

            bot = Chatbot(
                organization_id=org.id,
                name=f"LoadTest Bot {i:03d}",
                description="Load-test chatbot",
                behaviour="balanced",
            )
            db.add(bot)
            db.flush()

            sessions_out = []
            for j in range(args.sessions):
                sess = ChatSession(
                    organization_id=org.id,
                    chatbot_id=bot.id,
                    customer_id=f"customer-{i}-{j}",
                )
                db.add(sess)
                db.flush()
                token = create_access_token(
                    subject=str(sess.id),
                    organization_id=org.id,
                    extra_claims={
                        "type": "widget",
                        "chatbot_id": str(bot.id),
                    },
                )
                sessions_out.append({"session_id": str(sess.id), "token": token})

            sources_out = []
            for k in range(args.sources):
                src = KnowledgeSource(
                    organization_id=org.id,
                    chatbot_id=bot.id,
                    source_type="text",
                    uri=SAMPLE_DOC,  # inline text -> default chunker, no network
                    config={"_load_test": True},
                    sync_status="pending",
                )
                db.add(src)
                db.flush()
                sources_out.append({"source_id": str(src.id)})

            # A pre-existing thread so session-memory lookups have history to work with
            db.add(
                Message(
                    session_id=sess.id,
                    role="user",
                    content="Seed message from the load-test setup.",
                )
            )
            db.add(
                Message(
                    session_id=sess.id,
                    role="assistant",
                    content="Hello! How can I help you today?",
                )
            )

            orgs_out.append(
                {
                    "org_id": str(org.id),
                    "chatbot_id": str(bot.id),
                    "user_email": user.email,
                    "user_token": create_access_token(
                        subject=str(user.id),
                        organization_id=org.id,
                        extra_claims={"type": "access"},
                    ),
                    "sessions": sessions_out,
                    "knowledge_sources": sources_out,
                }
            )
            print(f"org {i:03d} seeded (sessions={len(sessions_out)}, sources={len(sources_out)})")

        db.commit()

        state = {
            "orgs": orgs_out,
            "config": {
                "orgs": args.orgs,
                "sessions_per_org": args.sessions,
                "sources_per_org": args.sources,
            },
        }
        out = Path(args.output)
        out.write_text(json.dumps(state, indent=2), encoding="utf-8")
        print(f"Wrote seed state to {out}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())