# Admin Guide (Platform Administrators)

This guide is for Scout.io **platform administrators** — the internal operators
who manage all organizations, audit logs, system configuration, health, and
data deletion across the platform. It assumes access to the `/admin` portal and
the platform-admin API. Organization admins managing their own workspace should
read `docs/guides/client-guide.md`.

## Access requirements

The `/admin` portal requires:

1. A user account with `platform_admin = true`.
2. **MFA enabled** — `require_platform_admin` returns `403` for platform-admin
   accounts without MFA, making two-factor authentication mandatory for admin
   access. Widget session auth is never affected.

## Admin portal pages

| Page | URL | Purpose |
|------|-----|---------|
| Dashboard | `/admin` | Platform statistics cards |
| Organizations | `/admin/organizations` | List, search, suspend orgs |
| Audit Logs | `/admin/audit-logs` | Paginated audit trail with filters |
| System Health | `/admin/system-health` | Real-time service status |
| Settings | `/admin/settings` | System configuration key-value editor |
| Onboarding & Feedback | `/admin/onboarding` | Onboarding funnel + feedback across all orgs |

## Admin API

All endpoints are under `/api/v1/admin`, platform-admin only.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/admin/organizations` | List orgs |
| GET | `/api/v1/admin/organizations/{org_id}` | Get org |
| PATCH | `/api/v1/admin/organizations/{org_id}` | Suspend/activate org |
| DELETE | `/api/v1/admin/organizations/{org_id}` | Delete org |
| POST | `/api/v1/admin/organizations/{org_id}/offboard` | Offboarding preview (see below) |
| POST | `/api/v1/admin/organizations/{org_id}/offboard/confirm` | Execute offboarding |
| GET | `/api/v1/admin/stats` | Platform stats |
| GET | `/api/v1/admin/system-config` | List system config |
| PUT | `/api/v1/admin/system-config/{key}` | Update system config |
| GET | `/api/v1/admin/audit-logs` | Audit logs |
| GET | `/api/v1/admin/llm-usage` | LLM usage records |
| GET | `/api/v1/admin/health` | Admin health check |
| GET | `/api/v1/admin/analytics/platform` | Platform-wide analytics |
| GET | `/api/v1/admin/onboarding/funnel` | Onboarding funnel + feedback |

> Admin requests use `get_db_admin`, which sets `app.is_platform_admin =
> 'true'` for the RLS bypass — cross-org access is narrowly scoped to the admin
> role, never a superuser.

## Organization management

- **List/search** orgs at `/admin/organizations`.
- **Suspend** an org via `PATCH /api/v1/admin/organizations/{org_id}` with
  `{"suspended": true}` (or `false` to reactivate).
- **Delete** an org via `DELETE /api/v1/admin/organizations/{org_id}`. For a
  full permanent purge of the org's data, use **offboarding** below.

## Offboarding (permanent data deletion)

Offboarding is the compliant path for deleting a customer's data. It is a
two-step, platform-admin-only flow:

1. `POST /api/v1/admin/organizations/{org_id}/offboard` — returns a **preview**
   of what would be deleted (per-table Postgres counts, Qdrant/pgvector points,
   Redis cache counts, upload files/bytes) plus a signed **confirmation token**
   (JWT `type=offboard_confirm`, bound to org + admin, 15-minute TTL). This
   call deletes nothing.
2. `POST /api/v1/admin/organizations/{org_id}/offboard/confirm` with the token
   — executes the purge and returns a completion report.

What gets purged (see `docs/operations/security-and-compliance.md` →
"Org offboarding"):

- Postgres: every org-scoped row in FK-safe order (messages, analytics, usage,
  knowledge sources, policies, sessions, chatbots, api keys, org-scoped audit
  logs, webhooks, usage billing records, users, then the org).
- Vectors: Qdrant chunks and pgvector rows for the org.
- Redis: org memory, session history, knowledge/optimization caches.
- Uploads: files under the org's upload directory.

Audit retention decision: org-scoped audit logs are purged, but an
**immutable proof-of-deletion** audit entry is written first (platform-level,
survives the purge). `usage_billing_records` are also deleted (FK constraint),
so ensure financial settlement happens **before** offboarding.

## Audit logs

Every sensitive action is logged to `audit_logs` (login, logout, chatbot
create/delete, webhook create/delete, system config changes, billing plan
changes, offboarding). View them at `/admin/audit-logs` or
`GET /api/v1/admin/audit-logs?limit=50&offset=0`.

## System configuration

`/admin/settings` is a key-value editor over `system_config`. Values are
written via `PUT /api/v1/admin/system-config/{key}` and are logged to the audit
trail. Use for runtime tunables; **do not store secrets** here — secrets belong
in Vault (see `docs/operations/security-and-compliance.md`).

## System health & analytics boundary

- `/admin/system-health` shows live service status from
  `GET /api/v1/admin/health` (Postgres, Redis, Qdrant, etc.).
- `/admin/analytics/platform` exposes platform-wide aggregates.
- The onboarding funnel (`/admin/onboarding`) shows per-org checklist state and
  all feedback submissions across every org. This cross-org view is admin-only
  by design — tenant dashboards can only ever see their own org's data.

## Incident response

During an incident:

1. Check `/admin/system-health` and `GET /health/ready` for dependency status.
2. Follow the relevant runbook:
   - Data loss / corruption / failed migration → `docs/operations/disaster-recovery.md`
   - Data-deletion requests → **offboarding** above.
   - Provider or infrastructure alerts → `docs/operations/monitoring-observability.md`
     (Alertmanager → Slack; trace-id → Grafana deep links).
3. Restore from nightly backup via `scripts/restore.sh --latest` only when
   appropriate (it wipes the datastore volumes — see the DR runbook).

## Related documentation

- `docs/operations/security-and-compliance.md` — security model, Vault, RLS,
  offboarding, privacy brief.
- `docs/operations/disaster-recovery.md` — backup/restore runbook.
- `docs/operations/monitoring-observability.md` — metrics, logs, alerts.
- `docs/integrations/billing-razorpay.md` — plan changes and Razorpay webhooks
  (events update org plan/status automatically).
- `docs/operations/staging-deployment.md` — staging environment ops.