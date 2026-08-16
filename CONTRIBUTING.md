# Contributing to Scout.io

Thank you for contributing. Scout.io is a multi-tenant AI knowledge platform
(FastAPI + Next.js + widget SDKs). This guide covers how to work with the repo.

## Repository layout

```
backend/          FastAPI application (Python 3.12)
frontend/         Next.js dashboard (Pages Router, TypeScript, Tailwind)
widget/           Embeddable chat widget (React + Rollup)
sdk/js            JavaScript SDK (scout-sdk)
sdk/python        Python SDK (scout_sdk)
services/reranker  Standalone cross-encoder reranking service
docker/           Docker Compose files, Nginx, observability, backup
scripts/          Setup, migration, seed, and restore scripts
docs/             Documentation (organized by audience)
load-tests/       Locust load-testing suite
```

## Development environment

See `docs/getting-started/`:

- `environment-setup.md` — `.env` wiring, Vault path convention, feature flags
- `local-development.md` — running backend, frontend, widget, tests locally
- `demo-deployment.md` — full Docker Compose deployment

Quick start:

```bash
scripts/setup_env.sh          # copies each .env.example -> .env
cd backend && uv pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

## Testing

Every change must keep the test suites green:

```bash
# Backend (FastAPI/Pytest) — the primary suite
cd backend && python -m pytest tests/ -q

# Frontend (vitest + typecheck)
cd frontend && npm test && npm run typecheck

# Widget (vitest + lint)
cd widget && npm test && npm run lint
```

Backend tests run on SQLite by default (a subset of Postgres-only RLS tests are
skipped). New endpoints should include test coverage in `backend/tests/`,
matching the patterns of existing suites (fixtures, `_seed`, client helpers in
`conftest.py`).

## CI / branch protection

Pull requests run `.github/workflows/ci.yml`:

- `Backend (pytest + syntax)` — full pytest suite + `compileall`
- `Frontend (vitest + typecheck)` — vitest + `tsc --noEmit`
- `Widget (vitest + typecheck)` — vitest + `tsc --noEmit`

All three are required status checks on `main`. Merges to `main` trigger
`.github/workflows/build.yml`, which builds and pushes `backend`, `frontend`,
and `widget` images to GHCR tagged with the commit SHA and `latest`. See
`docs/operations/staging-deployment.md` for the full pipeline description.

## Coding conventions

- **Backend**: FastAPI routers in `backend/app/api/endpoints/`, services in
  `backend/app/domain/` (or `backend/app/core/`), Pydantic schemas in
  `backend/app/schemas/`, models in `backend/app/models/`. Auth via
  `get_current_user` / `get_db_with_org` dependencies (RLS context is set per
  request — never bypass org scoping). Add audit log entries for sensitive
  actions via `app/utils/audit.py`.
- **Frontend**: Pages Router under `frontend/pages/`; API access through
  `frontend/src/lib/api.ts` (handles auth redirects). Match existing Tailwind
  conventions and component patterns.
- **Widget/SDKs**: keep the embeddable widget dependency-light and buildable
  with Rollup; SDK endpoint calls must match the backend routes exactly (see
  the API reference in `docs/guides/developer-portal-guide.md`).
- **Migrations**: every schema change gets an Alembic migration in
  `backend/alembic/versions/` (next number after `0009_*`). Postgres-only
  features (e.g. RLS) must degrade gracefully on SQLite so the test suite
  keeps passing.
- **Secrets**: never commit real secrets. Development reads from `.env` via the
  Vault-backed `SecretManager` (`backend/app/core/secrets.py`); production
  reads from Vault. Keep `.env.example` files free of real placeholder values.

## Documentation

Docs live in `docs/` and are organized by audience (`getting-started`,
`architecture`, `guides`, `operations`, `integrations`, `roadmap`). When you
change behavior, update the relevant doc and keep the `docs/README.md` table of
contents accurate. Never reference stale paths or endpoints.

## Commit and PR guidelines

- Small, focused commits with descriptive messages (see `git log` for style).
- Run the relevant test suite before pushing.
- Open a PR against `main`; the CI status checks must pass.

## Reporting issues

Use the GitHub issue tracker. For security vulnerabilities, follow the
procedure in `SECURITY.md`.