# Client Guide (Organization Admin)

This guide is for organization administrators — the people who set up and run a
Scout.io workspace for their team: creating chatbots, uploading knowledge,
watching analytics, and managing billing. It assumes no technical background.
Platform administrators (Scout.io staff) should read `docs/guides/admin-guide.md`.

## Signing in

Go to your Scout.io dashboard and sign in at `/auth/login` with your email and
password. If your account has two-factor authentication (2FA) enabled, you'll
enter a verification code from your authenticator app after your password.

## The dashboard

After signing in you land on **Overview** (`/dashboard`), which shows:

- Live organization info and usage stats (message volume, tokens, plan).
- Quick actions and a **Get started** checklist:
  1. Create your first chatbot
  2. Add your first knowledge source
  3. Test the widget
  4. Invite a teammate

Each checklist item links to the page where you do that step. The list hides
once all four are complete.

## Chatbots (`/dashboard/chatbots`)

A chatbot is a configurable AI assistant backed by your knowledge sources.

**Create a chatbot**: go to **Chatbots → New**, give it a name, and pick a
**model tier**:

| Tier | Best for |
|------|----------|
| Fast | Quick answers, low cost |
| Balanced | Default; best everyday mix of speed and quality |
| Accurate | Complex reasoning, highest quality |

**Edit a chatbot**: rename it, change its tier, attach/detach knowledge
sources, and configure its **policies** (what it can and can't do/answer). You
can also preview and copy the **widget snippet** (the code that embeds the chat
on your website).

Deleting a chatbot asks for confirmation before it's removed.

## Knowledge sources (`/dashboard/knowledge-sources`)

Knowledge sources are the documents and data your chatbots answer from. Add a
source per chatbot:

- **Website** — a URL to scrape.
- **File upload** — PDF, Markdown, DOCX, or TXT.
- **SQL / API / Git** connectors for structured or code-based data.

The list shows every source across your chatbots with a live **sync status**
(Synced / Failed / Syncing / Pending) and last-synced time. If a sync fails,
click **Retry**. Deleting a source warns you that it removes that source from
every chatbot using it.

> After your first source finishes syncing, you may see a small thumbs
> up/down feedback prompt — that's how the Scout.io team improves the product.

## Policies (`/dashboard/policies`)

Policies control chatbot behavior. Two types are supported:

- **Source filter** — restrict the chatbot to a specific set of knowledge
  sources (`allowed_source_ids`).
- **Content filter** — block sensitive terms from responses (`blocked_terms`,
  e.g. "password", "ssn", "credit card").

Policies can be attached to a specific chatbot or created at the organization
level (`/policies`), where they apply broadly.

## Analytics (`/dashboard/analytics`)

Org-scoped charts for your account only:

- **Message volume and sessions** over time (7 / 30 / 90-day ranges).
- **Token usage** over time, broken out per chatbot when you have more than one.
- **Feedback summary** (thumbs up/down).
- **Per-source usage** (admin role only) — which knowledge sources are actually
  being retrieved from.

## Team (`/dashboard/team`)

Invite teammates to your organization. Adding a second member completes the
onboarding checklist.

## Billing (`/dashboard/billing`)

See your current plan, usage vs. plan limits (tokens, chatbots, messages,
knowledge sources), and the renewal date. You can upgrade plans, change plans
(downgrades apply at the end of the current cycle), view invoices, or cancel
your subscription. New accounts without a subscription see a clear **Trial /
Free** state. A warning banner appears if you cross 80% of your included
usage.

> Billing may show "Billing is disabled in this environment" — that's the
> feature flag in non-production deployments. See
> `docs/integrations/billing-razorpay.md`.

## Settings (`/dashboard/settings`)

- **Organization name** — rename your organization.
- **Two-Factor Authentication** — set up or remove 2FA on your account. When
  enabling, scan the QR code with your authenticator app (or enter the manual
  key), enter a verification code, and save your recovery codes somewhere safe.
  Use the codes if you ever lose your authenticator device; you can regenerate
  them at any time.

## Embedding the widget on your website

1. Go to **Developer → Widget Integration** (`/developer/widget`).
2. Pick a chatbot, choose a theme (light/dark), and copy the generated embed
   snippet.
3. Paste it into your website before `</body>`.

End users then chat with your chatbot through the widget. See
`docs/guides/developer-portal-guide.md` for the full integration options
(position, colors, welcome message, events).

## Getting help

- API reference: `docs/guides/developer-portal-guide.md`
- Troubleshooting and local setup: `docs/getting-started/`
- Report issues via the project's issue tracker.