"""Cross-encoder reranking service for Scout.io.

Loads a small cross-encoder (ms-marco-MiniLM-L-6-v2) into GPU/CPU memory at
startup and exposes POST /rerank, which reorders candidate chunks by
query-chunk relevance. Used by the backend's knowledge retrieval step to
improve precision on top of Qdrant's initial vector similarity ranking.

Deliberately tiny surface area: the backend only needs this one endpoint plus
/health and /ready for orchestration.
"""

from __future__ import annotations

import os
import time

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from sentence_transformers import CrossEncoder

app = FastAPI(title="Scout Reranker", version="1.0.0")

MODEL_NAME = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
DEVICE = os.getenv("RERANKER_DEVICE", "cpu")

# Lazy, memoized so the model is loaded once per process (workers share nothing
# on CPU; each worker loads its own copy).
_encoder: CrossEncoder | None = None


def get_encoder() -> CrossEncoder:
    global _encoder
    if _encoder is None:
        _encoder = CrossEncoder(MODEL_NAME, device=DEVICE)
    return _encoder


class Chunk(BaseModel):
    id: str = Field(..., description="Chunk identifier (echoed back untouched)")
    text: str = Field(..., description="Chunk text to score against the query")
    score: float = Field(0.0, description="Original similarity score (echoed back)")


class RerankRequest(BaseModel):
    query: str = Field(..., min_length=1)
    chunks: list[Chunk] = Field(..., min_length=1)
    top_k: int | None = Field(None, ge=1, description="Number of results to return (default: all)")


class RerankResult(BaseModel):
    results: list[Chunk]
    elapsed_ms: float


@app.on_event("startup")
def _warm_model() -> None:
    """Load the model at startup so the first request isn't slow (and so k8s
    readiness checks pass only when the model is actually in memory)."""
    get_encoder()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model": MODEL_NAME}


@app.get("/ready")
def ready() -> dict:
    try:
        get_encoder()
        return {"status": "ready", "model": MODEL_NAME}
    except Exception as exc:  # pragma: no cover - depends on model download state
        raise HTTPException(status_code=503, detail=f"model not ready: {exc}")


@app.post("/rerank", response_model=RerankResult)
def rerank(payload: RerankRequest) -> RerankResult:
    if not payload.chunks:
        return RerankResult(results=[], elapsed_ms=0.0)

    t0 = time.perf_counter()
    try:
        encoder = get_encoder()
        pairs = [(payload.query, chunk.text) for chunk in payload.chunks]
        scores = encoder.predict(pairs, show_progress_bar=False)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"rerank failed: {exc}")

    ordered = sorted(
        zip(payload.chunks, scores),
        key=lambda pair: -float(pair[1]),
    )

    top_k = payload.top_k or len(ordered)
    results = [
        Chunk(id=chunk.id, text=chunk.text, score=float(score))
        for chunk, score in ordered[:top_k]
    ]
    return RerankResult(results=results, elapsed_ms=(time.perf_counter() - t0) * 1000)