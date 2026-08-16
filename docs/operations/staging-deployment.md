# Staging Environment & Deploy

This document covers the staging environment for Scout.io and the end-to-end deploy
process, including how to reset staging data to a known-good seed state.

## Purpose

Staging mirrors production (prod compose + GHCR images) but runs **fully self-contained**
so it never touches production data or secrets:

- Its own **Postgres** (database `scout_staging`), **Redis**, and **Qdrant** instances with
  separate volumes (`staging_*`).
- Its own **Vault** instance with a separate volume; backend runs with
  `DEPLOYMENT_ENV=staging` so secrets are read from `secret/scout-io/staging/*`.
- A **staging-only subdomain** (`staging.scout.io` by default) in the nginx config.
- Staging/test **Razorpay keys** via the staging Vault (never production keys).
- Staging host ports default to `8080`/`8443` (HTTP/HTTPS) so staging can run alongside
  production on the same host without clashing on `80`/`443`. Override via
  `STAGING_HTTP_PORT` / `STAGING_HTTPS_PORT` if a dedicated host is used.

## Architecture

`docker/docker-compose.staging.yml` defines:

| Service | Notes |
| --- | --- |
| `vault` | Staging Vault (file backend, `staging_vault_data` volume) |
| `postgres` | `scout_staging` DB, `staging_postgres_data` volume |
| `redis` | `staging_redis_data` volume |
| `qdrant` | `staging_qdrant_data` volume |
| `backend` | `DEPLOYMENT_ENV=staging`, GHCR image by default, Vault + env fallbacks |
| `frontend` | GHCR image, built with staging API/WS URLs |
| `nginx` | `nginx.staging.conf`, staging subdomain, TLS certs from `./nginx/ssl` |
| `celery_worker` / `celery_billing_worker` | Async task workers (GHCR backend image) |
| `celery_beat` / `celery_billing_beat` | Beat schedulers (GHCR backend image) |

The compose file supports `build:` (source) and `image:` (GHCR). `docker compose up -d`
builds from source by default; `docker compose pull && docker compose up -d` uses the
pushed GHCR images (this is what the CI deploy step will do).

## Deploy process

### 1. Provision the host

A single Docker host (VM or dedicated box) with Docker + Compose v2. DNS for
`staging.scout.io` points at the host.

### 2. Checkout / copy the repo

```bash
git clone <repo> scout-io && cd scout-io/docker
```

### 3. Configure environment

Create `docker/.env` (compose reads it automatically) with staging values:

```bash
# Data
STAGING_POSTGRES_USER=scout
STAGING_POSTGRES_PASSWORD=<strong-staging-password>
STAGING_POSTGRES_DB=scout_staging

# Vault (any value is fine; secrets can also be provided via env fallbacks)
STAGING_VAULT_TOKEN=staging-root-token

# URLs (defaults shown)
STAGING_API_URL=https://staging.scout.io
STAGING_WS_URL=wss://staging.scout.io/ws

# Ports (defaults shown)
STAGING_HTTP_PORT=8080
STAGING_HTTPS_PORT=8443
```

For GHCR deploys set `IMAGE_NAMESPACE` (your GitHub org/namespace) and `IMAGE_TAG`
(`latest` or a commit SHA).

### 4. TLS certificates

Place staging cert/key at `docker/nginx/ssl/cert.pem` and `docker/nginx/ssl/key.pem`
(use a real cert for the staging subdomain, or a self-signed/Let's Encrypt cert for
testing). The nginx container mounts this directory read-only.

### 5. Provision staging Vault secrets (optional but recommended)

The backend reads secrets from Vault path `secret/scout-io/staging/<key>` first, then
falls back to the env vars baked into the compose file. To use Vault (required for
Razorpay test keys), exec into the vault container and write the secrets:

```bash
docker compose -f docker-compose.staging.yml exec vault sh
vault login <STAGING_VAULT_TOKEN>
vault secrets enable -path=secret kv-v2
vault kv put secret/scout-io/staging/razorpay_key_id value=rzp_test_xxx
vault kv put secret/scout-io/staging/razorpay_key_secret value=...
vault kv put secret/scout-io/staging/razorpay_webhook_secret value=...
```

When Vault is healthy, the env-var fallbacks are ignored for secrets that exist in
Vault, so staging never falls through to production credentials.

### 6. Deploy

```bash
cd docker
docker compose -f docker-compose.staging.yml pull        # pull GHCR images (if using images)
docker compose -f docker-compose.staging.yml up -d       # build or start everything
docker compose -f docker-compose.staging.yml ps          # verify all healthy
```

### 7. Migrations

```bash
docker compose -f docker-compose.staging.yml exec backend alembic upgrade head
```

## Reset / seed staging data

Staging is disposable — reset it to a known-good seed state whenever a repeatable test
is needed:

```bash
# Wipe ALL staging data (postgres, redis, qdrant, vault volumes)
cd docker
docker compose -f docker-compose.staging.yml down -v --remove-orphans

# Bring the stack back up (fresh volumes)
docker compose -f docker-compose.staging.yml up -d

# Run migrations
docker compose -f docker-compose.staging.yml exec backend alembic upgrade head

# Seed a baseline org + admin user (see scripts/seed_test_data.py)
cd ..
python scripts/seed_test_data.py   # or: docker compose exec backend python scripts/seed_test_data.py
```

The `-v` flag deletes the `staging_*` volumes so every reset starts from a blank
Postgres/Redis/Qdrant/Vault — identical to the first deploy.

## CI/CD wiring

- `.github/workflows/build.yml` builds and pushes `backend`, `frontend`, and `widget`
  images to GHCR on merge to `main` (tagged with the commit SHA + `latest`).
- A future `deploy-staging.yml` (Sprint 4.2 follow-up) will SSH to the staging host and
  run `docker compose pull && up -d` using the SHA-tagged images. Until then, deploys are
  manual via the steps above.
- Staging secrets required in GitHub when that workflow is added: `STAGING_HOST`,
  `STAGING_SSH_USER`, `STAGING_SSH_KEY`, `STAGING_VAULT_TOKEN`.

## Isolation guarantees

- All data volumes are prefixed `staging_*`; production uses `postgres_data`,
  `redis_data`, `qdrant_data`, `vault_data`, `vault_logs`.
- Backend runs `DEPLOYMENT_ENV=staging` — secret manager resolves
  `secret/scout-io/staging/*`, never `production`.
- Separate Postgres DB (`scout_staging`), separate Redis/Qdrant/Vault instances.
- Separate nginx virtual host (`staging.scout.io`) and separate host ports.
- Razorpay test keys only; the `BILLING_ENABLED=true` flag exercises billing against
  Razorpay's sandbox, not live accounts.
---

## CI/CD (merged)

> The following section was merged from `docs/CI-CD.md`.

# CI/CD

## Overview

| Workflow | Trigger | Purpose |
| --- | --- | --- |
| `.github/workflows/ci.yml` | Every pull request | Backend pytest + syntax check, frontend vitest + typecheck, widget vitest + typecheck. All steps must pass for the PR to be mergeable. |
| `.github/workflows/build.yml` | Push to `main` (after merge) | Build and push `backend`, `frontend`, and `widget` images to GitHub Container Registry (GHCR), tagged with the commit SHA and `latest`. |

There is **no** `deploy-staging.yml` yet. Staging deployment is deferred until the
staging environment (docker-compose.staging.yml, staging host, docs/operations/staging-deployment.md) is built
in Sprint 4.2; at that point add a workflow that deploys the freshly built images via SSH +
`docker compose pull && up -d` (or the host's actual deploy mechanism).

## Required status checks on `main` (branch protection)

Untested code must not merge to `main`. Configure branch protection on the `main` branch:

1. GitHub repo **Settings → Branches → Add branch protection rule**.
2. Branch name pattern: `main`.
3. Enable **Require a pull request before merging** (recommended: 1 review).
4. Enable **Require status checks to pass before merging**.
5. In the status check search box, add the checks produced by `ci.yml`:
   - `Backend (pytest + syntax)`
   - `Frontend (vitest + typecheck)`
   - `Widget (vitest + typecheck)`
6. Enable **Do not allow bypassing the above settings**.
7. Optionally enable **Require branches to be up to date before merging** so a new
   commit on `main` forces a re-run before the PR can merge.

Until this rule is enabled, use the GitHub UI **Settings → Branches** for the `main`
branch and add the three checks as required status checks. CI must be green before any
merge, and `build.yml` will only run on `main` after a merged, tested PR.

## Secrets

- No secrets are required for `ci.yml` or `build.yml` (GHCR login uses the built-in
  `GITHUB_TOKEN` with `packages: write`).
- Staging/production deploys (future) will need `STAGING_HOST`, `STAGING_SSH_USER`,
  `STAGING_SSH_KEY`, and `STAGING_VAULT_TOKEN` configured as repository secrets.

## Production deploys

Automatic production deploys are intentionally **not** wired up. They stay manual/gated
until the disaster-recovery work (Sprint 6) is in place, at which point a separate,
approval-gated deploy workflow can be added on top of the same GHCR image pipeline.