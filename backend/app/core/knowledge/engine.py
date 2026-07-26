from uuid import UUID

from app.core.config import get_settings
from app.core.knowledge.embeddings import EmbeddingService
from app.core.knowledge.qdrant_store import QdrantStore
from app.models import Policy

settings = get_settings()


class KnowledgeEngine:
    def __init__(
        self,
        qdrant_store: QdrantStore | None = None,
        embedding_service: EmbeddingService | None = None,
    ):
        self.qdrant = qdrant_store or QdrantStore(
            embedding_service=embedding_service or EmbeddingService()
        )
        self.embedding_service = embedding_service or EmbeddingService()

    def index_chunks(
        self,
        chunks: list[tuple[str, dict]],
    ):
        self.qdrant.index_chunks(chunks)

    def retrieve(
        self,
        query: str,
        organization_id: str | UUID,
        chatbot_id: str | UUID | None = None,
        policies: list[Policy] | None = None,
        top_k: int | None = None,
    ) -> list[dict]:
        org_id_str = str(organization_id)
        chatbot_id_str = str(chatbot_id) if chatbot_id else None

        results = self.qdrant.search(
            query=query,
            top_k=top_k or settings.top_k_retrieval,
            organization_id=org_id_str,
            chatbot_id=chatbot_id_str,
        )

        if policies:
            results = self._filter_by_policies(results, policies)

        return results

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
        self.qdrant.delete_source_chunks(source_id)

    def delete_organization_data(self, organization_id: str):
        self.qdrant.delete_organization_chunks(organization_id)
