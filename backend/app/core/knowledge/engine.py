from uuid import UUID

from app.core.config import get_settings
from app.core.knowledge.embeddings import EmbeddingService
from app.core.knowledge.pgvector_store import PGVectorStore
from app.core.knowledge.qdrant_store import QdrantStore
from app.core.knowledge.reranker import RerankerClient
from app.core.metrics import RERANKER_FALLBACKS
from app.models import Policy

settings = get_settings()


class KnowledgeEngine:
    """Retrieval engine that routes to the active vector store.

    Store selection (highest priority first):
      1. Qdrant when ``settings.qdrant_enabled`` is true (default).
      2. pgvector when ``settings.qdrant_enabled`` is false and
         ``settings.pgvector_enabled`` is true (quick-start / Qdrant-less runs).
      3. Otherwise a no-op QdrantStore so retrieval degrades to empty results
         instead of raising.
    """

    def __init__(
        self,
        qdrant_store: QdrantStore | None = None,
        embedding_service: EmbeddingService | None = None,
        reranker_client: RerankerClient | None = None,
    ):
        embedding_service = embedding_service or EmbeddingService()
        self.embedding_service = embedding_service
        if qdrant_store is not None:
            self.store = qdrant_store
        elif settings.qdrant_enabled:
            self.store = QdrantStore(embedding_service=embedding_service)
        elif settings.pgvector_enabled:
            self.store = PGVectorStore(embedding_service=embedding_service)
        else:
            self.store = QdrantStore(embedding_service=embedding_service)
        self.reranker = reranker_client or RerankerClient()

    def index_chunks(
        self,
        chunks: list[tuple[str, dict]],
    ):
        self.store.index_chunks(chunks)

    def retrieve(
        self,
        query: str,
        organization_id: str | UUID,
        chatbot_id: str | UUID | None = None,
        policies: list[Policy] | None = None,
        top_k: int | None = None,
        reranker_enabled: bool | None = None,
    ) -> list[dict]:
        org_id_str = str(organization_id)
        chatbot_id_str = str(chatbot_id) if chatbot_id else None

        results = self.store.search(
            query=query,
            top_k=top_k or settings.top_k_retrieval,
            organization_id=org_id_str,
            chatbot_id=chatbot_id_str,
        )

        if policies:
            results = self._filter_by_policies(results, policies)

        results = self._rerank(
            query=query,
            results=results,
            enabled=reranker_enabled,
            top_k=top_k or settings.top_k_retrieval,
        )

        return results

    def _rerank(
        self,
        query: str,
        results: list[dict],
        enabled: bool | None,
        top_k: int,
    ) -> list[dict]:
        """Re-rank Qdrant results with the cross-encoder reranker.

        Controlled by ``settings.reranker_enabled`` (global) unless overridden
        per-call via ``enabled`` (e.g. from a chatbot's config JSON). Falls back
        to Qdrant's original similarity order on any reranker failure — a
        reranker outage must degrade to single-stage retrieval, never an error.
        """
        use = settings.reranker_enabled if enabled is None else enabled
        if not use or not results:
            return results

        # Fetch a few extra candidates from the reranker so re-ordering has room
        # to improve precision beyond the Qdrant top-K that will actually be used.
        max_candidates = max(top_k, settings.reranker_max_candidates)
        try:
            reranked = self.reranker.rerank(
                query=query,
                chunks=results[:max_candidates],
                top_k=top_k,
            )
        except Exception as exc:
            # Degrade gracefully: keep Qdrant's original ordering.
            logger = __import__("logging").getLogger(__name__)
            logger.warning("Reranker unavailable for query %r, using Qdrant order: %s", query[:60], exc)
            RERANKER_FALLBACKS.inc()
            return results

        if not reranked:
            return results

        # Preserve any metadata not echoed by the reranker service by re-merging
        # against the original results on id.
        by_id = {r.get("id"): r for r in results}
        merged = []
        for item in reranked:
            original = by_id.get(item["id"], {})
            merged.append({**original, "score": item.get("rerank_score", original.get("score", 0.0))})
        return merged

    def _filter_by_policies(
        self,
        results: list[dict],
        policies: list[Policy],
    ) -> list[dict]:
        for policy in policies:
            if policy.policy_type == "source_filter" and policy.rules:
                allowed_sources = policy.rules.get("allowed_source_ids", [])
                if allowed_sources:
                    results = [
                        r
                        for r in results
                        if r["source_id"] in allowed_sources
                    ]
            if policy.policy_type == "content_filter" and policy.rules:
                blocked_terms = policy.rules.get("blocked_terms", [])
                if blocked_terms:
                    results = [
                        r
                        for r in results
                        if not any(
                            term.lower() in r["text"].lower()
                            for term in blocked_terms
                        )
                    ]
        return results

    def retrieve_formatted_context(
        self,
        query: str,
        organization_id: str | UUID,
        chatbot_id: str | UUID | None = None,
        policies: list[Policy] | None = None,
        top_k: int | None = None,
    ) -> str:
        results = self.retrieve(
            query=query,
            organization_id=organization_id,
            chatbot_id=chatbot_id,
            policies=policies,
            top_k=top_k,
        )
        if not results:
            return ""

        formatted = []
        for i, r in enumerate(results):
            formatted.append(
                f"[Source {i+1}] (relevance: {r['score']:.3f})\n{r['text']}"
            )
        return "\n\n".join(formatted)

    def delete_source_data(self, source_id: str):
        self.store.delete_source_chunks(source_id)

    def delete_organization_data(self, organization_id: str):
        self.store.delete_organization_chunks(organization_id)
