import logging
from uuid import UUID

from app.core.config import get_settings
from app.core.knowledge.embeddings import EmbeddingService

settings = get_settings()
logger = logging.getLogger(__name__)


class PGVectorStore:
    def __init__(
        self,
        embedding_service: EmbeddingService | None = None,
    ):
        self.embedding_service = embedding_service or EmbeddingService()
        # Validate embedding dimension is a positive integer
        self._embedding_dimension = int(settings.embedding_dimension)
        if self._embedding_dimension <= 0:
            raise ValueError("embedding_dimension must be a positive integer")

    def _get_engine(self):
        from sqlalchemy import create_engine
        return create_engine(settings.database_url, pool_pre_ping=True)

    def _get_pooled_engine(self):
        """Get or create a pooled engine (singleton pattern)."""
        if not hasattr(PGVectorStore, "_pooled_engine") or PGVectorStore._pooled_engine is None:
            from sqlalchemy import create_engine
            PGVectorStore._pooled_engine = create_engine(
                settings.database_url,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=3600,
            )
        return PGVectorStore._pooled_engine

    def ensure_collection(self):
        try:
            engine = self._get_pooled_engine()
            with engine.connect() as conn:
                from sqlalchemy import text as sa_text
                conn.execute(sa_text("CREATE EXTENSION IF NOT EXISTS vector"))
                conn.execute(
                    sa_text("""
                        CREATE TABLE IF NOT EXISTS knowledge_vectors (
                            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                            source_id TEXT NOT NULL,
                            organization_id TEXT NOT NULL,
                            chatbot_id TEXT DEFAULT '',
                            text TEXT NOT NULL,
                            chunk_index INT DEFAULT 0,
                            embedding vector(:dimension),
                            created_at TIMESTAMPTZ DEFAULT NOW()
                        )
                    """),
                    {"dimension": self._embedding_dimension}
                )
                conn.commit()
        except Exception as exc:
            logger.warning("pgvector not available: %s", exc)

    def index_chunks(self, chunks: list[tuple[str, dict]]):
        self.ensure_collection()
        texts = [c[0] for c in chunks]
        metadatas = [c[1] for c in chunks]
        vectors = self.embedding_service.embed_texts(texts)

        from sqlalchemy import text as sa_text
        engine = self._get_pooled_engine()
        with engine.connect() as conn:
            for i in range(len(texts)):
                conn.execute(
                    sa_text(
                        """
                        INSERT INTO knowledge_vectors
                            (source_id, organization_id, chatbot_id, text, chunk_index, embedding)
                        VALUES (:source_id, :org_id, :chatbot_id, :text, :chunk_idx, :embedding)
                        """
                    ),
                    {
                        "source_id": str(metadatas[i].get("source_id", "")),
                        "org_id": str(metadatas[i].get("organization_id", "")),
                        "chatbot_id": str(metadatas[i].get("chatbot_id", "")),
                        "text": texts[i],
                        "chunk_idx": metadatas[i].get("chunk_index", i),
                        "embedding": vectors[i],
                    },
                )
            conn.commit()

    def search(
        self,
        query: str,
        top_k: int = 5,
        organization_id: str | None = None,
        chatbot_id: str | None = None,
    ) -> list[dict]:
        query_vector = self.embedding_service.embed_query(query)

        from sqlalchemy import text as sa_text
        engine = self._get_pooled_engine()
        with engine.connect() as conn:
            filters = []
            params = {
                "query_vec": query_vector,
                "query_vec2": query_vector,
                "limit": top_k,
            }
            if organization_id:
                params["org_id"] = organization_id
            if chatbot_id:
                params["chatbot_id"] = chatbot_id

            # Build WHERE clause safely using parameterized conditions
            conditions = []
            if organization_id:
                conditions.append("organization_id = :org_id")
            if chatbot_id:
                conditions.append("chatbot_id = :chatbot_id")
            where_clause = " AND ".join(conditions) if conditions else "TRUE"

            sql = sa_text(f"""
                SELECT id, text, source_id, chunk_index,
                       1 - (embedding <=> :query_vec::vector) AS score
                FROM knowledge_vectors
                WHERE {where_clause}
                ORDER BY embedding <=> :query_vec2::vector
                LIMIT :limit
            """)

            rows = conn.execute(sql, params).fetchall()
            return [
                {
                    "id": str(row.id),
                    "score": float(row.score) if row.score else 0.0,
                    "text": row.text,
                    "source_id": row.source_id,
                    "chunk_index": row.chunk_index,
                    "metadata": {},
                }
                for row in rows
            ]

    def delete_source_chunks(self, source_id: str):
        from sqlalchemy import text as sa_text
        engine = self._get_pooled_engine()
        with engine.connect() as conn:
            conn.execute(
                sa_text("DELETE FROM knowledge_vectors WHERE source_id = :sid"),
                {"sid": source_id},
            )
            conn.commit()

    def delete_organization_chunks(self, organization_id: str):
        from sqlalchemy import text as sa_text
        engine = self._get_pooled_engine()
        with engine.connect() as conn:
            conn.execute(
                sa_text("DELETE FROM knowledge_vectors WHERE organization_id = :oid"),
                {"oid": organization_id},
            )
            conn.commit()

    def count_organization_chunks(self, organization_id: str) -> int:
        from sqlalchemy import text as sa_text
        engine = self._get_pooled_engine()
        with engine.connect() as conn:
            return (
                conn.execute(
                    sa_text(
                        "SELECT COUNT(*) FROM knowledge_vectors WHERE organization_id = :oid"
                    ),
                    {"oid": organization_id},
                ).scalar()
                or 0
            )
