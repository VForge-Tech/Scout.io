# Org Offboarding (Permanent Data Deletion)

## Purpose

Permanently delete an organization and **all** data scoped to it across every
store the platform touches, with an explicit two-step confirmation so this
irreversible action cannot be triggered by accident.

## Flow

1. `POST /api/v1/admin/organizations/{org_id}/offboard` (platform admin only)
   - Returns a deletion **preview** (per-table Postgres counts, Qdrant/pgvector
     points, Redis cache counts, upload file/byte counts) plus a signed
     **confirmation token** (JWT, `type=offboard_confirm`, bound to the org and
     the admin, 15 minute TTL).
   - Deletes nothing.
2. `POST /api/v1/admin/organizations/{org_id}/offboard/confirm` (platform admin
   only) with `{"confirmation_token": "..."}`
   - Verifies the token (must be valid, match this org and this admin).
   - Executes the purge and returns a completion **report**.

The two calls are also audit-logged (`org_offboard_requested` and the
platform-level purge proof).

## What gets deleted

- **Postgres** – every org-scoped row across `messages` (via its sessions),
  `analytics_events`, `daily_analytics`, `llm_usage`, `knowledge_sources`,
  `policies`, `sessions`, `chatbots`, `api_keys`, `audit_logs` (org-scoped
  rows), `webhooks`, `usage_billing_records`, `users`, and finally the
  `organizations` row itself, in child-before-parent order so no FK is
  violated.
- **Vectors** – the org's points in the Qdrant collection, and the pgvector
  fallback rows when `pgvector_enabled`.
- **Redis** – org memory keys (`org_config:*`, `org_policies:*`), session
  history keys (`session:*:history`), the knowledge cache (`knowledge_cache:*`
  entries whose payloads reference the org), and the optimization cache
  (`opt_cache:*` namespace – keys are md5-hashed with no org marker, so the
  whole short-TTL namespace is evicted).
- **Uploads** – everything under `UPLOAD_DIR/<org_id>/`.

## Retention decision (documented)

**Audit logs.** Org-scoped audit-log rows are **purged** as part of the
offboarding – they are org data and the org is permanently leaving the
platform. However, the offboarding operation itself is written to `audit_logs`
**before** the purge as a platform-level record (`organization_id` and
`user_id` are NULL; the org id, org name and initiating admin id live in the
`details` JSON). Because it is not org-scoped, the purge cannot remove it, and
it survives as immutable proof that the deletion happened. This is a deliberate
exception to the purge rule.

**Billing records.** `usage_billing_records` rows are deleted as part of "all
Postgres rows". The FK from billing records to `organizations` is NOT NULL, so
retaining them would make it impossible to delete the org row. Financial
settlement must therefore happen **before** offboarding – the runbook
prerequisite below covers this.

## Runbook prerequisites

1. Confirm the operator genuinely intends permanent deletion.
2. Settle / export any outstanding **financial obligations** (billing records
   are deleted).
3. If any external requirement demands a data export (e.g. customer
   contract), export it before running the confirm step.
4. Confirm the organization name in the preview matches the target org.

## Verification

After offboarding:

- `GET /api/v1/admin/organizations` no longer lists the org.
- `GET /api/v1/admin/audit-logs` still contains the `org_offboarded` proof
  record with `organization_id`/`user_id` NULL and the org id in `details`.

## Scope notes / known gaps

- `usage_billing_records` has **no RLS policy** (it was created in migration
  0008 and was not added to the RLS table list in 0006). This pre-dates
  offboarding; offboarding does not rely on RLS (platform-admin bypass), but
  the gap is noted here for future RLS coverage.
- Deletion is executed in a single transaction for Postgres; Redis/Qdrant/
  uploads are best-effort external stores and are reported in the completion
  report (`deleted.*`) rather than rolled back with the DB.