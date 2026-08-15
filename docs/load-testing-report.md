# Scout.io Load-Testing Report

Date: 2026-08-16
Tooling: Locust 2.46.3 (headless, CSV output)
Load suite: `load-tests/` (seed.py, widget_chat_locustfile.py, ingestion_locustfile.py, common.py)

## Environment under test

- Backend: local uvicorn (`app.main:app`, single worker) with `MOCK_LLM=true`
  (LLM/embedding calls replaced by deterministic canned responses — no provider
  cost; the `llm_generate` stage still sleeps ~120 ms to model provider latency).
- Postgres 16, Redis 7, Qdrant (all local Docker containers).
- Widget messages: POST `/api/v1/widget/messages`; per-org rate limit
  `RATE_LIMIT_PER_ORG=1000/minute` active.
- Ingestion: POST knowledge-sources → POST sync → Celery worker
  (`app.tasks.embedding_tasks.celery_app`, concurrency 2) → chunk → embed →
  Qdrant upsert.

## Methodology

- Seeded 8 orgs (6 widget sessions + 3 knowledge sources each) via
  `load-tests/seed.py`.
- Per-stage latency is harvested from the `X-Pipeline-Timings` response header
  and emitted as per-stage Locust request events (`widget/<group>[stage]:<stage>`).
- Widget chat run: 30% of users pinned to "bursty" orgs, 70% to "normal" orgs,
  to expose per-org starvation.
- Ingestion run: each user owns one org and drives create → dispatch → poll
  until `sync_status` reaches `completed`/`failed`.

## Results — widget chat

Full-run aggregated (ramped to ~72 concurrent users on a single worker):

| Metric | widget/bursty | widget/normal |
|---|---|---|
| Requests | 58 | 204 |
| Failures | 2 (3.4%) | 5 (2.5%) |
| Client-observed p50 | 7.9 s | 7.7 s |
| Client-observed p95 | 31 s | 31 s |

Server-side per-stage latency (from `X-Pipeline-Timings`, ms):

| Stage | p50 | p95 |
|---|---|---|
| cache_lookup | <1 | <1 |
| retrieval | 10 | 28 |
| session_memory | <1 | <1 |
| llm_generate | 120 | 140 |
| validation | <1 | <1 |
| safety | <1 | <1 |
| postprocess | <1 | <1 |
| **total (server)** | **130** | **160–200** |

Key observations:

1. **The response pipeline itself is fast and stable under concurrency.** Server
   `total` stays ~130 ms (dominated by the ~120 ms mock LLM) with p95 ≤ 200 ms
   even while client-observed latency climbs to tens of seconds.
2. **The first bottleneck is the single uvicorn worker.** Sync FastAPI routes run
   in the default threadpool; at ~70 concurrent widget users the threadpool
   saturates and requests queue for seconds. This is an app-server concurrency
   limit, not a pipeline, DB, or Qdrant limit.
3. **Starvation control works.** 429 failures were ~0% for both groups at the
   default 1000/min limit (not reached during the smoke). Unit tests
   (`tests/test_load_hooks.py`) force a 2–3/min limit and confirm org A hitting
   its cap does not block org B — per-org keying prevents cross-org starvation.
   The bursty/normal split in the locustfile is in place to verify this at
   higher load in a proper soak run.

## Results — knowledge ingestion

Concurrent 6 users, ~25 s, worker concurrency 2:

| Group | Requests | Failures | p50 | p95 |
|---|---|---|---|---|
| create-source | 38 | 0 | 39 ms | 130 ms |
| dispatch-sync | 30–110 ms | 0 | 31 ms | 190 ms |
| poll-status | 126 | 0 | 22 ms | 31 ms |

- 38 knowledge sources created, dispatched, and synced to `completed` (2 chunks
  each) with **0 failures**. Ingestion pipeline (create → Celery → chunk →
  embed → Qdrant) is fully functional under multi-org concurrency.
- Dispatch and create are sub-50 ms; the dominant cost is Celery task execution
  (≈12 s for a 2-chunk source including the mock embedding sleep), which is
  throughput-bound by worker count.

## First bottleneck and scaling recommendation

**Bottleneck: app-server threadpool concurrency (single uvicorn worker).**

Evidence: server-side pipeline p95 ≈ 200 ms while client-observed p95 ≈ 31 s at
only ~72 users. The pipeline, Postgres (default pool `pool_size=5`,
`max_overflow=10`), and Qdrant are all well within budget at this load.

Cheapest fixes, in order:

1. **Scale the API app server first.** Run uvicorn/gunicorn with more workers
   (e.g. `--workers 4`, or container replicas behind a load balancer). This
   directly removes the queuing that produced the 31 s client p95. Re-run the
   widget smoke at the same concurrency and confirm client p95 drops toward the
   server p95.
2. **Right-size the Postgres pool** if worker scaling pushes DB concurrency:
   raise `pool_size`/`max_overflow` in `app/db/session.py` (keep
   `pool_pre_ping=True`) and monitor `scout_dependency_health`/DB connections.
3. **Scale Celery workers for ingestion** (dispatch latency is fine; total sync
   time scales with `--concurrency`). `scout_celery_queue_depth` alert
   (`docker/prometheus/alerts.yml`) fires when the queue grows, signalling when
   to add workers.

## How to reproduce

```bash
cd backend
MOCK_LLM=true python ../load-tests/seed.py --orgs 20 --sessions 10 --sources 5

cd ../load-tests
locust -f widget_chat_locustfile.py --host http://<host> \
  --headless -u 20 -r 5 --run-time 15m --csv=reports/widget_chat   # ramp 1x->10x
locust -f ingestion_locustfile.py --host http://<host> \
  --headless -u 30 -r 5 --run-time 10m --csv=reports/ingestion     # needs Celery worker
```

Full methodology and scenario descriptions in `load-tests/README.md`.

## Notes

- `MOCK_LLM=true` replaced provider calls (verified by
  `tests/test_load_hooks.py::test_mock_llm_never_calls_provider`). For a
  production-cost run, remove the flag and watch `scout_llm_fallback_triggers_total`.
- Smoke runs used a 2-chunk knowledge source; adjust `SAMPLE_DOC` in seed.py for
  larger payloads.
- One pre-existing defect was fixed during this work: alembic migration
  `0006_rls_policies.py` created a `messages` RLS policy referencing a
  non-existent `organization_id` column and then created a duplicate policy.
  `upgrade()` now skips `messages` in the generic loop (it has no org column and
  is handled by `_create_messages_rls`).