# Scout.io Load-Testing Suite

Locust-based load tests that exercise the widget-chat and knowledge-ingestion
pipelines under multi-org concurrency. Designed to answer:

1. **Does per-org rate limiting prevent one org from starving another?**
   (`widget_chat_locustfile.py` with the bursty/normal group split)
2. **What is the p50/p95/p99 latency of the full response pipeline and of each
   stage** (retrieval, llm_generate, session_memory, …) at 1x → 10x launch-day
   concurrency?
3. **Where is the first bottleneck** (Qdrant query latency, Postgres pool
   exhaustion, Celery worker throughput) and what is the cheapest scaling fix?

## Prerequisites

- Backend running with `MOCK_LLM=true` (or provider keys, at cost). The seed
  script and both load tests are real-network; no LLM calls are made by the
  load tests themselves.
- For the ingestion test, the backend must run with `CELERY_ENABLED=true` and a
  live Celery worker (e.g. `docker compose --profile full` brings up the worker).
- Python 3.11+ with Locust installed:

      pip install -r load-tests/requirements.txt

## 1. Seed test data

`seed.py` writes orgs + users + chatbots + widget sessions + knowledge sources
directly to the backend's Postgres (same `DATABASE_URL` the backend uses) and
emits `load-tests/seed_state.json`.

Run from the **backend** directory so `app.*` imports resolve:

    cd backend
    MOCK_LLM=true python ../load-tests/seed.py --orgs 20 --sessions 10 --sources 5

Idempotency: it always appends new orgs; re-seed with different names or wipe
before a repeat run.

## 2. Widget chat (multi-org, starvation, ramp)

Headless run with the ramp shape (1x → 10x users over 5 min, hold 5 min) and
CSV output:

    cd load-tests
    locust -f widget_chat_locustfile.py --host http://localhost:8000 \
      --headless -u 20 -r 5 --run-time 15m --csv=reports/widget_chat

`-u` sets the baseline user count; the shape scales it up to 10x. 30% of users
hammer bursty orgs, the rest drive normal orgs. Compare the `widget/bursty` vs
`widget/normal` request groups in the CSV/web UI:

- **429 failure rate** for `normal` must stay ~0 while `bursty` may be capped —
  that proves per-org limiting prevents starvation.
- **`widget/*[stage]:<stage>`** request names give per-stage percentiles.

Interactive UI (with the starvation scenario at fixed load):

    locust -f widget_chat_locustfile.py --host http://localhost:8000

## 3. Knowledge ingestion

Requires a live Celery worker:

    cd load-tests
    locust -f ingestion_locustfile.py --host http://localhost:8000 \
      --headless -u 30 -r 5 --run-time 10m --csv=reports/ingestion

Groups:
- `ingestion/create-source` — source-row insert latency
- `ingestion/dispatch-sync` — Celery dispatch latency
- `ingestion/poll-status` — sync completion polling (time-to-complete proxy)

## 4. Report

Summarise the CSVs into `docs/load-testing-report.md` with:

- Environment (concurrency, ramp, MOCK_LLM, backend instance size)
- Full-pipeline p50/p95/p99 at 1x vs 10x
- Per-stage p95 table
- Starvation result: bursty vs normal 429/latency
- Ingestion throughput and sync completion times
- First bottleneck + scaling recommendation (see `backend/app/db/session.py`
  engine `pool_size`/`pool_pre_ping`, Qdrant config, Celery concurrency)