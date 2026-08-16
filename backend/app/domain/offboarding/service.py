"""Org offboarding / permanent data destruction.

Deletes every row scoped to an organization across all org-scoped tables (in
FK-safe child-before-parent order), its Qdrant vectors (and pgvector fallback
rows when enabled), org-scoped Redis caches, and its uploaded source files
under ``UPLOAD_DIR/<org_id>/``.

Retention decision (documented in docs/offboarding.md):

- **Audit logs are purged** with the org's other rows (they are org data and
  the org is permanently leaving the platform), EXCEPT the offboarding
  operation itself, which is written to ``audit_logs`` as a platform-level
  record (``organization_id``/``user_id`` = NULL, ids in ``details``) so it
  survives the purge and serves as immutable proof that deletion happened.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

from jose import JWTError, jwt
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.knowledge.qdrant_store import QdrantStore
from app.core.knowledge.pgvector_store import PGVectorStore
from app.core.memory.knowledge_memory import KnowledgeMemory
from app.core.memory.optimization_memory import OptimizationMemory
from app.core.memory.org_memory import OrganizationalMemory
from app.core.memory.session_memory import SessionMemory
from app.models import Organization
from app.utils.audit import create_audit_log

logger = logging.getLogger(__name__)

OFFBOARD_CONFIRM_TTL_MINUTES = 15

# Deletion order: children before parents so no FK is violated at any point.
# ``messages`` has no organization_id (it joins through sessions) so it is
# deleted via a subquery before sessions themselves are removed.
POSTGRES_TABLES = [
    "messages",           # child of sessions -> matched by session subquery
    "analytics_events",   # child of chatbots, knowledge_sources
    "daily_analytics",    # child of chatbots, knowledge_sources
    "llm_usage",          # child of chatbots
    "knowledge_sources",  # child of chatbots
    "policies",           # child of chatbots
    "sessions",           # child of chatbots
    "chatbots",           # child of organizations
    "api_keys",           # child of users
    "audit_logs",         # child of users (org-scoped rows only)
    "webhooks",           # child of organizations
    "usage_billing_records",  # child of organizations
    "users",              # child of organizations
    "organizations",      # root
]


def _upload_root() -> Path:
    return Path(os.getenv("UPLOAD_DIR", "/tmp/scout_uploads"))


class OffboardingService:
    def __init__(
        self,
        db: Session,
        qdrant_store: QdrantStore | None = None,
        pgvector_store: PGVectorStore | None = None,
    ):
        self.db = db
        settings = get_settings()
        self.qdrant = qdrant_store or QdrantStore()
        self.pgvector = pgvector_store if settings.pgvector_enabled else None

    # -- confirmation token --------------------------------------------------

    def create_confirmation_token(self, org_id: UUID, admin_id: UUID) -> str:
        settings = get_settings()
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(org_id),
            "admin_id": str(admin_id),
            "type": "offboard_confirm",
            "iat": now,
            "exp": now + timedelta(minutes=OFFBOARD_CONFIRM_TTL_MINUTES),
        }
        return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")

    def verify_confirmation_token(self, token: str, org_id: UUID, admin_id: UUID) -> bool:
        settings = get_settings()
        try:
            payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        except JWTError:
            return False
        return (
            payload.get("type") == "offboard_confirm"
            and payload.get("sub") == str(org_id)
            and payload.get("admin_id") == str(admin_id)
        )

    # -- preview ---------------------------------------------------------------

    def preview(self, org: Organization) -> dict:
        """Count what would be deleted without touching anything."""
        settings = get_settings()
        session_ids = self._org_session_ids(org.id)
        redis_counts = self._count_redis(org.id, session_ids)

        qdrant_points = self.qdrant.count_organization_chunks(str(org.id))
        pgvector_points = (
            self.pgvector.count_organization_chunks(str(org.id)) if self.pgvector else None
        )
        uploads = self._count_uploads(org.id)

        return {
            "organization_id": str(org.id),
            "organization_name": org.name,
            "postgres": self._count_postgres(org.id),
            "qdrant": {"points": qdrant_points, "collection": self.qdrant.collection_name},
            "pgvector": {"points": pgvector_points} if pgvector_points is not None else None,
            "redis": redis_counts,
            "uploads": uploads,
            "vector_store": "qdrant" if settings.qdrant_enabled else ("pgvector" if self.pgvector else None),
        }

    # -- execution --------------------------------------------------------------

    def execute(self, org: Organization, admin_id: UUID, ip_address: str | None = None) -> dict:
        """Permanently purge the org across Postgres, vectors, Redis and uploads.

        Returns a completion report of exactly what was deleted. The purge is
        written to ``audit_logs`` as a platform-level record first (org/user id
        kept in ``details``, FK columns NULL) so the proof survives the deletion
        of the org's own rows.
        """
        org_id = org.id
        org_name = org.name
        session_ids = self._org_session_ids(org_id)

        # Detach the org instance now: its row will be deleted below, so any
        # later attribute access would trigger a refresh and fail. Guarded in
        # case the caller passed an instance belonging to a different session.
        try:
            self.db.expunge(org)
        except Exception:
            pass

        # Proof-of-deletion audit record (platform-level; not org-scoped so the
        # org-scoped audit_logs purge below cannot remove it).
        proof = create_audit_log(
            self.db,
            action="org_offboarded",
            user_id=None,
            organization_id=None,
            details={
                "organization_id": str(org_id),
                "organization_name": org_name,
                "initiated_by_user_id": str(admin_id),
                "scope": "postgres+qdrant+redis+uploads",
            },
            ip_address=ip_address,
        )

        postgres = self._purge_postgres(org_id)
        qdrant_points = self.qdrant.count_organization_chunks(str(org_id))
        self.qdrant.delete_organization_chunks(str(org_id))
        pgvector_deleted = None
        if self.pgvector:
            pgvector_deleted = self.pgvector.count_organization_chunks(str(org_id))
            self.pgvector.delete_organization_chunks(str(org_id))
        redis_counts = self._purge_redis(org_id, session_ids)
        uploads = self._purge_uploads(org_id)

        report = {
            "organization_id": str(org_id),
            "organization_name": org_name,
            "status": "offboarded",
            "deleted": {
                "postgres": postgres,
                "qdrant": {"points_deleted": qdrant_points,
                           "collection": self.qdrant.collection_name},
                "pgvector": {"points_deleted": pgvector_deleted} if pgvector_deleted is not None else None,
                "redis": redis_counts,
                "uploads": uploads,
            },
            "audit_log_id": str(proof.id),
            "retained": {
                "audit_logs": "platform-level purge proof (audit_log_id above) kept; "
                              "org-scoped audit logs purged",
            },
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
        return report

    # -- postgres ---------------------------------------------------------------

    def _org_session_ids(self, org_id: UUID) -> list[str]:
        rows = self.db.execute(
            text("SELECT id FROM sessions WHERE organization_id = :oid"),
            {"oid": self._stored_org_id(org_id)},
        ).fetchall()
        return [str(r[0]) for r in rows]

    def _count_postgres(self, org_id: UUID) -> dict:
        counts = {}
        for table in POSTGRES_TABLES:
            counts[table] = self.db.execute(
                text(f"SELECT COUNT(*) FROM {table} WHERE {self._org_condition(table)}"),
                self._params(org_id),
            ).scalar()
        return counts

    def _purge_postgres(self, org_id: UUID) -> dict:
        deleted = {}
        for table in POSTGRES_TABLES:
            result = self.db.execute(self._delete_sql(table), self._params(org_id))
            deleted[table] = result.rowcount
        self.db.commit()
        return deleted

    @staticmethod
    def _org_condition(table: str) -> str:
        if table == "messages":
            return "session_id IN (SELECT id FROM sessions WHERE organization_id = :oid)"
        if table == "organizations":
            return "id = :oid"
        return "organization_id = :oid"

    @staticmethod
    def _delete_sql(table: str) -> text:
        if table == "messages":
            return text(
                "DELETE FROM messages WHERE session_id IN "
                "(SELECT id FROM sessions WHERE organization_id = :oid)"
            )
        if table == "organizations":
            return text("DELETE FROM organizations WHERE id = :oid")
        return text(f"DELETE FROM {table} WHERE organization_id = :oid")

    def _stored_org_id(self, org_id: UUID) -> str:
        """Format the org id for raw SQL: dashed on Postgres (uuid type casts
        fine), hex on SQLite where the UUID column is stored as CHAR(32)."""
        dialect = self.db.get_bind().dialect.name
        return org_id.hex if dialect == "sqlite" else str(org_id)

    def _params(self, org_id: UUID) -> dict:
        return {"oid": self._stored_org_id(org_id)}

    # -- redis ------------------------------------------------------------------

    def _count_redis(self, org_id: UUID, session_ids: list[str]) -> dict:
        return {
            "session_history": len(session_ids),
            "org_config_policies": 2,
            "knowledge_cache": self._count_knowledge_cache(str(org_id)),
            "opt_cache": self._count_opt_cache(),
        }

    def _purge_redis(self, org_id: UUID, session_ids: list[str]) -> dict:
        counts = {}
        counts["session_history"] = SessionMemory().purge_org(session_ids)
        counts["org_config_policies"] = OrganizationalMemory().purge_org(str(org_id))
        counts["knowledge_cache"] = KnowledgeMemory().purge_org(str(org_id))
        opt = OptimizationMemory()
        opt_before = self._count_opt_cache()
        opt.invalidate_org_cache(str(org_id))
        opt_after = self._count_opt_cache()
        counts["opt_cache"] = max(opt_before - opt_after, 0)
        return counts

    def _count_knowledge_cache(self, org_id: str) -> int:
        # Best-effort: count cache keys referencing the org by inspecting payloads.
        mem = KnowledgeMemory()
        if not mem.client:
            return 0
        count = 0
        cursor = 0
        while True:
            cursor, keys = mem.client.scan(cursor=cursor, match="knowledge_cache:*", count=200)
            for key in keys:
                raw = mem.client.get(key)
                if raw:
                    try:
                        chunks = json.loads(raw)
                    except (json.JSONDecodeError, TypeError):
                        chunks = []
                    if any(
                        str(c.get("metadata", {}).get("organization_id", "")).lower()
                        == org_id.lower()
                        for c in chunks
                    ):
                        count += 1
            if cursor == 0:
                break
        return count

    def _count_opt_cache(self) -> int:
        mem = OptimizationMemory()
        if not mem.client:
            return 0
        count = 0
        cursor = 0
        while True:
            cursor, keys = mem.client.scan(cursor=cursor, match="opt_cache:*", count=200)
            count += len(keys)
            if cursor == 0:
                break
        return count

    # -- uploads ----------------------------------------------------------------

    def _count_uploads(self, org_id: UUID) -> dict:
        root = _upload_root() / str(org_id)
        if not root.exists():
            return {"files": 0, "bytes": 0}
        files = [p for p in root.rglob("*") if p.is_file()]
        return {"files": len(files), "bytes": sum(p.stat().st_size for p in files)}

    def _purge_uploads(self, org_id: UUID) -> dict:
        root = _upload_root() / str(org_id)
        if not root.exists():
            return {"files": 0, "bytes": 0}
        files = [p for p in root.rglob("*") if p.is_file()]
        total_bytes = sum(p.stat().st_size for p in files)
        shutil.rmtree(root, ignore_errors=True)
        return {"files": len(files), "bytes": total_bytes}