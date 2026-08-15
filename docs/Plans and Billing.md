# Plans, Pricing & Billing (Razorpay)

Scout.io uses [Razorpay Subscriptions](https://razorpay.com/docs/subscriptions/) for
plan management. Razorpay's self-serve business signup works from India without the
invite-only friction Stripe currently has. **Important:** confirm the account is fully
activated (KYC complete) before assuming live mode will work later — keep test-mode keys
in place until then.

## Plan tiers

Defined in `backend/app/core/billing/plans.py`. Limits are enforced at the API layer
in `backend/app/core/billing/limits.py`.

| Plan   | Price / month (INR) | Chatbots | Messages / month | Knowledge sources |
|--------|---------------------|----------|------------------|-------------------|
| Free   | ₹0                  | 1        | 1,000            | 5                 |
| Starter| ₹2,999             | 3        | 10,000           | 20                |
| Growth | ₹9,999             | 10       | 100,000          | 100               |
| Scale  | ₹29,999            | 50       | 1,000,000        | 500               |

Razorpay plan IDs (`plan_starter`, `plan_growth`, `plan_scale`) are created in the
Razorpay Dashboard (test mode) and referenced by the `razorpay_plan_id` field in each
`PlanTier`. The `free` plan has no Razorpay plan and is the default for new orgs.

### Enforcement behavior

- Creating a chatbot beyond the plan's `chatbot_limit` → HTTP `402 Payment Required`
  with a message the frontend can surface ("Your X plan allows up to N chatbots...").
- Creating a knowledge source beyond `knowledge_source_limit` → HTTP `402`.
- Widget messages beyond `monthly_message_limit` (per calendar month) → HTTP `402`.
- When an org's `plan_status` is `cancelled` or `halted`, it is automatically
  downgraded to the Free tier for enforcement purposes.

## Configuration

Billing is a **feature flag**. It is **disabled by default** so testing/dev builds
run without plan-limit enforcement and the checkout/webhook endpoints return `503`.
Enable it in production.

| Setting | Env var | Default | Notes |
|---------|---------|---------|-------|
| `billing_enabled` | `BILLING_ENABLED` | `false` | `true` in production. When off: no limits enforced, checkout/webhook return 503, billing page shows "disabled". |

Keys are pulled through the Vault wrapper (`backend/app/core/secrets.py`) with env-var
fallback for development. Path convention: `secret/scout-io/<env>/razorpay_*`.

| Secret key | Env var | Notes |
|------------|---------|-------|
| `razorpay_key_id` | `RAZORPAY_KEY_ID` | Test-mode Key ID (`rzp_test_...`) |
| `razorpay_key_secret` | `RAZORPAY_KEY_SECRET` | Test-mode Key Secret |
| `razorpay_webhook_secret` | `RAZORPAY_WEBHOOK_SECRET` | Webhook signing secret |

**Never hardcode live keys.** Only test-mode keys should be configured while the account
is not yet KYC-approved for live mode.

## API

### `POST /api/v1/organizations/me/billing/checkout-session`

Body: `{"plan": "growth"}` (must be `starter`, `growth`, or `scale`).

- Ensures a Razorpay customer exists for the org (`razorpay_customer_id` stored).
- Creates a monthly subscription against the plan's Razorpay Plan ID.
- Returns `{subscription_id, checkout_url, plan, status}`. `checkout_url` (the Razorpay
  short URL) is where the user completes payment.
- Records an audit log entry `billing.checkout_session_created`.

### `GET /api/v1/organizations/me/billing`

Returns the org's current plan, status, limits vs. usage, and the list of available plans
(for the billing UI).

### `POST /api/v1/webhooks/razorpay`

Handles Razorpay subscription events. **Every payload is verified** via the
`X-Razorpay-Signature` header — an HMAC-SHA256 of the **raw request body** using the
configured webhook secret, compared in constant time. Unsigned or invalid payloads are
rejected with `400` and never processed.

Supported events:

| Event | Effect |
|-------|--------|
| `subscription.activated` | Sets org `plan` + `plan_status=active`, stores subscription id. Audit: `billing.plan_activated`. |
| `subscription.charged` | Sets `plan_status=active`. Audit: `billing.subscription_charged`. |
| `subscription.cancelled` | Sets `plan_status=cancelled` (org downgraded to Free enforcement). Audit: `billing.plan_cancelled`. |
| `subscription.halted` | Sets `plan_status=halted`. Audit: `billing.plan_halted`. |

The org is resolved from the subscription's `notes.organization_id` (set at checkout
time), falling back to matching the stored `razorpay_subscription_id`.

## Webhook registration in Razorpay

1. In the Razorpay Dashboard (test mode), go to **Settings → Webhooks**.
2. Set the URL to `https://<your-api-host>/api/v1/webhooks/razorpay`.
3. Subscribe to `subscription.activated`, `subscription.charged`,
   `subscription.cancelled`, `subscription.halted`.
4. Copy the generated webhook secret into Vault as `razorpay_webhook_secret`.

## Going live checklist

- Set `BILLING_ENABLED=true` in production (it is off by default for testing builds).
- Confirm the Razorpay account has completed KYC and is **fully activated**.
- Provision live keys via Vault (`razorpay_key_id`, `razorpay_key_secret`).
- Create live Razorpay Plans and update `razorpay_plan_id` in `plans.py`.
- Re-verify webhook signature handling with live payloads (format is identical).