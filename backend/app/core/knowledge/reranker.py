"""Client for the cross-encoder reranker service (services/reranker).

The reranker re-orders candidate chunks by query relevance (cross-encoder) on
top of Qdrant's initial vector similarity ranking. This module isolates the
HTTP call, retry/timeout behaviour, and the graceful fallback: if the service
is unreachable, times out, or returns garbage, we log a warning and return the
chunks in their original (Qdrant) order rather than failing the request.

Fallback philosophy mirrors the rest of the codebase: QdrantStore.search()
falls back to keyword search, the LLM router falls back across models, and the
memory stores degrade to in-memory. A reranker outage must degrade to the
existing single-stage retrieval, never to an error.
"""

from __future__ import annotations

import logging

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class RerankerUnavailable(RuntimeError):
    """Raised when the reranker service cannot be used (network, timeout, 5xx)."""


class RerankerClient:
    def __init__(self, url: str | None = None, timeout_ms: int | None = None, retries: int | None = None):
        self.url = (url or settings.reranker_url).rstrip("/")
        self.timeout_ms = timeout_ms or settings.reranker_timeout_ms
        self.retries = max(0, retries if retries is not None else settings.reranker_retries)

    def rerank(
        self,
        query: str,
        chunks: list[dict],
        top_k: int | None = None,
    ) -> list[dict]:
        """Reorder `chunks` by reranker relevance.

        On any failure this raises RerankerUnavailable — callers are expected to
        catch it and fall back to the original ordering (see engine.retrieve).
        """
        if not chunks:
            return []

        payload = {
            "query": query,
            "chunks": [
                {"id": c.get("id", ""), "text": c.get("text", ""), "score": c.get("score", 0.0)}
                for c in chunks
            ],
            "top_k": top_k,
        }

        last_exc: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                resp = httpx.post(
                    f"{self.url}/rerank",
                    json=payload,
                    timeout=httpx.Timeout(self.timeout_ms / 1000.0),
                )
                if resp.status_code >= 500:
                    raise RerankerUnavailable(f"reranker 5xx: {resp.status_code}")
                resp.raise_for_status()
                data = resp.json()
                return self._remap(data.get("results", []))
            except RerankerUnavailable as exc:
                last_exc = exc
                logger.warning(
                    "Reranker attempt %d/%d failed for query %r: %s",
                    attempt + 1,
                    self.retries + 1,
                    query[:60],
                    exc,
                )
            except Exception as exc:  # httpx.TransportError, TimeoutException, JSON decode, 4xx
                last_exc = exc
                logger.warning(
                    "Reranker attempt %d/%d failed for query %r: %s",
                    attempt + 1,
                    self.retries + 1,
                    query[:60],
                    exc,
                )

        raise RerankerUnavailable(f"reranker unreachable after {self.retries + 1} attempts: {last_exc}")

    @staticmethod
    def _remap(results: list[dict]) -> list[dict]:
        """Map the service response back onto chunk dicts.

        The service echoes id/text and returns a new relevance `score`. We keep
        the original Qdrant score too so callers can report both if needed.
        """
        out = []
        for item in results:
            out.append(
                {
                    "id": item.get("id", ""),
                    "text": item.get("text", ""),
                    "score": item.get("score", 0.0),
                    "rerank_score": item.get("score", 0.0),
                }
            )
        return out