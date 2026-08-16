# Webhooks

Scout.io webhooks let an organization receive async notifications about events
in their account (default event: `sync.completed` when a knowledge-source sync
finishes). This doc covers the current implementation: the management API and
inbound signature verification. There are two distinct webhook surfaces:

1. **Outbound webhooks** — org-registered URLs that receive event
   notifications (management API below).
2. **Inbound webhook** — the Razorpay payment webhook that updates plan
   status (see `docs/integrations/billing-razorpay.md`).

## Outbound webhook management API

All endpoints are under `/api/v1/webhooks` and require an authenticated user
JWT (`Authorization: Bearer <access_token>`); rows are org-scoped.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/webhooks` | Create a webhook for the org |
| GET | `/api/v1/webhooks` | List the org's active webhooks |
| DELETE | `/api/v1/webhooks/{webhook_id}` | Deactivate a webhook |

### Create

```bash
curl -X POST http://localhost:8000/api/v1/webhooks \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/hooks/scout", "events": "sync.completed"}'
```

`events` defaults to `sync.completed`. Creating a webhook writes an audit log
entry (`webhook.created`); deleting sets `is_active = false` (soft delete) and
logs `webhook.deleted`.

### List / Delete

```bash
curl http://localhost:8000/api/v1/webhooks \
  -H "Authorization: Bearer <access_token>"

curl -X DELETE http://localhost:8000/api/v1/webhooks/{webhook_id} \
  -H "Authorization: Bearer <access_token>"
```

## Webhook model

`Webhook` (`backend/app/models/webhook.py`):

- `id` — UUID
- `organization_id` — owning org (FK, org-scoped via RLS)
- `url` — target URL (max 1024)
- `events` — event filter string (default `sync.completed`)
- `is_active` — soft-delete flag
- `secret` — signing secret (optional; used to sign outbound payloads)
- `created_at`

Delivery payloads are HMAC-signed with the webhook's `secret` when configured;
receivers should verify the signature before acting on the payload.

## Razorpay inbound webhook (signature-verified)

Razorpay subscription events (`subscription.activated`, `subscription.charged`,
`subscription.cancelled`, `subscription.halted`) are delivered to
`POST /api/v1/webhooks/razorpay`. Every payload is verified with
`verify_webhook_signature` (`backend/app/core/billing/razorpay_client.py`):
HMAC-SHA256 of the raw body against `razorpay_webhook_secret`
(configurable via Vault secret `razorpay_webhook_secret` or
`RAZORPAY_WEBHOOK_SECRET`), constant-time comparison. Unsigned or invalid
payloads are rejected; valid events update the org's plan/status and write
audit log entries. See `docs/integrations/billing-razorpay.md`.

## Configuration

- `webhook_secret` (Vault secret, env fallback in dev) — general webhook
  signing secret (`app/core/secrets.py` → `get_webhook_secret`).
- `razorpay_webhook_secret` (Vault secret / `RAZORPAY_WEBHOOK_SECRET`) — the
  inbound Razorpay signature key.

## Operations notes

- **Testing**: use a local endpoint (e.g. webhook.site) or a small HTTP
  receiver to capture delivery payloads. Razorpay webhooks can be exercised in
  test mode via the Razorpay dashboard.
- **Retries**: async event delivery with retry logic is part of the roadmap
  (see `docs/roadmap.md`); the current implementation provides the management
  API, signing, and inbound verification.