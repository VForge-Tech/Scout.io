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