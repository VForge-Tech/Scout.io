# Demo Deployment (Docker Compose)

This guide deploys a full Scout.io stack with Docker Compose. It is verified
against the compose files in `docker/` and is the recommended way to run the
platform for a demo or a self-hosted deployment. For the self-contained staging
environment, see `docs/operations/staging-deployment.md`.

## 1. Overview

Three compose files layer on top of the base `docker/docker-compose.yml`:

| File | Purpose |
|------|---------|
| `docker/docker-compose.yml` | Base: vault, backend, postgres, redis; qdrant/ollama/reranker under the `full` profile |
| `docker/docker-compose.dev.yml` | Dev overlay: backend hot-reload (`--reload`, bind mount) |
| `docker/docker-compose.prod.yml` | Prod overlay: nginx (TLS), Celery workers/beat, qdrant/ollama/pgvector, observability stack, backup |

Profiles on the base file: `full` (qdrant, ollama, reranker), `ollama`,
`pgvector`. The prod overlay enables `full` for qdrant/ollama and adds pgvector
under `pgvector`.

### Service summary (base file)

| Service | Image | Ports | Notes |
|---------|-------|-------|-------|
| vault | `hashicorp/vault:1.15` | 8200 | Dev mode (root token `dev-root-token`) |
| backend | build `../backend` | 8000 | Requires `backend/.env` |
| postgres | `postgres:16-alpine` | 5432 | User/pass/db default `scout`/`changeme`/`scout` |
| redis | `redis:7-alpine` | 6379 | |
| qdrant | `qdrant/qdrant:latest` | 6333, 6334 | profile `full` |
| ollama | `ollama/ollama:latest` | 11434 | profiles `full`, `ollama` |
| reranker | build `../services/reranker` | 8082 | profile `full`; limits 2 CPU / 2 GB |

### Service summary (prod overlay)

| Service | Notes |
|---------|-------|
| frontend | build `../frontend`, port 3000, needs `frontend/.env` |
| nginx | `nginx:alpine`, ports 80/443, TLS, proxies `/api/`, `/ws`, `/health`, `/docs`, `/redoc`, `/openapi.json`, `/` |
| celery_worker / celery_billing_worker | embedding + billing task workers |
| celery_beat / celery_billing_beat | scheduled analytics + billing aggregation |
| prometheus / grafana / loki / promtail / alertmanager | Observability stack (see `docs/operations/monitoring-observability.md`) |
| backup | Nightly Postgres + Qdrant backup to S3 (see `docs/operations/disaster-recovery.md`) |

## 2. Prerequisites

- Docker with the compose plugin.
- LLM API keys (at least one: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`,
  `TOGETHER_API_KEY`, `GEMINI_API_KEY`, or `AZURE_OPENAI_API_KEY`).
- A domain/DNS pointing at the host for TLS (prod overlay).
- TLS certificate/key at `docker/nginx/ssl/cert.pem` and `key.pem`
  (the `docker/nginx/ssl/` directory is not checked in — create it).

## 3. Configure environment

```bash
scripts/setup_env.sh
```

Edit `backend/.env`: add at least one LLM key and set `BILLING_ENABLED` as
desired. Edit `frontend/.env` for the dashboard's public API/WS URLs (for prod
use `https://your-domain` / `wss://your-domain/ws`). See
`docs/getting-started/environment-setup.md` for the full variable reference.

## 4. Start the stack

### Demo (base + dev overlay, hot reload)

```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml --profile full up -d
```

### Production-like (base + prod overlay)

```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml --profile full up -d
```

### Minimal (Postgres + Redis + backend, no Qdrant)

```bash
docker compose -f docker/docker-compose.yml up -d postgres redis
```

## 5. Run migrations

The backend needs the schema applied before serving:

```bash
cd backend
alembic upgrade head
```

(Or run `scripts/run_migrations.sh`.) Migrations are also applied by the
restore script in disaster-recovery scenarios.

## 6. Seed data (optional)

`scripts/seed_test_data.py` creates orgs, users, chatbots, and knowledge
sources for exercising the platform:

```bash
cd backend
python scripts/seed_test_data.py
```

Requires a reachable backend DB and an LLM key for embedding. The staging reset
procedure uses this script too (see `docs/operations/staging-deployment.md`).

## 7. Verify

### Backend health

```bash
curl http://localhost:8000/health
# {"status": "ok", "service": "scout-api", "version": "0.4.0"}

curl http://localhost:8000/health/ready     # DB / Redis / Qdrant status
curl http://localhost:8000/docs             # Swagger UI
```

### Frontend & TLS (prod overlay)

```bash
curl -I https://your-domain        # 200, TLS
curl https://your-domain/api/v1/auth/me   # 401 (unauthenticated) — proxy works
```

### Services

```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml ps
docker compose ... logs -f backend
```

Grafana is available at `http://<host>:3001` (default admin/admin — change via
`GRAFANA_ADMIN_USER` / `GRAFANA_ADMIN_PASSWORD`). Prometheus: `:9090`, Loki:
`:3100`, Alertmanager: `:9093`.

## Operational notes

- **Profiles**: qdrant, ollama, reranker, and the observability/backup services
  require `--profile full`. Without it, only vault/backend/postgres/redis
  (and, for prod, frontend/nginx/celery) start.
- **Vault**: the base file runs Vault in dev mode (`dev-root-token`) for local
  development. For production, provision Vault properly (see
  `docs/operations/security-and-compliance.md`) and set `VAULT_TOKEN` in
  `docker/.env`.
- **Backup**: the prod overlay's `backup` service backs up Postgres + Qdrant to
  S3-compatible storage nightly. Set `S3_ENDPOINT`, `S3_BUCKET`,
  `S3_ACCESS_KEY`, `S3_SECRET_KEY`. On-demand restore: `scripts/restore.sh
  --latest`. See `docs/operations/disaster-recovery.md`.
- **Billing**: Razorpay is feature-flagged. Enable `BILLING_ENABLED=true` only
  with test-mode keys until KYC activation. See
  `docs/integrations/billing-razorpay.md`.
- **Observability**: metrics, logs, and alerts ship with the prod overlay. See
  `docs/operations/monitoring-observability.md`.

## Troubleshooting

- **Port conflicts**: adjust host ports in the compose files or check listeners
  with `netstat -an | findstr "5432 6379 6333 8000 3000"`.
- **Backend won't start / JSONB errors**: migrations target Postgres; make sure
  `alembic upgrade head` ran against the Postgres service, not SQLite.
- **TLS cert missing**: create `docker/nginx/ssl/cert.pem` + `key.pem`
  (e.g. Let's Encrypt `certbot` or a self-signed cert for testing).
- **Docker rebuild**: `docker compose -f ... up --build -d` after dependency
  changes.