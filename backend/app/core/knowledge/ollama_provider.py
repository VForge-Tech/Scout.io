import logging

import httpx

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class OllamaProvider:
    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        try:
            resp = httpx.post(
                f"{self.base_url}/api/embed",
                json={"model": settings.ollama_embedding_model, "input": texts},
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("embeddings", [])
        except Exception as exc:
            logger.error("Ollama embedding failed: %s", exc)
            return [[0.0] * settings.embedding_dimension for _ in texts]

    def embed_query(self, query: str) -> list[float]:
        return self.embed_texts([query])[0]

    def chat(self, messages: list[dict], model: str | None = None) -> str:
        try:
            resp = httpx.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": model or settings.ollama_chat_model,
                    "messages": messages,
                    "stream": False,
                },
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "")
        except Exception as exc:
            logger.error("Ollama chat failed: %s", exc)
            return ""
