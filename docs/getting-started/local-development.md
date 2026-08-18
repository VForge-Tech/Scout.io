# Local Development

Run Scout.io locally for development. For a full containerized deployment see
`docs/getting-started/demo-deployment.md`; for environment wiring see
`docs/getting-started/environment-setup.md`.

## Quick-start (recommended for a fast demo)

One-command install spins up the minimal stack — Postgres (with pgvector),
Redis, backend API, Celery worker, and the Next.js dashboard — and seeds a
demo organization + chatbot. No manual `.env` editing and no API keys needed
(retrieval runs in deterministic `MOCK_LLM` mode).

```bash
# From a checkout, or clone + install in one shot:
#   curl -fsSL https://raw.githubusercontent.com/VForge-Tech/Scout.io/main/scripts/install.sh | bash
./scripts/install.sh
```

Windows (PowerShell):

```powershell
.\scripts\install.ps1
```

What the installer does:

1. Checks prerequisites (Docker + Compose v2, git).
2. Clones/pulls the repo if needed.
3. Generates `backend/.env` + `frontend/.env` from demo defaults (a random
   `JWT_SECRET`; `QDRANT_ENABLED=false`, `PGVECTOR_ENABLED=true`,
   `CELERY_ENABLED=true`, `MOCK_LLM=true`).
4. `docker compose -f docker/docker-compose.quickstart.yml --profile quick-start up -d --build`.
5. Waits until `http://localhost:8000/health/ready` reports `healthy`.
6. Runs `backend/scripts/seed_demo.py` (creates the demo org/user/chatbot and
   syncs its knowledge source through the real ingestion pipeline).
7. Prints the demo login and opens the dashboard.

Demo login: `demo@scout.io` / `DemoPass123!` — Dashboard http://localhost:3000,
API docs http://localhost:8000/docs.

To use real LLM/embedding providers, add `OPENAI_API_KEY=...` (and/or
`ANTHROPIC_API_KEY=...`) to `backend/.env` and restart:

```bash
docker compose -f docker/docker-compose.quickstart.yml --profile quick-start up -d --force-recreate backend celery_worker
```

### Why Redis is in the quick-start profile

Knowledge-source ingestion is dispatched through Celery with Redis as the
broker (`/knowledge-sources/{id}/sync` returns 503 when Celery is disabled).
Dropping Redis would make the stack look healthy while background sync silently
never ran, so the quick-start profile keeps Redis + a `celery_worker` and
documents the dependency instead of hiding it.

### Why Qdrant is NOT in the quick-start profile

The engine now falls back to the `pgvector` store when `QDRANT_ENABLED=false`
and `PGVECTOR_ENABLED=true` (`backend/app/core/knowledge/engine.py`), so the
quick-start runs vector retrieval on Postgres and skips Qdrant, Vault, Ollama,
and the reranker entirely. `/health/ready` treats disabled services as
`skipped` rather than failing the readiness gate.

## Option A — Tests only (no infrastructure)

The backend test suite runs with zero external services (SQLite + in-memory
fallbacks):

```bash
cd backend
python -m pytest tests/ -v --tb=short
```

The current suite is **223 passing, 8 skipped** (the skipped tests are
Postgres-only RLS tests). Coverage includes auth, orgs/users, chatbots,
policies, knowledge sources, widget API, admin, developer portal, the AI/RAG
pipeline, validation/sanitization, analytics, MFA, billing, RLS, health checks,
onboarding, and load-test hooks.

## Option B — Full stack with Docker (recommended)

```bash
# 1. Set up .env files
scripts/setup_env.sh

# 2. Add at least one LLM API key to backend/.env (see environment-setup.md)

# 3. Start infrastructure
docker compose -f docker/docker-compose.yml --profile full up -d

# 4. Run migrations
cd backend
alembic upgrade head

# 5. Start the backend
uv pip install -r requirements.txt
uvicorn app.main:app --reload

# 6. Start the frontend
cd ../frontend
npm install
npm run dev
```

### Access points

- Frontend dashboard: http://localhost:3000
- Backend API: http://localhost:8000
- API docs (Swagger): http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Docker profiles

| Profile | Services | Use case |
|---------|----------|----------|
| (none) | vault, backend, postgres, redis | Default backend + infra |
| `--profile full` | + qdrant, ollama, reranker | Full stack |
| `--profile minimal` | + ollama | No Qdrant |
| `--profile pgvector` | + pgvector | Postgres vector fallback |
| `--profile quick-start` (`docker-compose.quickstart.yml`) | postgres(+pgvector), redis, backend, celery_worker, frontend | Fast demo, no Vault/Qdrant/LLM keys |

```bash
# Development with hot-reload
docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml --profile full up -d

# Quick-start (standalone minimal stack)
docker compose -f docker/docker-compose.quickstart.yml --profile quick-start up -d --build
```

`docker-compose.dev.yml` runs the backend with `--reload` and mounts
`../backend` so code changes apply live.

## Backend without Docker (SQLite MVP demo)

```bash
cd backend
pip install -r requirements.txt

# PowerShell
$env:DATABASE_URL="sqlite:///./scout_demo.db"
$env:JWT_SECRET="demo-secret-key-for-mvp"
$env:QDRANT_ENABLED="false"
$env:CELERY_ENABLED="false"
$env:LITELLM_ENABLED="false"
$env:REDIS_URL=""
$env:QDRANT_URL=""

uvicorn app.main:app --reload --port 8000
```

All endpoints are functional against SQLite with in-memory fallbacks; no
external services required.

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Pages: `/auth/login`, `/dashboard/*` (tenant), `/admin/*` (platform admin),
`/developer/*` (developer portal). API calls go through
`frontend/src/lib/api.ts` against `http://localhost:8000/api/v1`; relative
`/api/v1/...` calls are proxied by `next.config.js` rewrites.

## Widget

```bash
cd widget
npm install
npm run build
```

Build output: `dist/scout-widget.js` (UMD), `dist/scout-widget.esm.js` (ESM),
`dist/index.d.ts` (types). See `docs/guides/developer-portal-guide.md` for
embedding.

## Celery workers

```bash
cd backend
celery -A app.tasks.embedding_tasks.celery_app worker --loglevel=info
celery -A app.tasks.analytics_tasks.celery_app beat --loglevel=info
```

Scheduled tasks: daily analytics aggregation, usage billing aggregation.

## Database migrations

```bash
cd backend
alembic upgrade head    # apply
alembic downgrade base  # roll back (dev only)
```

Migrations live in `backend/alembic/versions/` (`0001_initial_schema` through
`0009_*`).

## Verifying the stack

```bash
# Backend health
curl http://localhost:8000/health
# {"status": "ok", "service": "scout-api", "version": "0.4.0"}

# Readiness (checks DB, Redis, Qdrant — disabled services are reported as "skipped")
curl http://localhost:8000/health/ready

# Metrics (Prometheus)
curl http://localhost:8000/metrics
```

## Troubleshooting

### Backend: ModuleNotFoundError: No module named 'app'

Run from the backend directory:

```bash
cd backend
uvicorn app.main:app --reload
```

### Backend: SQLite JSONB error

Alembic migrations use Postgres-specific `JSONB`. Use Docker with Postgres, or
run tests with `Base.metadata.create_all()` (SQLite).

### Frontend: "Missing required error components" / hydration errors

Cause: accessing `localStorage` during SSR. Guard the component with a mounted
state flag.

### Port conflicts

```bash
netstat -an | findstr "8000 3000 5432 6379 6333"
Stop-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess
```

### Docker issues

Restart Docker Desktop, then:

```bash
docker compose -f docker/docker-compose.yml --profile full up --build -d
```

### Storage cleanup

```bash
cd backend
rm -rf .venv .pytest_cache *.db __pycache__ .mypy_cache
cd ../frontend
rm -rf node_modules .next
cd ../widget
rm -rf node_modules dist
docker system prune -a --volumes -f
```