# Cross-Encoder Reranking Service — Implementation Report

## Summary

Added a standalone cross-encoder reranker service that re-ranks Qdrant's
initial similarity results before they are passed into context building in the
response pipeline. The feature is opt-in (off by default), controlled by a
global config setting and a per-chatbot override stored in the chatbot's
`config` JSON column, with graceful degradation to Qdrant's original ordering
if the reranker is unreachable.

## Components

### Service: `services/reranker/`
- FastAPI app (`app/main.py`):
  - `POST /rerank` — body `{query, chunks: [{id, text, score}], top_k}` →
    `{results: [{id, text, score, rerank_score}], elapsed_ms}`. Chunks are
    scored with a cross-encoder and returned reordered by relevance; when
    `top_k` is given only the top-`top_k` are returned.
  - `GET /health` — liveness (reports loaded model).
  - `GET /ready` — readiness (model loaded and ready for inference).
- Model: `cross-encoder/ms-marco-MiniLM-L-6-v2` (CPU), loaded lazily and warmed
  on startup so the first request doesn't pay model-load latency.
- `Dockerfile` (python:3.11-slim, port 8082, healthcheck on `/ready`),
  `requirements.txt`, `.dockerignore`.
- `docker/docker-compose.yml`: added `reranker` service under the `full`
  profile with resource limits (`cpus: 2`, `memory: 2g`, reservation `1g`).

### Backend integration
- `backend/app/core/config.py` — new settings (all defaults keep the feature off):
  - `reranker_enabled: bool = False`
  - `reranker_url: str = "http://reranker:8082"`
  - `reranker_timeout_ms: int = 2000`
  - `reranker_retries: int = 1`
  - `reranker_max_candidates: int = 10`
- `backend/app/core/knowledge/reranker.py` — `RerankerClient` (httpx POST with
  timeout/retry, remaps response to `{id, text, score, rerank_score}`) and
  `RerankerUnavailable` exception raised after retries are exhausted or on 5xx.
- `backend/app/core/knowledge/engine.py` — `KnowledgeEngine._rerank()`:
  - Controlled by `settings.reranker_enabled` unless an explicit per-call
    override is passed (e.g. a chatbot's config value).
  - Fetches up to `max(reranker_max_candidates, top_k)` candidates so re-ranking
    has room to improve precision beyond the Qdrant top-K that gets used.
  - Any reranker failure (unreachable, timeout, 5xx, malformed response) is
    caught, logged, counted in the `scout_reranker_fallback_triggers_total`
    metric, and the original Qdrant ordering is returned — the request never
    fails because of the reranker.
  - Re-merges reranked results with original metadata (e.g. `source_id`,
    `chunk_index`) by `id`.
- `backend/app/core/pipeline/response_pipeline.py` — `run()` accepts
  `reranker_enabled: bool | None` and forwards it to `knowledge.retrieve()`.
- `backend/app/api/endpoints/widget_api.py` / `developer.py` — pass
  `chatbot.config.get("reranker_enabled")` through the pipeline.
- `backend/app/api/endpoints/retrieval.py` — debug endpoint exposes the flag and
  respects per-chatbot config.
- `backend/app/core/metrics.py` — new counter `scout_reranker_fallback_triggers_total`.

## Feature flags / disable-without-redeploy
- Global: set `reranker_enabled=false` (or unset) in config/env.
- Per-chatbot: store `{"reranker_enabled": true|false}` in the chatbot's `config`
  JSON column; the per-chatbot value overrides the global default.
- Values are read from the `Chatbot.config` at request time, so toggling requires
  no redeploy. The global flag is read from `get_settings()` at engine import
  time (matching existing `qdrant_enabled`/`mock_llm` behaviour), so changing the
  *global* default does require a restart; per-chatbot toggles do not.

## Fallback behaviour
If the reranker service is down, times out, or returns an error, `retrieve()`
keeps Qdrant's original similarity ordering, increments
`scout_reranker_fallback_triggers_total`, logs a warning, and returns normally.
This follows the codebase's existing "degrade, never fail" philosophy (Qdrant →
keyword search, LLM provider fallback, in-memory memory stores).

## Tests
- `services/reranker/tests/test_main.py` (5 tests, run locally): health,
  reordering by score, `top_k` limiting, empty-chunks validation, readiness —
  with the encoder mocked so the suite runs without the model.
- `backend/tests/test_reranker.py` (10 tests):
  - Client: reorder + `rerank_score`, retry-then-raise, transport error.
  - Engine: rerank reorders + merges metadata, disabled returns original order,
    global flag controls default, empty rerank result keeps original order,
    fallback on `RerankerUnavailable`, fallback on arbitrary exception,
    `retrieve()` reranks after Qdrant search, `retrieve()` falls back on failure.
- Backend full suite: **185 passed, 8 skipped** (up from 175 + 8).

## Retrieval precision: before/after

Measured with `backend/scripts/eval_reranker.py` against a constructed 36-chunk
knowledge base of product/support documents with 36 paraphrased natural-language
queries and ground-truth relevant chunks. Qdrant used real local embeddings
(`all-MiniLM-L6-v2`) so the comparison is meaningful (backend MOCK_LLM uses
hash-based vectors with no semantics). The reranker service ran the real
`ms-marco-MiniLM-L-6-v2` cross-encoder.

| Metric   | Qdrant-only | Qdrant + Reranker | Delta |
|----------|-------------|-------------------|-------|
| MRR@K    | 0.431       | 0.458             | +0.027 |
| nDCG@3   | 0.417       | 0.463             | +0.046 |
| nDCG@5   | 0.439       | 0.463             | +0.024 |

Findings:
- Reranking improves ranking precision on the constructed KB, especially nDCG@3
  (the position of the *single* best answer improves most).
- The dominant failure mode is **recall**, not ordering: for many queries the
  relevant chunk is not among the candidates Qdrant returns at all, so no
  reranker can recover it. A reranker only helps when the answer is already
  inside the candidate pool. Increasing `reranker_max_candidates` widens that
  pool and is the first knob to turn for further gains.
- On this small KB the per-query MRR mostly moved 1.0→1.0 or 0→0; the aggregate
  gains come from the handful of queries where the true chunk sat at rank 2-5
  and was pulled to #1.

## How to run

```bash
# 1. Start the reranker service (Docker or locally)
docker compose -f docker/docker-compose.yml --profile full up -d reranker
# or:
cd services/reranker && python -m uvicorn app.main:app --host 0.0.0.0 --port 8082

# 2. Enable globally (env) or per-chatbot (config JSON)
#    backend/.env: RERANKER_ENABLED=true

# 3. Optional: evaluate precision on the constructed KB
cd backend && python scripts/eval_reranker.py --reranker-url http://127.0.0.1:8082
```