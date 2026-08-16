# Observability

Scout runs a self-hosted observability stack alongside the application in
`docker/docker-compose.prod.yml`:

| Service        | Image                        | Port   | Role                                                    |
| -------------- | ---------------------------- | ------ | ------------------------------------------------------- |
| prometheus     | `prom/prometheus:v2.53.0`    | 9090   | Scrapes the backend `/metrics` endpoint, evaluates alerts |
| grafana        | `grafana/grafana:11.1.0`     | 3001   | Dashboards over Prometheus + Loki                       |
| loki           | `grafana/loki:3.1.0`         | 3100   | Log store (30d retention)                               |
| promtail       | `grafana/promtail:3.1.0`     | —      | Ships container stdout (JSON) into Loki                 |
| alertmanager   | `prom/alertmanager:v0.27.0`  | 9093   | Routes alerts to Slack                                  |

Grafana listens on host port **3001** (3000 is the frontend).

## Data flow

- The backend exposes a Prometheus text-format `/metrics` endpoint
  (`app/core/metrics.py`), scraped by prometheus every 15s.
- Every request (except `/metrics`, `/health`, `/health/ready`) is recorded:
  counter + latency histogram keyed by `method`, route `path`, and `status`.
- The backend logs every request as JSON via `JSONLogFormatter`, including a
  `grafana_link` deep-link keyed by `trace_id` (see below).
- promtail discovers containers labelled `logging=promtail` (the backend,
  frontend, and celery workers are labelled in compose) and ships their
  stdout into Loki, tagged with `container`, `service`, and `stream`.

## Trace-id → Grafana link pattern

Every request gets a `trace_id` (`X-Trace-ID` response header, set by
`app/core/tracing.py`). The request JSON log line includes:

```json
{
  "timestamp": "2026-08-15T18:00:00.000Z",
  "level": "INFO",
  "logger": "scout.request",
  "message": "GET /api/v1/chatbots 200",
  "trace_id": "9f2c1a7e...",
  "method": "GET",
  "path": "/api/v1/chatbots",
  "status": 200,
  "duration_ms": 42,
  "grafana_link": "http://grafana:3000/explore?orgId=1&left=now-6h&right=now&query=%7Bjob%3D%22scout-backend%22%7D%20%7C%3D%20%22trace_id%22%3A%20%229f2c1a7e...%22"
}
```

The `grafana_link` opens Loki Explore filtered to the JSON log line carrying
that exact `trace_id` (`{job="scout-backend"} |= "trace_id": "<id>"`). An
on-call engineer can:

1. Receive a Slack alert (e.g. `APIErrorRateHigh`).
2. Click the dashboard link in the alert, find the failing endpoint.
3. Search Loki for the failing status/time window, copy a `trace_id`.
4. Follow its `grafana_link` to the exact request + exception context.

The Grafana base URL is configurable via `GRAFANA_BASE_URL` (default
`http://grafana:3000`, overridable in `backend/.env` as `grafana_base_url`).
For the link to be usable from a workstation, set it to the externally
reachable Grafana URL (e.g. `https://grafana.scout.io`).

## Alerting

Prometheus rules live in `docker/prometheus/alerts.yml`:

| Alert                       | Condition                                                                  | Severity | For  |
| --------------------------- | -------------------------------------------------------------------------- | -------- | ---- |
| `APIErrorRateHigh`          | per-endpoint 5xx share > 5%                                                | critical | 5m   |
| `DependencyDown`            | `scout_dependency_health == 0` (postgres / redis / qdrant)                 | critical | 2m   |
| `CeleryQueueGrowing`        | `increase(scout_celery_queue_depth[10m]) > 0` and depth > 10               | warning  | 5m   |
| `CeleryTaskFailureRateHigh` | > 20% of celery tasks failing over 15m                                     | warning  | 10m  |
| `LLMFallbackRateHigh`       | fallback triggers > 10% of requests                                        | warning  | 10m  |

### Slack

Alertmanager reads the Slack webhook from a file. Set `SLACK_WEBHOOK_URL` in
the compose environment; the container writes it to
`/etc/alertmanager/slack_webhook` at startup (Alertmanager cannot expand
`${VAR}` in config files, so the secret is injected via `slack_api_url_file`).
Without it, Alertmanager logs a warning and Slack notifications are disabled.

`docker-compose.prod.yml`:

```yaml
environment:
  - SLACK_WEBHOOK_URL=${SLACK_WEBHOOK_URL:-}
```

### PagerDuty swap

Replace/add a PagerDuty receiver in `docker/alertmanager/alertmanager.yml`:

```yaml
receivers:
  - name: pagerduty
    pagerduty_configs:
      - service_key: /etc/alertmanager/pagerduty_key
        severity: critical
```

Inject the key the same way as the Slack webhook, and point the desired
`routes[].receiver` at it. Both can coexist in one receiver
(`slack_configs` + `pagerduty_configs`) to fire Slack and PagerDuty together.

## Dashboards

Provisioned (read-only, refreshed every 30s) from `docker/grafana/`:

- **Scout Requests** (`scout-requests`) — RPS per endpoint, status-class mix,
  p50/p95 latency, 5xx error rate.
- **Scout Celery** (`scout-celery`) — queue depth, 10m growth, task
  success/failure rates.
- **Scout Dependency Health** (`scout-dependencies`) — postgres/redis/qdrant
  UP/DOWN (same checks as `/health/ready`).
- **Scout LLM Providers** (`scout-llm`) — fallback trigger rate, 24h total,
  fallback share of requests.

Dashboards are configured in
`docker/grafana/provisioning/datasources/datasources.yml` (Prometheus `scout-prom`,
Loki `scout-loki`); panels reference datasources by UID.

## Validation

Re-run config checks after edits:

```bash
docker run --rm -v "$PWD/docker/prometheus:/etc/prometheus:ro" \
  --entrypoint promtool prom/prometheus:v2.53.0 check config /etc/prometheus/prometheus.yml
```

Loki / promtail / alertmanager configs are validated by their `-config.file`
flag on startup; alertmanager additionally supports
`amtool check-config`. See `docker-compose.prod.yml` for the exact commands.
---

## Load-testing report (merged)

> The following section was merged from `docs/load-testing-report.md`.

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