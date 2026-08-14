# Scout.io — Phase V Implementation Prompts

Each block below is self-contained and ready to paste into your AI IDE. Work through them roughly in order within a sprint — later prompts in a sprint sometimes assume earlier ones landed. Every prompt tells the AI IDE to first read your existing code before writing anything, so it stays consistent with what's already built rather than inventing a parallel pattern.

---

## Decisions Locked In

Where the review gave you a choice, here's the one I'd actually ship with, and why — no more forks in the road below.

| Area | Choice | Why |
|---|---|---|
| Secrets management | **HashiCorp Vault**, self-hosted, added as a service in `docker-compose.prod.yml` | Cloud-agnostic, fits your existing self-hosted Docker Compose pattern instead of assuming AWS/GCP |
| Observability stack | **Prometheus + Grafana + Loki + Alertmanager**, self-hosted | You already expose a Prometheus endpoint; this keeps everything in the stack you're already running instead of adding a SaaS bill pre-revenue |
| Error tracking | **Sentry**, SaaS free tier to start | Fastest to wire in; self-host later if volume demands it |
| CI/CD | **GitHub Actions** | You're already on GitHub |
| Billing | **Stripe** (Billing + metered usage) | Maps directly onto your existing `LLMUsage` model |
| Reranking model | `cross-encoder/ms-marco-MiniLM-L-6-v2` via `sentence-transformers`, run as its **own microservice** | Small, fast, well-benchmarked; isolating it keeps it off FastAPI's event loop |
| Tenant dashboard | **Next.js Pages Router** | Matches your existing Admin/Developer portals — don't mix routers mid-project |
| Tenant isolation backstop | **Postgres native Row-Level Security**, enforced via `SET LOCAL app.current_org_id` per request | Uses infra you already have, no new moving parts |
| Log aggregation | **Loki** (part of the Grafana stack above) | Same reasoning as observability |

---

## Sprint 1 — Multi-Tenancy & Security Hardening

### 1.1 Postgres Row-Level Security

```
Read the current SQLAlchemy models and org-isolation logic in the backend (Organization,
User, Chatbot, Policy, KnowledgeSource, ChatSession, Message, and any other tables scoped
to organization_id). Do not change the ORM query patterns yet — first add a defense-in-depth
layer at the database level.

Write a new Alembic migration that:
1. Enables Row-Level Security on every table with an organization_id column.
2. Adds a policy on each such table restricting SELECT/INSERT/UPDATE/DELETE to rows where
   organization_id = current_setting('app.current_org_id')::uuid.
3. Adds a separate policy (or bypass role) for platform-admin operations that legitimately
   need cross-org access (e.g. the /admin endpoints), scoped as narrowly as possible —
   do not just disable RLS for a superuser role used everywhere.

Then update the FastAPI request lifecycle (likely in the get_db dependency or a middleware)
to run `SET LOCAL app.current_org_id = :org_id` at the start of every request, sourced from
the authenticated user's JWT claims, before any query executes on that connection.

Write tests that prove: (a) a request scoped to Org A cannot read Org B's rows even if the
application-level WHERE clause is accidentally removed from a query, and (b) admin endpoints
still function correctly. Do not weaken any existing application-level org filtering — this
is an additional layer, not a replacement.
```

### 1.2 Vault secrets integration

```
Add HashiCorp Vault to docker-compose.yml (dev) and docker-compose.prod.yml as a new service,
using the official Vault Docker image. Configure it in dev mode locally and document the steps
needed to unseal/configure it for production in docs/.

Then:
1. Identify every secret currently read from .env files across backend, frontend, and widget
   (DB credentials, JWT signing keys, LLM provider API keys, Redis/Qdrant connection strings,
   webhook signing secrets, etc.) by grepping for os.environ / os.getenv / process.env usage.
2. Write a small Vault client wrapper (e.g. app/core/secrets.py using hvac) that fetches
   these at application startup and falls back to environment variables only in local dev
   when Vault is unreachable — never fail silently in a way that masks a real production
   misconfiguration.
3. Replace direct env var reads for secrets (not general config) with calls through this
   wrapper across the backend.
4. Update .env.example files to remove real secret placeholders and instead document that
   secrets live in Vault, with a path convention (e.g. secret/scout-io/<env>/<key>).

Do not commit any real secret values anywhere in this change.
```

### 1.3 Prompt-injection & cross-tenant leakage test suite

```
Read response_pipeline.py, engine.py, and sanitizer.py to understand the current RAG
request flow and what sanitizer.py already strips from responses.

Build an adversarial test suite (new file, e.g. tests/security/test_prompt_injection.py)
that sends crafted widget-chat inputs designed to:
1. Extract the system prompt or internal pipeline instructions.
2. Get the model to ignore the active Policy's source_filter/content_filter and answer from
   out-of-scope knowledge.
3. Get the model to reveal another organization's chatbot configuration, knowledge source
   content, or session data, by directly asking or via indirect injection embedded in
   retrieved document chunks (simulate a malicious document ingested into the knowledge base
   containing hidden instructions).
4. Trigger sanitizer.py bypass — craft outputs that leak provider/model names or secrets in
   formats the current sanitizer regex/logic doesn't catch (e.g. partial strings, encoded
   text, unusual delimiters).

For every test that currently fails (i.e. the attack succeeds), propose and implement a
concrete fix: this may mean strengthening the system prompt with explicit instruction-hierarchy
language, adding a post-generation classifier/filter step before the response leaves
response_pipeline.py, or extending sanitizer.py's detection patterns. Report a before/after
pass rate.
```

---

## Sprint 2 — Tenant-Facing Dashboard

### 2.1 Org dashboard shell

```
Read the existing Next.js Pages Router structure under /admin and /developer to match its
layout, auth pattern, and styling conventions exactly (Tailwind classes, component structure,
how JWT auth is checked on page load, how API calls are made to the FastAPI backend).

Create a new top-level section /dashboard for organization tenant users (distinct from
platform admins and API developers) with:
1. A layout component with sidebar nav: Overview, Chatbots, Knowledge Sources, Policies,
   Analytics, Team, Billing, Settings — stub pages for each, wired into routing.
2. Auth guard that allows any authenticated user belonging to an organization (not just
   admins) and redirects unauthenticated users to login.
3. An Overview page showing: chatbot count, this month's message volume, and current plan —
   pull real data from existing GET /organizations/me/ and /analytics/organization endpoints,
   don't hardcode placeholder numbers.

Match the existing design language exactly — this should feel like the same product as the
admin/developer portals, not a bolted-on section.
```

### 2.2 Chatbot builder UI

```
Read the existing chatbot CRUD endpoints (chatbots, policies) and their Pydantic schemas in
the backend to know exact field names and validation rules before building the form.

Build /dashboard/chatbots (list view) and /dashboard/chatbots/[id] (edit view) plus a create
flow, allowing an org user to:
1. Create/rename/delete a chatbot they own.
2. Attach one or more knowledge sources to it.
3. Configure its Policy (source_filter, content_filter, and any other fields the Policy model
   exposes) through a real form, not raw JSON editing.
4. Pick a model tier (fast/balanced/accurate per config.py's existing mapping) with plain-
   language descriptions of the cost/quality tradeoff for each.
5. Preview the widget snippet for this chatbot, reusing the existing widget-snippet generation
   logic from the developer portal rather than duplicating it.

Handle loading/error states for every API call. Confirm destructive actions (delete chatbot)
with a modal before executing.
```

### 2.3 Knowledge source upload & management UI

```
Read knowledge_sources CRUD endpoints, the ingestion Celery tasks, and the connector registry
(SQL/API/Git connectors mentioned in Progress.md) to understand what source types and status
fields already exist (sync status, last synced, error state).

Build /dashboard/knowledge-sources with:
1. A list showing every source for the org's chatbots, with live sync status (poll or
   websocket if one exists, otherwise short-interval polling) and last-synced timestamp.
2. An "Add Source" flow supporting file upload (PDF/Markdown/DOCX/TXT per the multi-modal
   ingestion already built), a website URL, and the SQL/API/Git connector types — each with
   the specific fields that connector type actually requires on the backend.
3. Clear surfacing of ingestion failures (pull from whatever error/status field the sync
   failure tracking in Sprint 3 of Phase IV already stores) with a retry button that calls
   the existing retry-capable sync endpoint.
4. A per-source delete flow that warns the user this will remove it from every chatbot using it.

Do not reimplement ingestion logic in the frontend — this is purely a UI over existing backend
capability.
```

### 2.4 Org-scoped analytics view

```
Read GET /analytics/chatbot/{chatbot_id}, GET /analytics/organization, and the
DailyAnalytics/AnalyticsEvent models to know what data is actually available before designing
charts around it.

Build /dashboard/analytics using recharts (already an available library) showing, scoped
strictly to the logged-in user's own organization:
1. Message volume and unique sessions over time (line chart, selectable date range).
2. Token usage over time, broken out per chatbot if the org has more than one.
3. Latency and feedback/thumbs-up-down trends if those fields exist in DailyAnalytics.
4. Per-source usage from GET /analytics/source/{source_id} for org admins auditing which
   knowledge sources are actually being retrieved from.

Confirm every query the frontend makes is going through org-scoped endpoints only — this page
must be impossible to use to see another organization's data, even by manipulating chatbot_id
in a request (backend should already reject this per Sprint 1.1 RLS work, but verify it here
with a manual test).
```

---

## Sprint 3 — Billing

### 3.1 Stripe subscription backend

```
Read the Organization model and any existing plan/tier concept in the codebase (check
system_config and Policy models for anything plan-related before assuming none exists).

Integrate Stripe:
1. Add a `stripe_customer_id` and `plan` field to the Organization model, with a new Alembic
   migration.
2. Build POST /organizations/me/billing/checkout-session (creates a Stripe Checkout session
   for a plan the user selects) and a webhook endpoint POST /webhooks/stripe that handles
   subscription.created/updated/deleted events, updating the org's plan and status accordingly.
   Verify Stripe webhook signatures — do not trust unsigned payloads.
3. Define at least three plan tiers (e.g. Starter/Growth/Scale) as Stripe Products/Prices,
   documented in docs/, with concrete limits per tier (chatbots allowed, monthly message
   volume, knowledge source count) enforced at the API layer — reject chatbot/message creation
   past the plan limit with a clear error the frontend can surface.
4. Add audit log entries for plan changes, reusing the existing app/utils/audit.py helper.

Use Stripe's test mode keys throughout; do not hardcode live keys anywhere — pull them through
the Vault wrapper built in Sprint 1.2.
```

### 3.2 Usage-based metering off LLMUsage

```
Read the LLMUsage model and everywhere it's currently written to (should be inside the AI
router / response pipeline after each generation call).

Build a Celery beat task (following the existing aggregate_daily_analytics pattern) that:
1. Runs daily, aggregating each org's LLMUsage records into total tokens and estimated cost
   for the period.
2. Reports usage to Stripe via the Metered Billing API (stripe.SubscriptionItem.create_usage_record)
   for orgs on usage-based plan components.
3. Writes the aggregate into a new UsageBillingRecord table (org_id, period, tokens, cost,
   reported_to_stripe: bool) so support/finance can audit what was billed without querying
   Stripe directly.

Add a soft-limit warning: when an org crosses 80% of their plan's included usage, create an
AnalyticsEvent (reusing the existing event model) that the frontend billing page can surface
as a warning banner.
```

### 3.3 Billing UI in tenant dashboard

```
Read the Stripe backend work from 3.1/3.2 and the existing /dashboard shell from 2.1 before
building this page, so it matches the layout conventions already established.

Build /dashboard/billing showing:
1. Current plan, renewal date, and a link into Stripe's hosted Customer Portal for
   payment-method changes and invoice history (don't rebuild what Stripe's portal already
   does well).
2. Current-period usage against plan limits (tokens, chatbots, messages) as progress bars,
   pulling from UsageBillingRecord / the analytics endpoints.
3. A plan comparison/upgrade flow that calls the checkout-session endpoint from 3.1.
4. The 80%-usage warning banner from 3.2 when applicable.

Handle the case where an org has no active subscription yet (new signups) by defaulting to
a clearly labeled trial/free tier state rather than showing errors.
```

---

## Sprint 4 — CI/CD & Staging

### 4.1 GitHub Actions pipeline

```
Read the existing test setup (pytest for backend, npm test for frontend/widget) and the
docker-compose files to understand build targets before writing workflows.

Create .github/workflows/ with:
1. ci.yml — on every PR: run backend pytest suite, frontend npm test, widget npm test,
   and a lint/typecheck step for each. Fail the check if any step fails. Cache
   pip/npm dependencies to keep runs fast.
2. build.yml — on merge to main: build and push Docker images for backend, frontend, and
   widget to GitHub Container Registry, tagged with the commit SHA and `latest`.
3. deploy-staging.yml — on merge to main, after build.yml succeeds: deploy the new images to
   the staging environment (see 4.2) via SSH + docker compose pull && up -d, or via your
   actual staging host's deploy mechanism if one already exists — check for one before
   assuming SSH is the right approach.

Add a required-status-check branch protection recommendation in docs/ for main, so untested
code can't merge. Do not add automatic production deploys yet — that stays manual/gated until
Sprint 6's DR work is in place.
```

### 4.2 Staging environment + dockerignore fix

```
Read docker-compose.yml, docker-compose.dev.yml, and docker-compose.prod.yml to understand
the differences between environments already defined.

1. Add .dockerignore files to backend/, frontend/, and widget/ (not just the repo root) —
   each scoped to what that specific build context actually needs, excluding .git, .env*
   (except .env.example), node_modules, __pycache__, .venv, test directories, and docs.
   Verify with `docker build` that image build context size drops meaningfully.
2. Create docker-compose.staging.yml, based on docker-compose.prod.yml but pointing at
   staging-scoped resources (separate Postgres/Qdrant/Redis instances or databases, staging
   Stripe test keys via Vault, a staging-only subdomain in the Nginx config) so staging never
   touches production data.
3. Document the staging deploy process end-to-end in docs/staging.md, including how to reset
   staging data to a known-good seed state for repeatable testing.
```

---

## Sprint 5 — Observability & Load Testing

### 5.1 Prometheus + Grafana + Loki + Alertmanager stack

```
Read the existing Prometheus metrics endpoint, JSONLogFormatter, and tracing middleware
(X-Trace-ID) to know what's already instrumented before adding new services.

1. Add prometheus, grafana, loki, promtail, and alertmanager services to
   docker-compose.prod.yml, with Prometheus scraping the existing metrics endpoint and
   promtail shipping container stdout logs (already JSON-formatted) into Loki.
2. Build starter Grafana dashboards (as provisioned JSON, checked into the repo under
   docker/grafana/dashboards/) for: request rate/latency/error rate per endpoint, Celery
   queue depth and task failure rate, Qdrant/Postgres/Redis health (reuse the existing
   /health/ready aggregation logic as a source), and LLM provider fallback trigger rate.
3. Configure Alertmanager routes for: error rate above threshold, /health/ready reporting
   any dependency down for more than 2 minutes, and Celery queue depth growing unbounded —
   routed to a Slack webhook to start (document how to swap in PagerDuty later).

Log a trace_id-to-Grafana-dashboard link pattern so an on-call engineer can jump from an
alert straight to the relevant trace/logs.
```

### 5.2 Load testing suite

```
Read response_pipeline.py and the widget message endpoint to understand the full request
path being tested, including where LLM provider calls happen (these should be mocked or
capped in load tests to avoid real API cost/rate-limit issues).

Build a load-testing suite (Locust or k6, pick whichever fits the team's language preference
— Locust if the team is Python-first) under a new load-tests/ directory that:
1. Simulates concurrent widget chat sessions across multiple simulated organizations
   simultaneously, to specifically test whether one org's load can starve another's
   (per-org rate limiting should prevent this — verify it does).
2. Ramps from baseline to at least 10x expected launch-day concurrency, recording p50/p95/p99
   latency for the full pipeline and for each pipeline stage individually if timing hooks
   exist (add lightweight ones if not).
3. Separately load-tests the knowledge ingestion path (bulk document upload + embedding)
   under concurrent multi-org ingestion.

Produce a report identifying the first bottleneck that appears as load increases (likely
Qdrant query latency, Postgres connection pool exhaustion, or Celery worker count) and a
concrete scaling recommendation for it.
```

### 5.3 Reranking microservice

```
Read qdrant_store.py and engine.py to see exactly where retrieved chunks are currently
ranked and passed into the context-building step in response_pipeline.py.

1. Build a small standalone FastAPI service (new directory, e.g. services/reranker/) that
   loads cross-encoder/ms-marco-MiniLM-L-6-v2 via sentence-transformers at startup and
   exposes POST /rerank accepting a query and a list of candidate chunks, returning them
   reordered by relevance score. Add it to docker-compose.yml as its own service with its
   own resource limits.
2. Update engine.py's retrieval step to call this service after Qdrant's initial similarity
   search, reranking the top-K candidates before they're passed into context optimization.
   Make this behind a feature flag / config setting so it can be disabled per-chatbot or
   globally without a redeploy.
3. Add a fallback: if the reranker service is unreachable or times out, fall back to Qdrant's
   original similarity ranking rather than failing the whole request — this must degrade
   gracefully, consistent with the existing fallback philosophy in this codebase.
4. Measure and report retrieval precision before/after on a sample set of real queries against
   your existing knowledge bases, if any test knowledge base exists, or construct one.
```

---

## Sprint 6 — Backup/DR & Compliance

### 6.1 Backup & tested restore automation

```
Read the Postgres and Qdrant service definitions in docker-compose.prod.yml to know exact
data volume locations before scripting backups.

1. Add a Celery beat task or standalone cron container that runs nightly pg_dump of Postgres
   and a Qdrant snapshot API call, uploading both to object storage (S3-compatible; use
   whatever provider the team already has, or document the assumption if none exists).
   Retain daily backups for 30 days, weekly for 90 days.
2. Write a restore script (scripts/restore.sh or equivalent) that rebuilds a full environment
   from a given backup timestamp, and a docs/disaster-recovery.md runbook describing the exact
   steps a human follows during an incident.
3. Actually run the restore script against a scratch environment as part of this work, not
   just write it — confirm a real backup can be turned into a working environment, and record
   how long the process took (this becomes your documented RTO).
```

### 6.2 Org offboarding data purge

```
Read every table and Qdrant collection that stores org-scoped data (documents, embeddings,
chat sessions, messages, analytics events, audit logs — decide deliberately whether audit
logs should be purged or retained for legal reasons, and document that decision explicitly).

Build an org-offboarding endpoint/task that, on request, permanently deletes:
1. All Postgres rows scoped to that organization_id across every relevant table.
2. All Qdrant vectors/collections scoped to that org.
3. Any cached data in Redis (session memory, knowledge memory, org memory caches).
4. Uploaded source files in object storage.

Require explicit confirmation (e.g. a signed request from a platform admin, or a
double-confirmation flow from the org owner) before executing, log the purge itself to
audit_logs (as an exception to the "delete everything" rule, since you need proof deletion
happened), and return a completion report of exactly what was deleted.
```

### 6.3 Privacy policy / ToS drafting brief

```
This isn't a coding task — draft a structured brief for a lawyer to turn into an actual
Privacy Policy, Terms of Service, and Data Processing Agreement, covering: what customer
data Scout.io ingests and why (documents, chat content), where it's stored (Postgres/Qdrant
region), which third-party subprocessors are involved (LLM providers per LiteLLM config,
Stripe, hosting provider), the data retention periods now defined in 6.1's backup policy, the
offboarding/deletion capability now defined in 6.2, and whether any LLM provider used trains
on submitted data (check each configured provider's data usage policy explicitly — don't
assume "no" for any of them).

Output this as a clearly organized document a lawyer can work from directly, not final legal
language — flag any point where you're not confident of the technical fact so it gets verified
before publishing.
```

---

## Sprint 7 — Closed Beta Prep

### 7.1 TOTP-based MFA

```
Read the existing JWT auth flow (login/refresh/logout) to understand exactly where to insert
a second factor without breaking existing sessions or the widget's separate session-token
auth path (which should NOT require MFA — that's end-user chat auth, not org-admin auth).

1. Add a `totp_secret` (encrypted at rest, not plaintext) and `mfa_enabled` field to the User
   model, with a migration.
2. Build endpoints to enable MFA (generate secret, show QR code, verify first code before
   activating), disable MFA (require current password + a valid code), and a login flow that,
   for mfa_enabled users, requires a second /auth/mfa/verify step after password check before
   issuing tokens.
3. Add recovery codes (one-time use, generated at MFA setup, stored hashed) for account
   recovery if the authenticator device is lost.
4. Build the corresponding UI in the dashboard's Settings page for setup/disable/recovery-code
   regeneration.

Do not make MFA mandatory platform-wide yet — make it available and strongly recommended for
org admins, mandatory only for platform admin accounts (the /admin portal).
```

### 7.2 Beta onboarding & feedback instrumentation

```
Read the existing AnalyticsEvent model and dashboard shell from Sprint 2 before adding new
tracking, so beta feedback data lands in the same system rather than a separate one.

1. Build a lightweight onboarding checklist on the dashboard Overview page for new orgs
   (create first chatbot, add first knowledge source, test the widget, invite a teammate),
   tracked via AnalyticsEvent so you can see where beta users actually get stuck.
2. Add a simple in-dashboard feedback widget (thumbs up/down + optional text) surfaced after
   key actions (first successful chatbot response, first knowledge source sync), stored as
   its own event type.
3. Build a minimal internal view (under /admin, matching existing admin page conventions) for
   the team to review onboarding funnel drop-off and feedback submissions across all beta orgs,
   since this is exactly the kind of cross-org visibility that should stay admin-only, not
   exposed to tenant dashboards.

This sprint's goal is instrumentation, not polish — the point is to know exactly where real
users struggle once beta actually starts.
```
