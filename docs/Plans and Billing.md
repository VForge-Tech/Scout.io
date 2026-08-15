# Plans, Pricing & Billing (Razorpay)

Scout.io uses [Razorpay Subscriptions](https://razorpay.com/docs/subscriptions/) for
plan management. Razorpay's self-serve business signup works from India without the
invite-only friction Stripe currently has. **Important:** confirm the account is fully
activated (KYC complete) before assuming live mode will work later — keep test-mode keys
in place until then.

## Plan tiers

Defined in `backend/app/core/billing/plans.py`. Limits are enforced at the API layer
in `backend/app/core/billing/limits.py`.

| Plan   | Price / month (INR) | Chatbots | Messages / month | Knowledge sources | Included tokens / month |
|--------|---------------------|----------|------------------|-------------------|-------------------------|
| Free   | ₹0                  | 1        | 1,000            | 5                 | 100,000 |
| Starter| ₹2,999             | 3        | 10,000           | 20                | 1,000,000 |
| Growth | ₹9,999             | 10       | 100,000          | 100               | 5,000,000 |
| Scale  | ₹29,999            | 50       | 1,000,000        | 500               | 25,000,000 |

Razorpay plan IDs (`plan_starter`, `plan_growth`, `plan_scale`) are created in the
Razorpay Dashboard (test mode) and referenced by the `razorpay_plan_id` field in each
`PlanTier`. The `free` plan has no Razorpay plan and is the default for new orgs.

Each paid plan also defines a usage-based component: `included_monthly_tokens` (how much
token usage is covered by the subscription each calendar month) and
`overage_price_paise_per_1k` (the per-1,000-token overage price in paise). See
[Usage-based billing](#usage-based-billing) below.

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

Response includes:

- `usage` — chatbot / message / knowledge-source counts vs `limits`.
- `usage_billing` — the latest `UsageBillingRecord` for the current calendar month
  (`total_tokens`, `estimated_cost`, `overage_tokens`, `overage_cost`,
  `reported_to_razorpay`), or `null` until the daily billing task has run.
- `warning` — a `billing.usage_soft_limit` warning banner (fired at 80% of included
  token usage), or `null`. The billing page renders it as an orange banner.
- `limits.included_monthly_tokens` — the plan's included token allowance.

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

## Usage-based billing

### How usage is recorded

Every generation in `ResponsePipeline` records an `LLMUsage` row
(`backend/app/models/llm_usage.py`) after the AI router call, capturing the model
actually used plus provider-reported (or estimated) prompt/completion token counts.
Estimated cost is computed from `backend/app/core/billing/pricing.py` (per-model
paise-per-1K prices) and stored in `LLMUsage.cost`. This is the **only** place
`LLMUsage` is written.

### Daily aggregation (Celery beat)

`backend/app/tasks/billing_tasks.py` runs on a Celery beat schedule (03:00 UTC daily).
For each org with usage in the current calendar month it:

1. Aggregates `LLMUsage` into prompt/completion/total tokens + estimated cost.
2. Upserts a `UsageBillingRecord` (`backend/app/models/usage_billing_record.py`, unique
   per `organization_id` + `YYYY-MM` period) storing the totals, the computed overage
   (usage beyond `included_monthly_tokens`), and whether it was reported.
3. For paid plans whose usage exceeds the included allowance, reports the overage to
   Razorpay as a **subscription add-on** (`subscription.createAddon`) billed on the next
   invoice. Razorpay has no native usage-metering API; if the add-on cannot be created
   (no subscription, no overage price, or API failure), the overage is **tracked
   internally** (`reported_to_razorpay=false`) and surfaced on the billing page so it can
   be invoiced manually at period end.
4. Fires a `billing.usage_soft_limit` `AnalyticsEvent` once per period when usage reaches
   80% of the plan's included tokens; the billing endpoint surfaces it as a `warning`.

Overage pricing comes from `plans.py` (`overage_price_paise_per_1k`). Add-on amounts are
capped per charge by `MAX_OVERAGE_TOKENS_PER_ADDON` in `pricing.py`; the remainder is
deferred and can be billed in a follow-up add-on.

### Deploying the beat

The billing beat and worker are separate compose services (`celery_billing_beat`,
`celery_billing_worker`) in `docker/docker-compose.prod.yml`. The worker app includes
both `billing_tasks` and `analytics_tasks`.

## Subscription management

Razorpay has **no self-serve customer portal**, so subscription management is done
in-house against its subscription APIs. Endpoints are org-scoped under
`/api/v1/organizations/me/billing/`:

- `GET /subscription` — returns `SubscriptionDetail`. New signups with no
  `razorpay_subscription_id` get `has_subscription=false` (the frontend shows a
  clear trial/free state rather than an error). Otherwise it fetches the Razorpay
  subscription, maps `plan_id` back to a plan key, and lists the invoice history
  (`client.invoice.all`) — invoice listing is best-effort and won't fail the detail view.
- `POST /subscription/change-plan` — upgrades/downgrades via `subscription.edit`
  with `schedule_change_at` ∈ {`now`, `cycle_end`}. The org's plan is updated in the
  DB immediately (Razorpay sends no plan-change webhook); limits reflect it at once.
- `POST /subscription/cancel` — calls `subscription.cancel`. Default
  `cancel_at_cycle_end=true` keeps the org **active** until the paid period ends
  (the `subscription.cancelled` webhook flips enforcement at cycle end); passing
  `cancel_at_cycle_end=false` flags `plan_status="cancelled"` immediately.
- The frontend `/dashboard/billing` renders the current plan + renewal date +
  payment method, invoice history, usage-vs-limits progress bars, a plan comparison
  grid (checkout-session for new subscriptions, change-plan for existing ones), the
  80% usage warning banner, and a Trial/Free state for orgs without a subscription.

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
- Review `included_monthly_tokens` / `overage_price_paise_per_1k` in `plans.py` and the
  per-model prices in `pricing.py` against your negotiated rates before enabling usage
  billing.
- Re-verify webhook signature handling with live payloads (format is identical).