# Scout.io Changelog

All notable changes to Scout.io are documented in this file. The project tracks
sprints (Phase IV onward) and numbered versions (0.x). See
`docs/roadmap.md` for the full implementation history and phase plan.

## [0.5.0] — 2026-08-16

- **Beta onboarding instrumentation & feedback** (Sprint 24)
  - Onboarding checklist (`GET /api/v1/analytics/onboarding`) computed from
    live org state, recorded idempotently as `onboarding.step` analytics events.
  - In-dashboard feedback widget (`POST /api/v1/analytics/feedback`) with
    thumbs up/down + optional text.
  - Admin-only funnel view (`GET /api/v1/admin/onboarding/funnel`) across all
    beta orgs.
  - Frontend: `FeedbackWidget` component, onboarding checklist on the dashboard
    overview, feedback prompts after chatbot test and first knowledge-source
    sync, admin `Onboarding & Feedback` page.
- **TOTP multi-factor authentication** (Sprint 23)
  - `totp_secret` (Fernet-encrypted), `mfa_enabled`, `recovery_codes`
    (bcrypt-hashed) on the User model; migration `0009`.
  - MFA endpoints under `/api/v1/auth/mfa/*`: status, setup (QR), enable,
    disable, recovery-code regeneration, verify-login.
  - Login flow returns `{mfa_required, mfa_token}` for MFA users; two-step
    login via `/api/v1/auth/mfa/verify-login`.
  - MFA mandatory for platform admins (`require_platform_admin` returns 403
    until enabled); widget session auth unaffected.
  - Frontend: MFA step in login, Two-Factor Authentication card in settings.
- **Documentation reorganization**: docs moved into audience-based tree under
  `docs/` (`getting-started`, `architecture`, `guides`, `operations`,
  `integrations`, `roadmap`), root README trimmed, added `LICENSE`,
  `CONTRIBUTING.md`, `CHANGELOG.md`, `SECURITY.md`.

## [0.4.0] — 2026-08-08

- **Org offboarding / permanent data deletion** (Sprint 22): two-step
  platform-admin flow (`/api/v1/admin/organizations/{org_id}/offboard[/confirm]`)
  with deletion preview + signed confirmation token; Postgres (FK-safe order),
  Qdrant/pgvector, Redis, and upload purge; audit-proof retained.
- **Backup & disaster recovery** (Sprint 21): nightly `pg_dump` + Qdrant
  snapshot to S3-compatible object storage, retention (daily 30d / weekly 90d),
  and `scripts/restore.sh` with measured ~22 s RTO. See
  `docs/operations/disaster-recovery.md`.
- **Cross-encoder reranking service** (Sprint 20): standalone `services/reranker`
  behind `reranker_enabled` flag with graceful fallback; MRR@K measured.
- **Load-testing suite** (Sprint 19): Locust workloads, mock-LLM hooks,
  per-stage pipeline timings, per-org rate limiting verified. See
  `docs/operations/monitoring-observability.md`.
- **Observability stack** (Sprint 18): Prometheus `/metrics`, Grafana (port
  3001), Loki + promtail, Alertmanager → Slack; trace-id → Grafana deep links.
- **Staging environment + .dockerignore** (Sprint 17): self-contained
  `docker-compose.staging.yml`, staging Nginx vhost, per-component
  `.dockerignore`.
- **CI/CD** (Sprint 16): GitHub Actions `ci.yml` (backend pytest, frontend +
  widget vitest/typecheck) and `build.yml` (GHCR image publish on main).
- **Subscription management** (Sprint 15): change-plan / cancel / invoice
  history on `/dashboard/billing`.
- **Usage-based billing** (Sprint 14): `LLMUsage` recording, Razorpay overage
  add-ons, `UsageBillingRecord` aggregation, 80% soft-limit warning.
- **Plans & billing** (Sprint 13): Razorpay Subscriptions (Free/Starter/
  Growth/Scale), plan limits enforced at the API layer, billing feature flag.
- **Tenant dashboard** (Sprint 12): `/dashboard` for chatbots, knowledge
  sources, analytics (recharts), settings.
- **Adversarial security hardening** (Sprint 11): 22 prompt-injection tests,
  system-prompt hardening, post-generation safety filter, sanitizer
  extensions.
- **Vault secret management** (Sprint 10): `SecretManager` with env fallback,
  path convention `secret/scout-io/<env>/<key>`.
- **Row-Level Security** (Sprint 9): Postgres RLS on org-scoped tables,
  `SET LOCAL app.current_org_id` per request, admin bypass policy.

## [0.3.0] — 2026-07-15

Phase III: AI & RAG pipeline.

- Knowledge engine (embeddings, Qdrant store, policy-aware retrieval engine).
- AI router (LiteLLM primary → fallback → graceful error chain).
- Memory framework (session / knowledge / org / optimization caches).
- Response pipeline (cache → retrieval → context → generation → validation →
  sanitization).
- Validation & sanitization (hallucination detection, secret stripping).
- `LLMUsage` model, debug retrieval endpoint, Celery embedding tasks.

## [0.2.0] — 2026-06-01

Phase II: Core platform.

- `ApiKey`, `AuditLog`, `Message` models; widget session tokens (`type: widget`).
- Developer portal (API keys, widget snippet), admin endpoints, org analytics.
- Frontend Pages Router shell, Tailwind.

## [0.1.0] — 2026-05-01

Phase I: Foundation.

- Organization / User / Chatbot / Policy / KnowledgeSource / ChatSession models.
- JWT auth (access + refresh), bcrypt password hashing.
- Auth, organizations, chatbots, policies, knowledge sources CRUD.
- Admin endpoints, role-based access control, org isolation, rate limiting.
- Celery setup, Alembic initial migration, Docker Compose (backend, postgres,
  redis, qdrant).