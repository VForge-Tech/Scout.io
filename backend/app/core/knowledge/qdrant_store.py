from uuid import UUID

from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
from qdrant_client.http.exceptions import UnexpectedResponse

from app.core.config import get_settings
from app.core.knowledge.embeddings import EmbeddingService

settings = get_settings()


class QdrantStore:
    def __init__(
        self,
        collection_name: str | None = None,
        embedding_service: EmbeddingService | None = None,
    ):
        if not settings.qdrant_enabled:
            self.client = None
            self.collection_name = collection_name or settings.qdrant_collection
            self.embedding_service = embedding_service or EmbeddingService()
            return
        
        self.client = QdrantClient(url=settings.qdrant_url)
        self.collection_name = collection_name or settings.qdrant_collection
        self.embedding_service = embedding_service or EmbeddingService()

    def ensure_collection(self):
        if not self.client:
            return
        try:
            self.client.get_collection(self.collection_name)
        except (UnexpectedResponse, ValueError):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=qdrant_models.VectorParams(
                    size=self.embedding_service.dimensions,
                    distance=qdrant_models.Distance.COSINE,
                ),
            )

    def index_chunks(
        self,
        chunks: list[tuple[str, dict]],
    ):
        if not self.client:
            return
        self.ensure_collection()
        texts = [c[0] for c in chunks]
        metadatas = [c[1] for c in chunks]
        vectors = self.embedding_service.embed_texts(texts)

        points = [
            qdrant_models.PointStruct(
                id=metadatas[i].get("chunk_id", i),
                vector=vectors[i],
                payload={
                    "text": texts[i],
                    "source_id": str(metadatas[i].get("source_id", "")),
                    "organization_id": str(metadatas[i].get("organization_id", "")),
                    "chatbot_id": str(metadatas[i].get("chatbot_id", "")),
                    "chunk_index": metadatas[i].get("chunk_index", i),
                    **{k: str(v) if isinstance(v, UUID) else v for k, v in metadatas[i].items() if k not in ("chunk_id",)},
                },
            )
            for i in range(len(texts))
        ]

        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
        )

    def search(
        self,
        query: str,
        top_k: int = 5,
        organization_id: str | None = None,
        chatbot_id: str | None = None,
        score_threshold: float | None = None,
    ) -> list[dict]:
        if not self.client:
            return []
        
        query_vector = self.embedding_service.embed_query(query)

        must_filters = []
        if organization_id:
            must_filters.append(
                qdrant_models.FieldCondition(
                    key="organization_id",
                    match=qdrant_models.MatchValue(value=organization_id),
                )
            )
        if chatbot_id:
            must_filters.append(
                qdrant_models.FieldCondition(
                    key="chatbot_id",
                    match=qdrant_models.MatchValue(value=chatbot_id),
                )
            )

        filter_query = qdrant_models.Filter(must=must_filters) if must_filters else None

        try:
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=top_k,
                query_filter=filter_query,
                score_threshold=score_threshold,
            )
        except Exception:
            return self._keyword_search(query, top_k, organization_id, chatbot_id)

        return [
            {
                "id": str(hit.id),
                "score": hit.score,
                "text": hit.payload.get("text", ""),
                "source_id": hit.payload.get("source_id", ""),
                "chunk_index": hit.payload.get("chunk_index", 0),
                "metadata": {k: v for k, v in hit.payload.items() if k != "text"},
            }
            for hit in search_result
        ]

    def _keyword_search(
        self,
        query: str,
        top_k: int = 5,
        organization_id: str | None = None,
        chatbot_id: str | None = None,
    ) -> list[dict]:
        if not self.client:
            return []
            
        keywords = query.lower().split()
        try:
            scroll_result = self.client.scroll(
                collection_name=self.collection_name,
                limit=100,
            )
        except Exception:
            return []

        points = scroll_result[0]
        scored = []

        for point in points:
            text = (point.payload.get("text", "") or "").lower()
            if organization_id and point.payload.get("organization_id") != organization_id:
                continue
            if chatbot_id and point.payload.get("chatbot_id") != chatbot_id:
                continue

            score = sum(1 for kw in keywords if kw in text) / max(len(keywords), 1)
            if score > 0:
                scored.append((score, point))

        scored.sort(key=lambda x: -x[0])
        scored = scored[:top_k]

        return [
            {
                "id": str(point.id),
                "score": score,
                "text": point.payload.get("text", ""),
                "source_id": point.payload.get("source_id", ""),
                "chunk_index": point.payload.get("chunk_index", 0),
                "metadata": {k: v for k, v in point.payload.items() if k != "text"},
            }
            for score, point in scored
        ]

    def delete_source_chunks(self, source_id: str):
        if not self.client:
            return
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=qdrant_models.FilterSelector(
                filter=qdrant_models.Filter(
                    must=[
                        qdrant_models.FieldCondition(
                            key="source_id",
                            match=qdrant_models.MatchValue(value=source_id),
                        )
                    ]
                )
            ),
        )

    def delete_organization_chunks(self, organization_id: str):
        if not self.client:
            return
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=qdrant_models.FilterSelector(
                filter=qdrant_models.Filter(
                    must=[
                        qdrant_models.FieldCondition(
                            key="organization_id",
                            match=qdrant_models.MatchValue(value=organization_id),
                        )
                    ]
                )
            ),
        )

    def count_organization_chunks(self, organization_id: str) -> int:
        if not self.client:
            return 0
        result = self.client.count(
            collection_name=self.collection_name,
            count_filter=qdrant_models.Filter(
                must=[
                    qdrant_models.FieldCondition(
                        key="organization_id",
                        match=qdrant_models.MatchValue(value=organization_id),
                    )
                ]
            ),
        )
        return result.count
