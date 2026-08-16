# Scout.io Progress Tracker

## Phase I: Foundation Layer [COMPLETED]

### Completed
- Database models: Organization, User, Chatbot, Policy, KnowledgeSource, ChatSession
- JWT authentication (access + refresh tokens) with bcrypt password hashing
- API endpoints: auth (login/refresh/logout), organizations, chatbots CRUD, policies CRUD, knowledge sources CRUD
- Admin endpoints: list orgs, get org, update status, platform stats
- Role-based access control with `require_admin` dependency
- Organization isolation enforced in all queries
- Rate limiting with slowapi
- Celery setup with basic health check task
- Alembic initial migration (0001_initial_schema)
- SQLite test infrastructure with 32 passing tests
- Docker Compose: backend, postgres, redis, qdrant services

---

## Phase II: Core Platform Layer [COMPLETED]

### Backend Models & Schemas
- `ApiKey` model: id, user_id, organization_id, name, key_prefix, key_hash, last_used_at, expires_at, is_active
- `AuditLog` model: id, user_id, organization_id, action, details (JSONB), ip_address, timestamp
- `Message` model: id, session_id, role, content, metadata (JSONB)
- Alembic migration 0002 adding api_keys, audit_logs, messages tables
- Pydantic schemas for ApiKey, AuditLog, Widget session/request/response
- `app/utils/audit.py` helper for logging audit events
- Widget session token support via JWT with `type: "widget"` claim

### API Endpoints
- Developer: `POST/DELETE /developer/api-keys`, `GET /developer/api-keys`, `GET /developer/widget-snippet`
- Widget: `POST /widget/sessions`, `POST /widget/messages`
- Admin: `PATCH/DELETE /admin/organizations/{id}`, `GET /admin/audit-logs`, `GET /admin/health`
- Analytics and sessions endpoints under `/organizations/me/`

### Frontend (Pages Router)
- Placeholder dashboard page
- Tailwind CSS configured
- Standalone build output

---

## Phase III: AI & RAG Pipeline [COMPLETED]

### Knowledge Engine
- `embeddings.py`: LiteLLM embedding abstraction (supports OpenAI, Anthropic, Gemini, Together AI)
- `qdrant_store.py`: Qdrant collection management, vector indexing with metadata, similarity search with org/chatbot filtering
- `engine.py`: Orchestrator with policy-aware retrieval (`source_filter`, `content_filter`)

### AI Router
- `config.py`: Model configuration mapping fast→cheap, balanced→medium, accurate→expensive
- `router.py`: LiteLLM wrapper with primary→fallback→graceful error chain, token counting, streaming

### Memory Framework
- `session_memory.py`: Redis-backed conversation history (last N messages), context builder
- `knowledge_memory.py`: Short-term cache for retrieved chunks
- `org_memory.py`: Organization config and policies cache
- `optimization_memory.py`: FAQ response caching

### Validation & Optimization
- `response_validator.py`: Hallucination detection via word overlap threshold
- `sanitizer.py`: Strips provider names, model names, API keys from responses
- `token_optimizer.py`: Context compression by token-aware priority truncation

### Pipeline
- `response_pipeline.py`: End-to-end pipeline: cache check → memory check → knowledge retrieval → context optimization → AI generation → validation → sanitization → cache → return

### Additional
- `LLMUsage` model for tracking token usage
- Updated widget API to use full ResponsePipeline
- Celery tasks for background embedding/indexing
- Debug retrieval endpoint: `GET /api/v1/debug/retrieve`
- Alembic migration 0003 for LLM usage tracking
- 62 passing tests (32 Phase II + 30 Phase III)

---

## Phase IV: Production Layer [IN PROGRESS]

### Sprint 1: Analytics Engine [COMPLETED]
- `AnalyticsEvent` model: event_type, entity_id, organization_id, chatbot_id, source_id, payload JSON
- `DailyAnalytics` model: per-day aggregates for sessions, messages, tokens, latency, feedback, sync stats
- Celery daily aggregation task (`aggregate_daily_analytics`)
- API endpoints:
  - `GET /analytics/chatbot/{chatbot_id}` – chatbot aggregate stats
  - `GET /analytics/organization` – org-wide summary
  - `GET /analytics/source/{source_id}` – source usage and sync stats
  - `GET /admin/analytics/platform` – platform-wide totals
  - `POST /analytics/events` – track raw analytics events

### Sprint 2: Security Enhancements [COMPLETED]
- API key authentication via `X-API-Key` header with bcrypt hash verification
- Audit logging on all sensitive actions: login, logout, chatbot create/delete, webhook create/delete, system config changes
- CORS configured with configurable `cors_origins` (whitelist-based)
- HTTPS termination via Nginx with SSL configuration
- Structured JSON logging to stdout via custom `JSONLogFormatter`
- Tracing middleware adding `X-Trace-ID` to all requests
- Rate limiting per IP and per organization configurable via settings
- Response sanitization strips provider names, model names, API keys, secrets

### Sprint 3: Error Handling & Graceful Degradation [COMPLETED]
- **LLM failures**: primary → fallback → graceful error response
- **Qdrant failures**: automatic fallback to keyword search (TF-IDF on scroll results)
- **Sync failures**: status tracking with retry support
- **Graceful shutdown**: DB connections properly closed via `get_db` generator pattern
- Configurable timeouts for broker connections

### Sprint 4: Monitoring & Observability [COMPLETED]
- Structured JSON logging with `trace_id`, `user_id`, `organization_id` context
- Tracing middleware: every request gets a `X-Trace-ID` header
- Health endpoints: `GET /health`, `GET /health/ready` (aggregates DB, Redis, Qdrant status)
- Admin system health page showing real-time service status
- Admin audit log viewer with pagination

### Sprint 5: Admin Dashboard [COMPLETED]
- Pages Router pages under `/admin/`:
  - **Dashboard** (`/admin`): Platform statistics cards
  - **Organizations** (`/admin/organizations`): List, search, suspend
  - **Audit Logs** (`/admin/audit-logs`): Paginated table with filters
  - **System Health** (`/admin/system-health`): Service status cards
  - **Settings** (`/admin/settings`): System config key-value editor

### Sprint 6: Developer Portal [COMPLETED]
- Pages Router pages under `/developer/`:
  - **Dashboard** (`/developer`): Overview with link cards
  - **API Keys** (`/developer/api-keys`): Create (show once), list, revoke
  - **API Docs** (`/developer/docs`): Interactive docs links + auth info
  - **Widget Integration** (`/developer/widget`): Chatbot selector, theme picker, snippet generator

### Sprint 7: Deployment & Infrastructure [COMPLETED]
- Production Docker Compose (`docker-compose.prod.yml`): backend, frontend, nginx, celery_worker, celery_beat
- Nginx config with HTTPS, SSL termination, proxy for API, frontend, WebSocket
- Resource limits and reservations for production services
- Celery beat for scheduled analytics aggregation
- Frontend API proxy via Next.js rewrites

### Sprint 8: Testing & Documentation [COMPLETED]
- Alembic migration 0004 for Phase IV models (analytics_events, daily_analytics, system_config, webhooks)
- 62+ existing tests all passing
- Integration tests for Phase IV endpoints
- Widget SDK (Python & JavaScript) published

#### Additional Completed Features
- Webhook delivery system with retry logic and signature verification
- Knowledge source connectors: SQL, API, Git (extensible registry pattern)
- Multi-modal knowledge ingestion (PDF, Markdown, DOCX, TXT, Websites)
- Ollama local LLM support for embeddings and chat
- Pgvector fallback for embeddings (no external vector DB required)
- Structured JSON logging with trace_id, user_id, organization_id context
- Prometheus metrics endpoint ready for production monitoring
- Rate limiting per IP and per organization (configurable via settings)

### Sprint 9: Database-Level Row-Level Security (RLS) [COMPLETED]
- **Alembic migration 0006**: Enables RLS on all 13 organization-scoped tables (users, chatbots, policies, knowledge_sources, sessions, messages, api_keys, audit_logs, analytics_events, daily_analytics, llm_usage, webhooks)
- **Standard org-isolation policy**: All SELECT/INSERT/UPDATE/DELETE restricted to rows where `organization_id = current_setting('app.current_org_id')::uuid`
- **Messages table isolation**: Policy joins through sessions table to enforce org isolation
- **Platform admin bypass policy**: Separate policy allowing cross-org access when `app.is_platform_admin = 'true'` (narrowly scoped, not superuser)
- **Request lifecycle integration**: FastAPI dependency `get_db_with_org` runs `SET LOCAL app.current_org_id = :org_id` at start of each request, sourced from JWT `org_id` claim
- **Admin endpoints**: Use `get_db_admin` which sets `app.is_platform_admin = 'true'` for cross-org queries
- **Widget sessions**: Token includes `org_id` claim; widget message endpoint sets RLS context per session
- **JWT enhancement**: Access/refresh tokens now carry `org_id` claim for RLS context
- **Tests**: 15 tests covering app-level isolation (works on SQLite) and PostgreSQL RLS behavior (skipped on SQLite)
- **All 100 tests pass** (92 passing, 8 skipped PostgreSQL-only RLS tests)

### Sprint 10: HashiCorp Vault Secret Management [COMPLETED]
- **Vault service**: Added to docker-compose.yml (dev mode) and docker-compose.prod.yml (production file backend with auto-unseal support)
- **Vault client wrapper** (`app/core/secrets.py`): hvac-based client with KV v2 support, availability checking, and secret read/write/delete operations
- **SecretManager**: High-level wrapper that fetches from Vault with environment variable fallback for local development
  - Production: Vault required, fails fast if unavailable or secret missing
  - Development: Falls back to environment variables if Vault unreachable
  - Path convention: `secret/scout-io/<environment>/<key>` (e.g., `secret/scout-io/production/database_url`)
- **Config integration** (`app/core/config.py`): Settings class now populates all secret fields from SecretManager at initialization
  - Required secrets: database_url, redis_url, qdrant_url, qdrant_api_key, jwt_secret, celery_broker_url, celery_result_backend
  - Optional secrets: openai_api_key, anthropic_api_key, together_api_key, gemini_api_key, azure_openai_api_key, webhook_secret
- **Early initialization**: Secret manager initialized at module load in `app/main.py` with deployment environment detection
- **Documentation**: `.env.example` files updated to document Vault path convention and remove secret placeholders
- **Production setup guide**: `docs/operations/security-and-compliance.md` (Vault section) with step-by-step provisioning, initialization, unsealing, policy creation, AppRole auth, secret writing, and rotation procedures
- **All 92 tests pass** with env var fallback in test environment

### Sprint 11: Adversarial Security Testing & Hardening [COMPLETED]
- **Test suite** (`tests/security/test_prompt_injection.py`): 22 adversarial tests across 4 attack categories
  - System prompt extraction (4 tests): direct requests, roleplay, encoding, chain-of-thought
  - Policy bypass (4 tests): source_filter/content_filter override, instruction hierarchy, indirect injection via retrieved chunks
  - Cross-org data leakage (3 tests): direct queries, session extraction, knowledge source leaks
  - Sanitizer bypass (6 tests): provider/model name variations, secrets, encoded/partial/unusual formats
  - Response validator (3 tests): hallucination detection, safety validation
- **Fixes implemented**:
  - **System prompt hardening** (`app/core/memory/session_memory.py`): Explicit instruction hierarchy with 6 "NEVER VIOLATE" rules
  - **Post-generation safety filter** (`app/core/pipeline/response_pipeline.py`): `_check_post_generation_safety()` catches cross-org UUIDs, system prompt leaks, instruction override language
  - **Extended sanitizer patterns** (`app/core/validation/sanitizer.py`): 
    - Provider names with spaces/hyphens (`Open AI`, `Open-AI`)
    - Partial matches in compounds (`openai-compatible`, `gemini-powered`)
    - Secrets with unusual delimiters (`sk_abc`, `sk.abc`, `sk:abc`, `sk|abc`)
    - Model name variations (`GPT 4o`, `GPT4`, `Claude Opus`)
  - **Response validator enhancements** (`app/core/validation/response_validator.py`): Added patterns for prompt printing/revelation requests
- **Before/After Pass Rate**:
  - Baseline: 16/22 passed (72.7%) — 6 failures across sanitizer gaps, cross-org mock issues, validator param
  - After fixes: 22/22 passed (100%) — all adversarial tests now pass
- **Total test suite**: 114 tests passing (92 original + 22 security), 8 skipped (PostgreSQL-only RLS)

### Sprint 12: Tenant Dashboard (Chatbots, Knowledge Sources, Analytics) [COMPLETED]
- **Dashboard layout** (`frontend/src/components/DashboardLayout.tsx`): top nav + sidebar shared by all tenant pages under `/dashboard/`
- **Overview** (`/dashboard`): Live org info (`GET /organizations/me`) + org analytics (`GET /analytics/organization`), stat cards, quick actions
- **Settings** (`/dashboard/settings`): Organization rename via `PUT /organizations/me`
- **Chatbot management** (`/dashboard/chatbots`, `/chatbots/new`, `/chatbots/[id]`):
  - Create, rename, delete with confirmation modal
  - Model tier picker (fast/balanced/accurate) mapped to backend behaviour config
  - Knowledge source attach/detach per chatbot
  - Real policy form: source_filter → `allowed_source_ids`, content_filter → `blocked_terms`
  - Widget snippet preview + copy reusing `GET /developer/widget-snippet?theme=light|dark`
- **Knowledge sources** (`/dashboard/knowledge-sources`):
  - Aggregated list across all org chatbots with 5s polling (no websocket exists)
  - Add Source flow: website URL, file upload (PDF/Markdown/DOCX/TXT via `/uploads/{chatbot_id}`), and SQL/API/Git connectors with exact backend fields
  - Sync status badges (Synced/Failed/Syncing/Pending), retry button, delete confirmation warning it removes the source from every chatbot using it
  - Backend: new `POST /chatbots/{chatbot_id}/knowledge-sources/{source_id}/sync` dispatch endpoint (503 if Celery disabled); uploads `allowed_types` broadened for Markdown/DOCX/TXT
  - `frontend/src/lib/api.ts` rewritten: multipart `formData` support + `api.upload<T>()`
- **Analytics** (`/dashboard/analytics`): recharts page (installed; was not previously a dependency)
  - Date-range selector (7/30/90 days), message volume + sessions over time (composed chart)
  - Token usage over time broken out per chatbot (shown only when >1 chatbot)
  - Feedback summary card; latency/feedback fields exposed via daily endpoint
  - Admin-only knowledge source usage table (`GET /analytics/source/{source_id}`) gated on role from new `GET /auth/me`
  - Backend time-series endpoints (all org-scoped):
    - `GET /analytics/organization/daily?start_date&end_date` — daily rows for the caller's org
    - `GET /analytics/chatbot/{chatbot_id}/daily` — 404 unless chatbot belongs to caller's org
  - `GET /auth/me` added (referenced in developer docs but previously missing)
- **Cross-org isolation verified**: analytics tests confirm org A cannot read org B's daily or aggregate analytics (404), plus `/auth/me` test
- **Total test suite**: 124 passing (114 + 10 analytics/auth tests), 8 skipped (PostgreSQL-only RLS)

### Sprint 13: Plans & Billing (Razorpay Subscriptions) [COMPLETED]
- **Plan tiers** (`backend/app/core/billing/plans.py`): Free / Starter (₹2,999) / Growth (₹9,999) / Scale (₹29,999) with concrete limits per tier — chatbots allowed, monthly message volume, knowledge source count
- **Organization model + migration 0007**: added `plan`, `plan_status`, `razorpay_customer_id`, `razorpay_subscription_id` columns (indexed)
- **Razorpay integration** (`backend/app/core/billing/razorpay_client.py`):
  - `POST /organizations/me/billing/checkout-session` creates a Razorpay customer + subscription for the selected plan, returns the Razorpay-hosted checkout URL
  - `POST /webhooks/razorpay` handles `subscription.activated`, `subscription.charged`, `subscription.cancelled`, `subscription.halted`, updating org plan/status and writing audit log entries (`billing.plan_activated`, `plan_cancelled`, `plan_halted`, `subscription_charged`)
  - Every webhook verifies `X-Razorpay-Signature` (HMAC-SHA256 of the raw body, constant-time compare); unsigned/invalid payloads rejected
  - Org resolution from subscription `notes.organization_id` with fallback to stored `razorpay_subscription_id`
- **Plan limits enforced at API layer** (`backend/app/core/billing/limits.py`): chatbot create, knowledge source create, and widget message processing all reject past the plan limit with HTTP 402 + clear message; cancelled/halted orgs auto-downgrade to Free tier for enforcement
- **Keys via Vault**: `razorpay_key_id`, `razorpay_key_secret`, `razorpay_webhook_secret` pulled through the existing SecretManager (env fallback in dev); test-mode keys only, never hardcoded
- **Feature flag**: `billing_enabled` (`BILLING_ENABLED`, default `false`). Off in testing/dev — plan limits not enforced (no-op), checkout/webhook endpoints return 503, frontend billing page shows a "Billing is disabled in this environment" notice. Enable `BILLING_ENABLED=true` in production.
- **Frontend** (`/dashboard/billing`): current plan, usage vs limits cards, plan cards with Upgrade → redirect to Razorpay checkout (disabled when the flag is off)
- **Docs**: `docs/integrations/billing-razorpay.md` — tiers/limits, Vault key provisioning, webhook registration, feature flag, live-mode checklist (KYC note)
- **Tests**: 20 billing tests (checkout-session, signature rejection, all four webhook events, plan limit enforcement for chatbots/knowledge sources/messages, cancelled-downgrade, usage summary, disabled-flag 503 behavior)
- **Total test suite**: 145 passing (142 + 3 flag tests), 8 skipped (PostgreSQL-only RLS)

### Sprint 14: Usage-Based Billing (Token Overage via Celery Beat) [COMPLETED]
- **LLMUsage now actually written**: `ResponsePipeline` records an `LLMUsage` row after every AI generation (was previously never written — only read by analytics/admin). `AIRouter` captures provider-reported token counts (fallback to `count_tokens` estimate) + the model actually used (incl. fallback chain); estimated cost stored via new `pricing.py`
- **Pricing module** (`backend/app/core/billing/pricing.py`): per-model paise-per-1K input/output prices (`gpt-3.5-turbo`, `gpt-4o-mini`, `gpt-4o`, Claude, Gemini, Llama) with a medium default; `estimate_cost_paise`, `overage_amount_paise`, add-on batch cap (`MAX_OVERAGE_TOKENS_PER_ADDON`)
- **Plan usage component** (`plans.py`): each tier gains `included_monthly_tokens` (Free 100k / Starter 1M / Growth 5M / Scale 25M) and `overage_price_paise_per_1k` for paid tiers
- **`UsageBillingRecord` model + migration 0008**: unique per `organization_id` + `YYYY-MM` period; stores prompt/completion/total tokens, estimated cost (paise), overage tokens/cost, `reported_to_razorpay`, `razorpay_addon_id`
- **Celery beat task** (`backend/app/tasks/billing_tasks.py`, 03:00 UTC daily): per-org month aggregation, `UsageBillingRecord` upsert, Razorpay overage reporting, 80% soft-limit event, idempotent re-runs
- **Razorpay overage reporting** (`razorpay_client.create_addon`): Razorpay has no usage-metering API, so overage is charged as a subscription **add-on** on the next invoice (`subscription.createAddon`, verified against the SDK); graceful **fallback to internal tracking** (`reported_to_razorpay=false`) when there's no subscription, no overage price, or the API call fails
- **Soft-limit warning**: `billing.usage_soft_limit` AnalyticsEvent fired once per period at 80% of included tokens; surfaced by `usage_summary` (`warning`) and rendered as an orange banner on `/dashboard/billing`
- **Billing endpoint**: `GET /organizations/me/billing` now returns `usage_billing` (current month record) and `limits.included_monthly_tokens`
- **Frontend** (`/dashboard/billing`): warning banner, token usage card (used / included, overage + add-on vs invoice status)
- **Infra**: `celery_billing_beat` + `celery_billing_worker` compose services; worker app includes both `billing_tasks` and `analytics_tasks`
- **Docs**: `docs/integrations/billing-razorpay.md` — usage-based billing section (recording, aggregation, overage fallback, deployment)
- **Tests**: 16 new tests (pricing math + model matching, aggregation create/upsert, Razorpay add-on report + failure fallback + no-subscription skip, soft-limit once-per-period + below-threshold, endpoint warning/usage_billing surface, pipeline LLMUsage recording incl. provider-usage capture, no-db skip)
- **Total test suite**: 161 passing (145 + 16), 8 skipped (PostgreSQL-only RLS) — frontend build clean

### Sprint 15: Subscription Management on /dashboard/billing [COMPLETED]
- **Research**: Razorpay has no self-serve customer portal — confirmed against the SDK. The API surface for in-house flows is `subscription.edit` (change `plan_id` + `schedule_change_at`), `subscription.cancel` (body includes `cancel_at_cycle_end`), and `client.invoice.all({"subscription_id": ...})` for invoice history. SDK method signatures verified directly (`Subscription.cancel`/`edit` take `data` dicts; `Invoice.all(data)`)
- **Razorpay client** (`razorpay_client.py`): added `update_subscription(subscription_id, plan_id, schedule_change_at="now")`, `cancel_subscription(subscription_id, cancel_at_cycle_end=False)` (existing cancel signature preserved), and `list_subscription_invoices(subscription_id)` (newest first); existing `fetch_subscription` reused
- **Schemas** (`schemas/billing.py`): `SubscriptionDetail` (`has_subscription` flag, plan/status, `current_start`/`current_end`, `next_charge_on`, `payment_method`, `cancel_at_cycle_end`, invoice list), `InvoiceRead`, `ChangePlanRequest/Response`, `CancelSubscriptionRequest/Response`
- **New endpoints** (`billing.py`, all org-scoped, `_require_billing_enabled`):
  - `GET /organizations/me/billing/subscription` — returns `has_subscription=false` for new signups with no `razorpay_subscription_id` (frontend shows trial/free state, no errors); otherwise fetches the Razorpay subscription and maps `plan_id` back to the plan key via `_plan_for_razorpay`; invoice history is **best-effort** (list failure doesn't fail the detail view)
  - `POST /organizations/me/billing/subscription/change-plan` — validates plan + `schedule_change_at` ∈ {now, cycle_end}, calls `update_subscription`, reflects the new plan on the org immediately (Razorpay sends no plan-change webhook), audit log `billing.plan_changed`
  - `POST /organizations/me/billing/subscription/cancel` — calls `cancel_subscription`; default `cancel_at_cycle_end=true` keeps the org **active** (access until the paid period ends; webhook `subscription.cancelled` flips enforcement at cycle end), immediate cancel (`false`) flags `plan_status="cancelled"` right away, audit log `billing.plan_cancelled`
- **Frontend** (`/dashboard/billing`): current-plan card (name, price, renewal date, status incl. "cancelling at cycle end", payment method), invoice-history table, usage progress bars (tokens / chatbots / messages / knowledge sources vs plan limits with color shifts at 80% and over limit + overage cost notice), plan comparison grid with checkout-session upgrade flow for new subs and a "Switch (existing sub)" in-house change-plan flow (upgrade now / downgrade at cycle end), cancel-with-confirmation flow, and a clear **Trial / Free** state for orgs without a subscription. Warning banner + token card preserved
- **Tests**: 10 new (subscription detail no-subscription / with-invoices / invoice-failure best-effort, change-plan success + unknown/free plan + no-subscription, cancel at-cycle-end keeps active + immediate flags cancelled + no-subscription, 503 when disabled)
- **Total test suite**: 170 passing, 8 skipped (PostgreSQL-only RLS) — frontend build clean

### Sprint 16: CI/CD Pipeline & Branch Protection [COMPLETED]
- **Frontend test setup added**: no `npm test` existed despite the README claiming one — installed `vitest` (dev dep), added `test` (`vitest run`) and `typecheck` (`tsc --noEmit`) scripts, and a smoke test (`tests/smoke.test.ts`) covering the api client helpers and `fetchArray`. Removed the non-functional `next lint` script (no ESLint config exists in the repo) in favor of `tsc --noEmit` typechecking
- **Widget test setup added**: installed `vitest`, `jsdom`, `@testing-library/react` (dev deps), added `test` script, `vitest.config.ts` (jsdom env + `@` alias), `tests/setup.ts` (jsdom `matchMedia` stub), and a smoke test rendering `ThemeProvider` (`tests/smoke.test.tsx`); kept existing `lint` (`tsc --noEmit`)
- **CI workflow** (`.github/workflows/ci.yml`): on every PR, three parallel jobs that each fail the check on any failing step —
  - `Backend (pytest + syntax)`: full `python -m pytest tests/ -q` + `compileall` syntax check, Python 3.12 with pip cache keyed on `requirements.txt`
  - `Frontend (vitest + typecheck)`: `npm ci` → `npm test` → `npm run typecheck`, npm cache keyed on `package-lock.json`
  - `Widget (vitest + typecheck)`: `npm ci` → `npm test` → `npm run lint`, npm cache keyed on `package-lock.json`
- **Build workflow** (`.github/workflows/build.yml`): on push to `main` (after merge), builds and pushes `backend` / `frontend` / `widget` images to GitHub Container Registry (GHCR) tagged with the commit SHA + `latest`; Docker Buildx + `type=gha` layer caching per service; GHCR login via `GITHUB_TOKEN` (`packages: write`); image namespace lowercased for GHCR
- **Branch protection**: `docs/operations/staging-deployment.md` (CI/CD section) documents the two workflows, the required-status-check settings for `main` (the three CI job names), and notes the only secrets needed are the built-in `GITHUB_TOKEN`
- **No staging/prod deploys**: `deploy-staging.yml` intentionally not created — staging env (4.2: docker-compose.staging.yml, host, docs/operations/staging-deployment.md) doesn't exist yet; production deploys stay manual/gated. Backup & DR (the Sprint 6 prerequisite) is now in place (Sprint 21: nightly S3 backups + restore runbook, `docs/operations/disaster-recovery.md`), so an approval-gated production deploy workflow can now be added
- **Verification**: 3 frontend + 2 widget vitest tests pass, both typechecks clean, frontend `next build` clean, backend pytest sanity passes; workflows validated as parseable YAML

### Sprint 17: Staging Environment + Dockerignore [COMPLETED]
- **`.dockerignore` files** added to `backend/`, `frontend/`, and `widget/` (per build context), excluding `.git`, `.env*` (keeping `.env.example`), `node_modules`, `.next`/`dist` build artifacts, `__pycache__`/`.venv`/`*.py[cod]`, test directories, and `docs`. Build context sizes verified with `docker build --progress=plain`:
  - `backend`: 2.12MB → **24.00kB**
  - `frontend`: 461.52MB → **384.03kB**
  - `widget`: 104.01MB → **141.28kB**
  - All three images built clean and test images removed after verification
- **`docker-compose.staging.yml`**: based on `docker-compose.prod.yml` but fully self-contained — separate Postgres (`scout_staging` DB), Redis, Qdrant, and Vault instances with `staging_*` volumes so staging never touches production data. Backend runs `DEPLOYMENT_ENV=staging` (secrets from `secret/scout-io/staging/*` with env-var fallbacks since Vault isn't required for staging), `BILLING_ENABLED=true` against Razorpay test keys, GHCR image names (`ghcr.io/<namespace>/backend|frontend:latest|sha`) with source `build:` fallback. Celery worker/billing/beat services included. Nginx mounts the staging vhost; host ports default `8080`/`8443` so it can coexist with production
- **`docker/nginx/nginx.staging.conf`**: staging-only virtual host (`staging.scout.io`), 80→443 redirect + TLS from `./nginx/ssl`, same proxy paths as prod (`/api/`, `/ws`, `/health`, `/docs`, `/redoc`, `/openapi.json`, `/`)
- **Frontend Dockerfile**: now accepts `NEXT_PUBLIC_API_URL` / `NEXT_PUBLIC_WS_URL` as build args so the staging image is compiled against the staging API/WS URLs instead of localhost
- **`docs/operations/staging-deployment.md`**: end-to-end deploy (host provisioning, `docker/.env`, TLS certs, staging Vault secret provisioning incl. Razorpay test keys, `pull`/`up -d`, migrations) plus **reset/seed procedure** (`down -v --remove-orphans` wipes all `staging_*` volumes → re-up → `alembic upgrade head` → `scripts/seed_test_data.py`) and isolation guarantees
- **Compose validation**: `docker compose -f docker-compose.staging.yml config` passes (also fixed a latent malformed `depends_on` list+condition mix present in prod.yml)

### Sprint 18: Observability — Metrics, Logs & Alerting [COMPLETED]
- **Backend instrumentation** (`app/core/metrics.py` + `prometheus-client` added to `backend/requirements.txt`): Prometheus text-format `/metrics` endpoint with `scout_http_requests_total` (method/path/status counter), `scout_http_request_duration_seconds` (histogram), `scout_celery_tasks_total` (task/state, via Celery `task_success`/`task_failure` signals + `register_celery_metrics()` in `embedding_tasks`, `analytics_tasks`, `billing_tasks`), `scout_celery_queue_depth` (gauge, 15s background sampler), `scout_dependency_health` (gauge reusing the shared `check_dependencies()` from the new `app/core/health.py`, now also used by `/health/ready`), and `scout_llm_fallback_triggers_total` (primary→fallback model, incremented in `app/core/ai/router.py`)
- **MetricsMiddleware** (outermost, runs after tracing so `trace_id` is populated): records every request except `/metrics`, `/health`, `/health/ready`; route paths resolved to templates (`/organizations/me/{org}`-style) so metric cardinality stays bounded; emits a `scout.request` JSON log line with `trace_id`, `method`, `path`, `status`, `duration_ms`, and a `grafana_link`
- **Trace-id → Grafana deep-link pattern**: `grafana_log_link(trace_id)` builds a Loki Explore URL (`{job="scout-backend"} |= "trace_id": "<id>"`) defaulting to `http://grafana:3000` (configurable via `GRAFANA_BASE_URL` / `grafana_base_url` setting). Logged on every request so an on-call engineer jumps from an alert → dashboard → trace-scoped logs
- **Observability stack** added to `docker/docker-compose.prod.yml` (and `staging`): prometheus (v2.53.0, 30d retention, scrapes `backend:8000/metrics` + itself), grafana (11.1.0, host port **3001**, provisioned datasources + dashboards, admin creds via env), loki (3.1.0, 30d retention), promtail (3.1.0, `docker_sd_configs` over `/var/run/docker.sock`, scrapes containers labelled `logging=promtail` — added to backend/frontend/celery services), alertmanager (v0.27.0). Also fixed the latent malformed `depends_on` in prod.yml (same bug Sprint 17 fixed in staging)
- **Prometheus alert rules** (`docker/prometheus/alerts.yml`, validated with `promtool check config` — SUCCESS, 5 rules): `APIErrorRateHigh` (per-endpoint 5xx > 5%, critical, 5m), `DependencyDown` (`scout_dependency_health == 0` for 2m, critical — same logic as `/health/ready`), `CeleryQueueGrowing` (`increase(…[10m]) > 0` and depth > 10, warning), `CeleryTaskFailureRateHigh` (>20% failing over 15m, warning), `LLMFallbackRateHigh` (fallbacks > 10% of requests, warning)
- **Alertmanager → Slack** (`docker/alertmanager/alertmanager.yml` + `template.tmpl`): routes each alert class to Slack `#alerts` with title/text templates + Grafana dashboard links from alert annotations; webhook injected via `SLACK_WEBHOOK_URL` → written to `slack_api_url_file` at startup (Alertmanager does **not** expand `${VAR}` in config — confirmed empirically); PagerDuty swap documented (same receiver-chain pattern)
- **Grafana provisioning** (`docker/grafana/provisioning/datasources` + 4 dashboards with fixed UIDs matching the alert links): Scout Requests (`scout-requests`: RPS/endpoint, status mix, p50/p95, 5xx rate), Scout Celery (`scout-celery`: queue depth, growth, task failure rate), Scout Dependency Health (`scout-dependencies`: UP/DOWN per service), Scout LLM Providers (`scout-llm`: fallback rate/share)
- **Config validation**: prometheus + 5 rules OK (`promtool`), alertmanager config loads cleanly with the webhook file, loki starts and listens on 3100, promtail config parses (`-dry-run`), `docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile full config` passes
- **Docs**: `docs/operations/monitoring-observability.md` — stack overview, data flow, the trace_id→Grafana link pattern (with example JSON log), alert rules table, Slack setup, PagerDuty swap, dashboard list, validation commands
- **Tests**: full suite re-run after instrumentation — **171 passing, 8 skipped**; `/metrics` endpoint verified live (200, all metric families present, counter incremented on real requests, `X-Trace-ID` header set)

### Sprint 19: Load-Testing Suite [COMPLETED]
- **Backend load-test hooks**: `mock_llm` setting (`MOCK_LLM=true`) added to `app/core/config.py`; `AIRouter.generate()` returns a deterministic `_mock_generate` reply (120 ms sleep, no provider call) and `EmbeddingService` returns hash-seeded pseudo-vectors of the configured dimension, so the full pipeline runs against real infra at zero API cost
- **Per-stage pipeline timing**: `ResponsePipeline.run()` now returns a `timings` dict (cache_lookup, knowledge_cache_lookup, retrieval, knowledge_cache_write, context_build, session_memory, llm_generate, validation, safety, postprocess, total); the widget endpoint exposes it via an `X-Pipeline-Timings` JSON response header
- **Per-org rate limiting wired** (was configured but never applied): new `app/core/rate_limit.py` (`limiter` + `widget_org_key` extracting org_id from the widget JWT, IP fallback); `@limiter.limit(...)` applied to `POST /api/v1/widget/messages` so one org's burst can't starve another
- **Tests** (`tests/test_load_hooks.py`): timings header shape, mock-LLM never calls provider, per-org 429 at a forced low limit, and cross-org independence (org A capped while org B still succeeds). Full suite now **175 passing, 8 skipped**
- **`load-tests/` suite** (Locust): `requirements.txt`, `README.md`, `common.py` (seed-state loading, X-Pipeline-Timings parsing, per-stage Locust events, bursty/normal org pool split), `seed.py` (creates orgs/users/chatbots/widget sessions/knowledge sources + pre-minted JWTs directly in the backend DB, writes `seed_state.json`), `widget_chat_locustfile.py` (multi-org concurrent chat, bursty-vs-normal starvation scenario, 1x→10x `LoadTestShape` ramp, per-stage percentile capture), `ingestion_locustfile.py` (create source → dispatch sync → poll to completion)
- **Verified end-to-end** against local Docker infra (Postgres 16, Redis 7, Qdrant) with `MOCK_LLM=true` and a real Celery worker: widget smoke at ~72 users shows server-side pipeline p95 ≈ 200 ms (dominated by the ~120 ms mock LLM) while client-observed p95 ≈ 31 s — **first bottleneck is the single uvicorn worker threadpool**, not the pipeline, Postgres pool, or Qdrant; ingestion smoke (6 users, worker concurrency 2) ran 38 create/dispatch cycles + 126 polls with **0 failures** and all sources `completed`
- **Migration fix**: `alembic/versions/0006_rls_policies.py` `upgrade()` created a `messages` RLS policy referencing a non-existent `organization_id` column then created a duplicate policy — now skips `messages` in the generic loop (no org column; handled by `_create_messages_rls`); fresh `alembic upgrade head` verified against a clean DB
- **Docs**: `docs/operations/monitoring-observability.md` (load-testing report section: methodology, per-stage p50/p95 tables, starvation result, ingestion throughput, first-bottleneck analysis + scaling recommendations: scale API workers first, then Postgres pool, then Celery concurrency) and `load-tests/README.md` (seed + run instructions)

### Sprint 20: Cross-Encoder Reranking Service [COMPLETED]
- **`services/reranker/`** standalone FastAPI service: `POST /rerank` (body `{query, chunks[{id,text,score}], top_k}` → reordered `results` with `rerank_score`, plus `elapsed_ms`), `GET /health`, `GET /ready`; loads `cross-encoder/ms-marco-MiniLM-L-6-v2` (CPU) lazily and warms on startup; `Dockerfile` (python:3.11-slim, port 8082, `/ready` healthcheck), `requirements.txt`, `.dockerignore`
- **`docker/docker-compose.yml`**: `reranker` service added under the `full` profile with resource limits (`cpus: 2`, `memory: 2g`, reservation `1g`), env `RERANKER_MODEL` / `RERANKER_DEVICE=cpu`
- **Backend integration** (`app/core/knowledge/reranker.py`): `RerankerClient` (httpx POST, timeout, retry, `RerankerUnavailable` on failure/5xx) + new settings `reranker_enabled=False`, `reranker_url=http://reranker:8082`, `reranker_timeout_ms=2000`, `reranker_retries=1`, `reranker_max_candidates=10`; `KnowledgeEngine._rerank()` re-ranks up to `max(top_k, reranker_max_candidates)` Qdrant results after `search()` and before context building, re-merging metadata by id and replacing `score` with `rerank_score`
- **Feature flag / disable-without-redeploy**: global `reranker_enabled` config (off by default, opt-in like `pgvector_enabled`/`mock_llm`); per-chatbot override via `chatbot.config["reranker_enabled"]` threaded through `ResponsePipeline.run()` (new `reranker_enabled` param) from `widget_api.py` and `developer.py`, and through the `retrieval.py` debug endpoint; per-chatbot toggles take effect per-request, no redeploy
- **Graceful fallback**: any reranker failure (unreachable/timeout/5xx/malformed response) logs a warning, increments the new `scout_reranker_fallback_triggers_total` counter, and returns Qdrant's original similarity ordering — a reranker outage degrades to single-stage retrieval, never errors the request (existing "degrade, never fail" philosophy)
- **Tests**: `services/reranker/tests/test_main.py` (5, mocked encoder — health, reorder, top_k, empty validation, ready) + `backend/tests/test_reranker.py` (10: client retry/reorder/error, engine rerank/merge/flag control/fallback paths); fixed `QdrantStore.ensure_collection()` to catch `ValueError` too (in-process/local Qdrant clients raise it for missing collections, not just `UnexpectedResponse`). Full backend suite **185 passing, 8 skipped**
- **Precision measurement** (`backend/scripts/eval_reranker.py`): constructed 36-chunk product/support KB + 36 paraphrased queries with ground truth; real embeddings (`all-MiniLM-L6-v2`) via a local `EmbeddingService`-compatible stand-in and in-process Qdrant, reranker run against the real service. MRR@K 0.431→0.458, nDCG@3 0.417→0.463, nDCG@5 0.439→0.463. Key finding: dominant failure mode is **recall** (relevant chunk absent from candidate pool), which reranking can't fix — widening `reranker_max_candidates` is the first lever for further gains
- **Docs**: `docs/integrations/vector-db-qdrant.md` (components, feature flags, fallback behaviour, precision table + findings, run instructions)

---

### Sprint 21: Backup & Disaster Recovery [COMPLETED]
- **Nightly backup container** (`docker/backup/`, image `scout-backup`): runs on a cron schedule (default 03:00 UTC, `CRON_SCHEDULE`) inside the compose project network; `backup.sh` does `pg_dump -Fc` (Postgres over TCP) + Qdrant snapshot via REST (`POST /collections/{name}/snapshots`, then downloads it), uploads both to S3-compatible object storage via AWS CLI v2 (`S3_ENDPOINT`); base image `postgres:16-alpine` + aws-cli + curl + docker-cli + docker-cli-compose; `BACKUP_ON_START` (default true) runs one backup at container start
- **Object layout & retention**: `scout-backups/<prefix>/daily/<STAMP>/postgres.dump` + `qdrant.snapshot` (STAMP=`YYYYMMDDTHHMMSSZ`); weekly copy under `weekly/<YEAR>/W<week>/` on Sundays; pruning by object mtime (daily 30 days, weekly 90 days). No S3 provider existed in the repo, so integration assumes any S3-compatible endpoint (validated against local MinIO); provider choice documented as an assumption in the runbook
- **`docker/docker-compose.prod.yml`**: `backup` service added (profile `full`, S3/POSTGRES/QDRANT env, depends_on postgres healthy + qdrant started, restart always)
- **Restore** (`docker/backup/restore.sh` + `scripts/restore.sh` host wrapper): resolves `--latest` or `--timestamp <STAMP>`, downloads objects, stops/removes stack and **wipes `postgres_data` + `qdrant_data` volumes** (keeps compose network alive since the restore container is attached to it — deliberately not `compose down`), starts postgres+qdrant, `pg_restore --clean --no-owner`, then Qdrant snapshot recovery. Key Qdrant API discoveries that make recovery work: it is **`PUT /collections/{c}/snapshots/recover`** (not POST), the snapshot file must live under the container's **`/qdrant/snapshots`** dir (not storage), and recovery **refuses to overwrite an existing collection** — delete the target collection first. `COMPOSE_FILE` accepts a space-separated `-f` list so layered stacks (base `docker-compose.yml` + prod overlay) can be restored; the `scripts/restore.sh` wrapper defaults to the production base+prod layered stack
- **Alembic handling**: restore runs `alembic upgrade head` (applies any migrations newer than the backup) only when the compose file has a `backend` service — skipped in scratch/DR test environments
- **Validated end-to-end** against `docker/docker-compose.scratch.yml` (Postgres + Qdrant + MinIO + backup, project `scouttest`): seeded 3 orgs/3 messages + 3-point Qdrant collection, ran a real backup, tore everything down, restored from `--latest`, and verified — Postgres orgs=3/msgs=3, Qdrant points_count=3 with identical payloads, and a search smoke test returns the right doc at score 1.0. **Measured RTO ≈ 22 s** (download → wipe → pg_restore → qdrant recover → full stack up)
- **Docs**: `docs/operations/disaster-recovery.md` runbook (architecture, exact volume locations from compose files, incident procedure, verification steps, expected RTO/RPO, reproducible scratch-env DR test procedure)

### Sprint 22: Org Offboarding (Permanent Data Deletion) [COMPLETED]
- **Two-step confirmation flow** (platform-admin only): `POST /admin/organizations/{org_id}/offboard` returns a deletion **preview** (per-table Postgres counts, Qdrant/pgvector points, Redis cache counts, upload files/bytes) + a signed **confirmation token** (JWT `type=offboard_confirm`, bound to org+admin, 15 min TTL, deletes nothing); `POST /admin/organizations/{org_id}/offboard/confirm` with the token verifies it and executes the purge, returning a completion report
- **Postgres purge** (`app/domain/offboarding/service.py`): deletes every org-scoped row in FK-safe child-before-parent order — `messages` (via session subquery), `analytics_events`, `daily_analytics`, `llm_usage`, `knowledge_sources`, `policies`, `sessions`, `chatbots`, `api_keys`, `audit_logs` (org-scoped), `webhooks`, `usage_billing_records`, `users`, then the `organizations` row; raw-SQL UUID params are dialect-aware (dashed on Postgres, hex on SQLite so tests pass)
- **Vector purge**: `count_organization_chunks`/`delete_organization_chunks` on Qdrant collection (payload `organization_id` filter) and pgvector fallback rows when enabled
- **Redis purge**: org memory (`org_config:*`/`org_policies:*`), session history keys collected from DB first, knowledge cache (`knowledge_cache:*` scanned + payload-matched on org id), and the `opt_cache:*` namespace evicted wholesale (md5-hashed keys, no org marker, short TTL — rationale in code)
- **Uploads purge**: `shutil.rmtree(UPLOAD_DIR/<org_id>/)` with file/byte counts
- **Audit-log retention decision (documented in `docs/operations/security-and-compliance.md`, Offboarding section)**: org-scoped audit logs ARE purged (org data), but the offboarding op is written first as a platform-level proof (`organization_id`/`user_id` NULL, ids in `details`) that survives the purge as immutable proof; `usage_billing_records` are deleted too (NOT NULL FK to organizations blocks retaining), so financial settlement must precede offboarding
- **Tests**: `backend/tests/test_offboarding.py` — 10 tests (service purge of every table, audit-proof survival, qdrant/redis/uploads mocks, preview-without-delete, token roundtrip/rejection, two-step endpoint flow, non-admin 403). Full suite: **195 passed, 8 skipped** (up from 185/8)

### Sprint 23: TOTP Multi-Factor Authentication [COMPLETED]
- **User model**: `totp_secret` (Fernet-encrypted at rest), `mfa_enabled`, `recovery_codes` (bcrypt-hashed JSON list) columns; alembic migration 0009. Encryption key is SHA-256-derived from `jwt_secret` (no new Vault secret to provision)
- **`app/core/security/totp.py`**: pyotp secret generation, `otpauth://` provisioning URI, server-side QR as base64 PNG data URI (`qrcode` lib), Fernet encrypt/decrypt, one-time recovery-code generation/hashing/verification (format `XXXX-XXXX-XXXX-XXXX`, normalized on input)
- **Endpoints** (`/auth/mfa/*`, new `app/api/endpoints/mfa.py`): `GET /status`; `POST /setup` (password-gated, returns secret + URI + QR); `POST /enable` (verifies a first TOTP code, persists encrypted secret + hashed recovery codes, returns plaintext codes once); `POST /disable` (password + TOTP/recovery code, clears MFA); `POST /recovery-codes/regenerate` (rotates codes); `POST /verify-login` (completes login for MFA users)
- **Login flow**: for `mfa_enabled` users, `POST /auth/login` now returns `{mfa_required: true, mfa_token}` (short-lived JWT `type=mfa_verify`) instead of tokens; `/auth/mfa/verify-login` consumes the token plus a TOTP/recovery code and issues real access+refresh tokens. Recovery codes are single-use (consumed on use)
- **Platform-admin enforcement**: `require_platform_admin` returns 403 ("MFA must be enabled...") for `platform_admin` accounts without MFA, making it mandatory for the `/admin` portal; regular org admins get a recommended-but-optional dashboard Settings UI. Widget session auth (`type=widget` JWT from `/widgets/sessions`) is untouched and never requires MFA
- **Frontend**: `auth/login.tsx` adds a verification-code step after password when MFA is required; `dashboard/settings.tsx` adds a Two-Factor Authentication card (QR + manual key, enable with code, one-time recovery-code display, disable + regenerate with password/code confirmation)
- **Tests**: `backend/tests/test_mfa.py` (15 tests: status, setup password gate, secret/QR shape, encrypted-at-rest persistence, enable wrong-code, login verify step, TOTP + recovery-code login, single-use recovery codes, disable, regenerate invalidation, platform-admin gating before/after enable). Existing platform-admin tests updated to seed MFA and complete the two-step login. Full backend suite: **210 passed, 8 skipped** (up from 195/8); frontend typecheck + 3 vitest tests pass

### Sprint 24: Beta Onboarding Instrumentation & Feedback [COMPLETED]
- **Onboarding checklist** (`GET /analytics/onboarding`, new `app/api/endpoints/onboarding.py`): four steps computed from live org state — create first chatbot, add first knowledge source, test the widget (any ChatSession), invite a teammate (>=2 users). Newly completed steps are recorded once as `AnalyticsEvent` `onboarding.step` (payload `{step, label}`), idempotent across repeat calls, so the funnel reflects real drop-off even if a user never revisits the dashboard
- **In-dashboard feedback widget** (`POST /analytics/feedback`, `FeedbackCreate` schema): thumbs up/down + optional text stored as `AnalyticsEvent` `feedback` (payload `{rating, message, context}`, plus chatbot_id/source_id columns). Frontend `components/FeedbackWidget.tsx` surfaced in the developer page after a successful chatbot test (`context=chatbot_test`) and on the knowledge-sources page the first time a source reaches `sync_status=completed` (`context=source_sync`, prompted once per source via sessionStorage)
- **Dashboard overview** (`dashboard/index.tsx`): "Get started" checklist card links each step to the relevant page, hides once all four are complete
- **Admin-only funnel view** (`GET /admin/onboarding/funnel`, platform-admin gated via `require_platform_admin` + `get_db_admin`): per-org current-state funnel (chatbot/source/widget-session/teammate booleans + recorded steps + created_at) plus summary counts and all feedback submissions across every org. `frontend/pages/admin/onboarding.tsx` renders summary cards + two tables; nav item added to `AdminLayout`. Cross-org visibility stays tenant-isolated (RLS untouched) and admin-only
- **Tests**: `backend/tests/test_onboarding.py` (6 tests: empty checklist, event recording once across repeat calls, feedback submission + validation, funnel 403 for non-admin, cross-org funnel/summary/feedback). Full backend suite: **216 passed, 8 skipped** (up from 210/8); frontend typecheck + 3 vitest tests pass

---

## Phase V: In Progress / Planned
- Advanced cost tracking and budget alerts per organization/chatbot (plan tiers/billing + usage-based overage + subscription management done in Sprints 13–15; feature-flagged)
- CI/CD: PR CI + GHCR image builds done in Sprint 16; staging compose/docs done in Sprint 17; deploy-staging.yml and approval-gated production deploy not yet wired
- Performance optimization: incremental sync, intelligent caching improvements
- SDK generation for Python, JavaScript, Go (Python/JS done)
- Real-time analytics dashboard updates (WebSocket-based; static/date-range charts done in Sprint 12)
- Custom model fine-tuning integration
- Multi-region deployment support
- Horizontal scaling for Celery workers
- Plugin/extension system for custom knowledge connectors

---

## Product requirements document (merged)

> The following section was merged from `docs/PRD.md`.

# PRODUCT REQUIREMENTS DOCUMENT (PRD) 

## Project Information 

|Field|Value|
|---|---|
|Project Name|Scout.io|
|Product Type<br>|AI Knowledge Infrastructure<br>Platform|
|Primary Ofering|Organization-centric AI Chatbot<br>Infrastructure|
|MVP Focus|Website-based AI Chatbots|
|Architecture|Multi-tenant & Modular<br>|
|Deployment Strategy|Cloud-frst with Hybrid Deployment<br>Readiness|
|Target Users|Organizations, Developers and<br>Customers|



## Problem Statement 

Modern businesses are increasingly establishing their digital presence through websites and web applications to provide information, services, and support to their customers. However, most organizations encounter one or more of the following challenges while attempting to provide intelligent customer interactions. 

### Existing Challenges 

#### _Challenge 1: High Development Complexity_ 

Building intelligent chatbot systems requires organizations to manage: 

- AI integrations 

- Multiple LLM providers 

- Knowledge management 

- Data synchronization 

- Response validations 

- Session management 

- Security configurations 

- Analytics infrastructure 

This significantly increases development complexity and maintenance overhead. 

_Challenge 2: Vendor Lock-in_ 

Many existing chatbot solutions tightly couple organizations with: 

- Specific AI providers 

- Specific cloud providers 

- Proprietary infrastructures 

- Closed ecosystems 

Organizations often lose flexibility once integrations are completed. 

#### _Challenge 3: Knowledge Management Challenges_ 

Organizations possess information distributed across multiple sources such as: 

- Websites 

- Documentation 

- Databases 

- APIs 

- Knowledge repositories 

- Frequently Asked Questions 

Managing and synchronizing this information while maintaining consistency becomes increasingly difficult. 

_Challenge 4: Limited Configurability_ 

Most chatbot solutions provide limited control over: 

- Response behaviours 

- Security policies 

- Session management 

- Data retention 

- Knowledge constraints 

- AI configurations 

Organizations require significantly greater flexibility without increasing engineering complexity. 

_Challenge 5: Data Ownership Concerns_ 

Organizations often hesitate to: 

- Share confidential information. 

- Migrate their complete databases. 

- Store proprietary knowledge externally. 

Maintaining ownership and control over organizational knowledge remains an important concern. 

#### _Challenge 6: Reliability Issues_ 

AI systems frequently suffer from: 

- Hallucinations 

- Provider failures 

- Knowledge inconsistencies 

- Service interruptions 

- Poor response validation mechanisms 

Organizations require intelligent fallback mechanisms and graceful degradation strategies. 

## Proposed Solution 

Scout.io addresses these challenges by providing an organization-centric AI infrastructure platform that enables organizations to securely expose their knowledge through configurable chatbot experiences. 

Scout.io provides: 

- Multi-chatbot management. 

- Multiple knowledge source support. 

- Intelligent AI routing. 

- Multi-provider support. 

- Response validation mechanisms. 

- Synchronization workflows. 

- Configurable response behaviours. 

- Hybrid deployment capabilities. 

- Graceful degradation mechanisms. 

- Organization-level data ownership. 

Organizations are provided with intelligent abstractions rather than implementation complexities. 

## Product Vision 

To become an extensible, secure, configurable, and provider-independent AI Knowledge Infrastructure Platform that enables organizations to intelligently expose their knowledge through AI-powered experiences. 

Scout.io prioritizes: 

- Security 

- Stability 

- Scalability 

- Maintainability 

- Flexibility 

- Simplicity 

Website chatbots represent the first capability offered by the platform and not the final destination of the product. 

## Product Goals 

### Primary Goals 

- Reduce chatbot development complexity. 

- Provide provider-independent AI infrastructures. 

- Enable multiple chatbot management. 

- Maintain organization-level data ownership. 

- Ensure configurable AI behaviours. 

- Provide production-grade reliability. 

### Secondary Goals 

- Minimize engineering efforts for organizations. 

- Support multiple deployment models. 

- Maintain long-term extensibility. 

- Enable intelligent AI orchestration. 

- Preserve architectural simplicity. 

## Stakeholders 

### Platform Administrators 

Responsibilities include: 

- Platform management. 

- Infrastructure maintenance. 

- System monitoring. 

- Tenant management. 

- Security management. 

### Organizations 

Responsibilities include: 

- Creating chatbots. 

- Managing configurations. 

- Managing knowledge sources. 

- Defining chatbot policies. 

- Managing analytics. 

### Developers 

Responsibilities include: 

- Widget integrations. 

- API integrations. 

- Dashboard configurations. 

- Future SDK integrations. 

### Customers 

Responsibilities include: 

- Chatbot interactions. 

- Feedback submissions. 

- Session participation. 

Customers will never have access to: 

- AI providers. 

- Internal configurations. 

- Knowledge metadata. 

- Organizational policies. 

- Response generation workflows. 

## Functional Requirements 

### Organization Management 

Organizations should be able to: 

- Create accounts. 

- Manage chatbots. 

- Configure policies. 

- Configure response behaviours. 

- Manage sessions. 

- Manage analytics. 

### Chatbot Management 

Organizations should be able to: 

- Create multiple chatbots. 

- Configure chatbot behaviours. 

- Configure storage policies. 

- Configure synchronization mechanisms. 

- Configure AI policies. 

Each chatbot should remain independently configurable. 

### Knowledge Source Management 

Organizations should be able to connect: 

- Websites 

- Documents 

- APIs 

- Databases 

- Code repositories 

- Future integrations 

Organizations should remain the owners of their knowledge sources. 

### AI Management 

Organizations should be able to configure: 

- Fast mode 

- Balanced mode 

- High Accuracy mode 

- Cost Efficient mode 

- Custom behaviours 

Organizations will configure behaviours rather than AI providers. 

Model selection remains the responsibility of Scout.io. 

### Session Management 

Organizations should be able to configure: 

- Session retention policies. 

- Storage durations. 

- Session analytics. 

- Customer interaction policies. 

Examples include: 

- No storage 

- Seven days 

- Thirty days 

- Ninety days 

- Custom configurations 

### Analytics Management 

Organizations should be be able to monitor: 

- Response statistics. 

- Session statistics. 

- Performance statistics. 

- Token utilization. 

- Synchronization statistics. 

- Feedback statistics. 

Optional analytics may include: 

- Confidence scores. 

- Retrieved contexts. 

- Source mappings. 

 Validation statistics. 

### Response Policies 

Organizations should be able to configure: 

#### _Strict Mode_ 

- Source-only responses. 

#### _Balanced Mode_ 

- Configurable general knowledge support. 

#### _Creative Mode_ 

- Broader AI utilization. 

_Custom Mode_ 

Organizations determine: 

- Allowed domains. 

- Restricted domains. 

- Behaviour policies. 

- Security policies. 

## Non-Functional Requirements 

Scout.io must satisfy the following requirements. 

### Security Requirements 

The platform must: 

- Enforce organization-level isolation. 

- Prevent unauthorized access. 

- Prevent confidential information leakage. 

- Validate generated responses. 

- Secure organizational configurations. 

### Performance Requirements 

The platform should: 

- Maintain low response latency. 

- Efficiently manage synchronization workflows. 

- Optimize token utilization. 

 Support concurrent chatbot sessions. 

### Scalability Requirements 

The platform must support: 

- Multiple organizations. 

- Multiple chatbots. 

- Horizontal scaling. 

- Hybrid deployments. 

- Future distributed architectures. 

### Maintainability Requirements 

The architecture must remain: 

- Modular. 

- Extensible. 

- Provider-independent. 

- Contributor friendly. 

## Response Workflow Requirements 

Every response must pass through: 

Question 

| Intent Detection 

| Policy Validation 

| Security Validation 

- | Knowledge Retrieval 

| Context Optimization 

- | AI Routing 

- | Response Generation 

- | 

Response Validation 

| Response Sanitization 

| 

Analytics Logging 

| Final Response 

No response should bypass this workflow. 

## AI Requirements 

The platform must support: 

- Multiple LLM providers. 

- Open-source fallback models. 

- Intelligent routing mechanisms. 

- Provider abstractions. 

- Future provider integrations. 

Customers must never know: 

- Which model generated responses. 

- Which provider was utilized. 

- Internal response generation workflows. 

## Knowledge Requirements 

The platform must support: 

- Multiple knowledge sources. 

- Synchronization mechanisms. 

- Embedding management. 

- Context retrieval. 

- Future knowledge integrations. 

Knowledge management should remain configurable and extensible. 

## Deployment Requirements 

The MVP must support: 

- Website integrations. 

- Cloud deployments. 

- Containerized environments. 

Future support includes: 

- Self-hosted deployments. 

- Hybrid deployments. 

- Enterprise deployments. 

## Fallback Requirements 

Scout.io must implement graceful degradation mechanisms. 

Examples include: 

Primary Provider | Failure | Secondary Provider | Failure | Scout Open Models | Failure | Graceful Response 

Examples of graceful responses include: 

- Service unavailable notifications. 

- Alternative responses. 

- Retry mechanisms. 

## Open-source Philosophy 

Scout.io intentionally adopts existing and battle-tested open-source ecosystems whenever feasible. 

Examples include: 

- AI abstractions 

- Knowledge retrieval systems 

- Synchronization frameworks 

- Monitoring solutions 

- Authentication systems 

Engineering efforts should primarily focus upon solving problems unique to Scout.io rather than rebuilding mature infrastructures. 

## MVP Scope 

The MVP includes: 

- Multi-tenant architecture. 

- Multiple chatbot support. 

- Website integrations. 

- Multiple knowledge sources. 

- Organization dashboards. 

- Session management. 

- Analytics. 

- AI routing mechanisms. 

- Response validations. 

- Synchronization workflows. 

- Open-source fallback models. 

- Configurable response policies. 

- Hybrid deployment readiness. 

## Future Scope 

Future capabilities include: 

- Voice interfaces. 

- Multi-modal support. 

- Enterprise integrations. 

- Agentic workflows. 

- Mobile SDKs. 

- White-label deployments. 

- Multi-language capabilities. 

- Advanced analytics. 

- GPU deployments. 

- Distributed architectures. 

Future capabilities should extend existing architectural boundaries without introducing breaking changes. 

## Success Metrics 

The MVP shall be considered successful if it satisfies the following objectives: 

### Product Metrics 

- Reliable chatbot responses. 

- Stable synchronization workflows. 

- Configurable organizational policies. 

- Successful multi-provider integrations. 

- Graceful degradation support. 

### Technical Metrics 

- High system availability. 

- Efficient response generation. 

- Reliable fallback mechanisms. 

- Organization-level isolation. 

- Maintainable codebases. 

### User Metrics 

Organizations should be able to: 

- Configure chatbots without implementation complexity. 

- Manage knowledge sources efficiently. 

- Maintain ownership of their organizational data. 

- Deploy intelligent chatbot experiences with minimal effort. 

## Product Constraints 

The following constraints must remain non-negotiable: 

- Security takes precedence over feature additions. 

- Organizations remain the owners of their data. 

- Provider implementations remain abstracted. 

- Components remain independently replaceable. 

- Multi-tenancy remains mandatory. 

- Responses must pass through validation mechanisms. 

- Graceful degradation mechanisms should exist wherever feasible. 

 Architectural simplicity should be preferred over unnecessary complexity. 

## Product Philosophy 

Scout.io is not intended to become another chatbot builder. It is designed to become an extensible AI Knowledge Infrastructure Platform that enables organizations to securely, intelligently, and efficiently expose their knowledge through configurable AI experiences. 

Its success will not be measured by the number of features implemented, but rather by its ability to provide: 

- Reliable AI infrastructures. 

- Secure knowledge management. 

- Provider-independent architectures. 

- Organization-centric experiences. 

- Long-term maintainability. 

This Product Requirements Document serves as the authoritative product specification for Scout.io and defines the functional, non-functional, architectural, and business requirements that all subsequent engineering decisions must inherit and preserve. 


---

## Phases (merged)

> The following section was merged from `docs/Phases.md`.

# PHASES 

## Overview 

This document defines the implementation roadmap for Scout.io. The project is intentionally divided according to product capabilities rather than technological boundaries. 

Every phase should satisfy the following objectives: 

- Produce usable deliverables. 

- Preserve architectural consistency. 

- Remain independently testable. 

- Preserve future extensibility. 

- Maintain security-first principles. 

Each phase builds incrementally upon the previous phase without introducing breaking architectural changes. 

## Project Roadmap 

Scout.io 

| Phase I Foundation Layer | Phase II Core Platform Layer | Phase III Intelligence Layer | Phase IV Production Layer | Phase V Scale & Future | Future Capabilities 

## Phase I 

# Foundation Layer 

### Objectives 

The objective of Phase I is to establish the foundational infrastructure required throughout Scout.io. 

### Deliverables 

_Project Infrastructure_ 

- Repository setup. 

- Project architecture. 

- Development environments. 

- Configuration management. 

- Logging mechanisms. 

- Environment management. 

#### _Backend Foundation_ 

- Modular monolith architecture. 

- Project structure implementation. 

- API foundations. 

- Middleware implementations. 

- Service abstractions. 

#### _Database Foundation_ 

- Multi-tenancy architecture. 

- Database schemas. 

- Organizational models. 

- Session models. 

- Policy models. 

- Analytics models. 

#### _Security Foundation_ 

- JWT authentication. 

- Authorization mechanisms. 

- Organization isolation. 

- Security middleware. 

- Input validations. 

_Scout Core Foundation_ 

Implement: 

- Policy Layer 

- Security Layer 

- Session Layer 

- Knowledge Layer abstractions 

- AI Layer abstractions 

### Completion Criteria 

Phase I shall be considered complete if: 

- Organizations can register. 

- Authentication workflows function correctly. 

- Multi-tenancy is operational. 

- Scout Core abstractions are implemented. 

- Security mechanisms are functioning. 

## Phase II 

# Core Platform Layer 

### Objectives 

The objective of Phase II is to make Scout.io usable by organizations. 

### Deliverables 

_Organization Dashboard_ 

Implement: 

- Organization management. 

- Dashboard interfaces. 

- Chatbot management. 

- Policy configurations. 

- Session configurations. 

_Chatbot Management_ 

Support: 

- Multiple chatbots. 

- Independent configurations. 

- Independent policies. 

- Independent analytics. 

#### _Knowledge Source Management_ 

Implement support for: 

- Websites. 

- PDFs. 

- Markdown files. 

- TXT files. 

_Synchronization Workflows_ 

Implement: 

- Manual synchronizations. 

- Scheduled synchronizations. 

- Metadata management. 

_Widget Development_ 

Implement: 

- Scout Widget. 

- Theme configurations. 

- Website integrations. 

- Session handling. 

### Completion Criteria 

Organizations should be capable of: 

- Creating chatbots. 

- Connecting knowledge sources. 

- Configuring behaviours. 

- Deploying widgets. 

- Managing sessions. 

At the completion of Phase II, Scout.io becomes a usable product. 

## Phase III 

# Intelligence Layer 

### Objectives 

The objective of Phase III is to implement Scout Core’s intelligence capabilities. 

### Deliverables 

#### _Knowledge Layer_ 

#### Implement: 

- Embedding generation. 

- Retrieval workflows. 

- Knowledge indexing. 

- Context management. 

#### _AI Layer_ 

#### Implement: 

- AI routing. 

- Provider abstractions. 

- Multi-model support. 

- Open-source fallback models. 

_Validation Layer_ 

#### Implement: 

- Context validations. 

- Policy validations. 

- Response validations. 

- Security validations. 

_Optimization Layer_ 

#### Implement: 

- Retrieval optimizations. 

- Cache management. 

- Token optimizations. 

- Performance improvements. 

_Memory Framework_ 

#### Implement: 

- Session memory. 

- Knowledge memory. 

- Organizational memory. 

- Optimization memory. 

### Completion Criteria 

Scout Core should support: 

- Context-aware responses. 

- Multi-provider support. 

- Retrieval optimizations. 

- Graceful fallback mechanisms. 

- Token optimizations. 

Phase III transforms Scout.io into an intelligent AI Knowledge Infrastructure Platform. 

## Phase IV 

# Production Layer 

### Objectives 

The objective of Phase IV is to prepare Scout.io for production deployments. 

### Deliverables 

#### _Analytics Framework_ 

#### Implement: 

- Organizational analytics. 

- Session analytics. 

- Retrieval analytics. 

- Synchronization analytics. 

- Performance analytics. 

_Deployment Framework_ 

#### Implement: 

- Widget deployments. 

- Production configurations. 

- Deployment validations. 

- Integration workflows. 

_Security Enhancements_ 

#### Implement: 

- Advanced rate limiting. 

- Session protections. 

- Response sanitization. 

- Audit mechanisms. 

#### _Performance Improvements_ 

Implement: 

- Background workers. 

- Queue management. 

- Intelligent caching. 

- Incremental synchronizations. 

_Monitoring_ 

Implement: 

- Service monitoring. 

- Performance monitoring. 

- Failure monitoring. 

- Synchronization monitoring. 

### Completion Criteria 

Scout.io should support: 

- Production deployments. 

- Organizational monitoring. 

- Secure integrations. 

- Intelligent synchronizations. 

- Performance optimizations. 

## Phase V 

# Scale & Future Layer 

### Objectives 

The objective of Phase V is to introduce scalability and future capabilities. 

### Deliverables 

_Future Knowledge Sources_ 

Support: 

- APIs. 

- Databases. 

- Git repositories. 

- Enterprise integrations. 

####  Future connectors. 

_Deployment Extensions_ 

Implement: 

- SDK integrations. 

- Hybrid deployments. 

- Self-hosting capabilities. 

- Enterprise deployments. 

_Advanced Intelligence_ 

Implement: 

- Advanced optimizations. 

- Multi-modal capabilities. 

- Voice integrations. 

- Agentic workflows. 

_Scalability Improvements_ 

Implement: 

- Horizontal scaling. 

- Distributed architectures. 

- Future microservices. 

- Multi-region deployments. 

### Completion Criteria 

Scout.io should support: 

- Enterprise capabilities. 

- Future integrations. 

- Advanced deployments. 

- Distributed architectures. 

- Long-term extensibility. 

## Suggested MVP Scope 

The MVP intentionally excludes: 

- Voice interfaces. 

- Multi-modal capabilities. 

- Enterprise deployments. 

- Agentic workflows. 

- Mobile applications. 

- Distributed architectures. 

### MVP Includes 

Organizations 

##### ↓ 

Multiple Chatbots 

##### ↓ 

Website Sources 

##### ↓ 

Knowledge Retrieval 

##### ↓ 

AI Routing 

##### ↓ 

Scout Widget 

##### ↓ 

Analytics 

##### ↓ 

Production Deployment 

##### ↓ 

Organizations Ready 

The MVP should remain intentionally minimal and stable. 

## Suggested Development Order 

### Sprint Zero 

#### Implement: 

- Repository setup. 

- Architecture setup. 

- Environment configurations. 

- Database setup. 

- Security foundations. 

### Sprint One 

#### Implement: 

- Authentication. 

- Organizations. 

- Policies. 

- Multi-tenancy. 

- Dashboard foundations. 

### Sprint Two 

#### Implement: 

- Chatbot management. 

- Knowledge source management. 

- Synchronization workflows. 

### Sprint Three 

#### Implement: 

- Scout Widget. 

- Session management. 

- Deployment workflows. 

### Sprint Four 

#### Implement: 

- Knowledge Layer. 

- Retrieval mechanisms. 

- Embedding workflows. 

### Sprint Five 

Implement: 

- AI Layer. 

- Multi-provider support. 

- Fallback mechanisms. 

### Sprint Six 

Implement: 

- Memory Framework. 

- Optimization Layer. 

- Token optimizations. 

### Sprint Seven 

Implement: 

- Analytics. 

- Monitoring. 

- Performance optimizations. 

### Sprint Eight 

Implement: 

- Production deployments. 

- Security enhancements. 

- Final testing. 

## Development Philosophy 

The implementation philosophy of Scout.io intentionally follows: 

Foundation → Functionality → Intelligence → Production → Scalability 

and not: 

Frontend → Backend → AI → Deployment 

Every phase should deliver meaningful capabilities rather than partially completed technological implementations. 

## Project Constraints 

The following constraints remain mandatory throughout development: 

- Security takes precedence over feature additions. 

- Organizations remain the owners of their knowledge. 

- Multi-tenancy remains mandatory. 

- Scout Core remains provider-independent. 

- Optimization mechanisms remain privacy-preserving. 

- Components remain independently replaceable. 

- Graceful degradation mechanisms should always exist. 

- Future architectural changes must preserve backward compatibility whenever feasible. 

## Phase Philosophy 

Scout.io intentionally evolves through capabilities rather than technologies. Each phase exists to progressively transform the platform from foundational infrastructure into an intelligent, production-ready AI Knowledge Infrastructure Platform. 

The success of this roadmap will not be measured by implementation speed alone, but by its ability to preserve simplicity, extensibility, security, and reliability throughout every stage of development. 

This document serves as the authoritative implementation roadmap for Scout.io and defines all development phases, deliverables, constraints, and milestones that future engineering efforts must inherit and preserve. 

