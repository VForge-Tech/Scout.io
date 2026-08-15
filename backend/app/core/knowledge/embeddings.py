from functools import lru_cache

import litellm
from litellm import embedding as litellm_embedding

from app.core.config import get_settings

settings = get_settings()


class EmbeddingService:
    def __init__(self, model: str | None = None, dimensions: int | None = None):
        self.model = model or settings.embedding_model
        self.dimensions = dimensions or settings.embedding_dimension

    def embed_text(self, text: str) -> list[float]:
        if settings.mock_llm:
            return self._mock_embed(text)
        response = litellm_embedding(
            model=self.model,
            input=[text],
            dimensions=self.dimensions,
        )
        return response.data[0]["embedding"]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if settings.mock_llm:
            return [self._mock_embed(t) for t in texts]
        response = litellm_embedding(
            model=self.model,
            input=texts,
            dimensions=self.dimensions,
        )
        return [item["embedding"] for item in response.data]

    def embed_query(self, query: str) -> list[float]:
        return self.embed_text(query)

    def _mock_embed(self, text: str) -> list[float]:
        """Deterministic pseudo-embedding for MOCK_LLM load-test mode.

        A hash-derived unit vector of the configured dimension. Qdrant cosine
        search still ranks (deterministically) without a real provider call.
        """
        import hashlib

        digest = hashlib.sha256(text.encode("utf-8")).digest()
        seed = int.from_bytes(digest[:8], "big")
        values = [((seed >> i) & 0xFFFF) / 65535.0 * 2.0 - 1.0 for i in range(self.dimensions)]
        norm = sum(v * v for v in values) ** 0.5 or 1.0
        return [v / norm for v in values]


@lru_cache
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()
