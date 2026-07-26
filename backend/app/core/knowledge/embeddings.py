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
        response = litellm_embedding(
            model=self.model,
            input=[text],
            dimensions=self.dimensions,
        )
        return response.data[0]["embedding"]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = litellm_embedding(
            model=self.model,
            input=texts,
            dimensions=self.dimensions,
        )
        return [item["embedding"] for item in response.data]

    def embed_query(self, query: str) -> list[float]:
        return self.embed_text(query)


@lru_cache
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()
