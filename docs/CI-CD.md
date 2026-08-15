# CI/CD

## Overview

| Workflow | Trigger | Purpose |
| --- | --- | --- |
| `.github/workflows/ci.yml` | Every pull request | Backend pytest + syntax check, frontend vitest + typecheck, widget vitest + typecheck. All steps must pass for the PR to be mergeable. |
| `.github/workflows/build.yml` | Push to `main` (after merge) | Build and push `backend`, `frontend`, and `widget` images to GitHub Container Registry (GHCR), tagged with the commit SHA and `latest`. |

There is **no** `deploy-staging.yml` yet. Staging deployment is deferred until the
staging environment (docker-compose.staging.yml, staging host, docs/staging.md) is built
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