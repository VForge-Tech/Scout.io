# Developer Portal Guide

This guide is for developers integrating Scout.io into their own applications:
using the REST API, managing API keys, and embedding the chat widget. It merges
the previous `GUIDE.md` API reference and `ClientREADME.md` widget integration
into one corrected reference. Setup of the platform itself is covered in
`docs/getting-started/`; the API is also self-documenting at
`http://localhost:8000/docs` (Swagger) and `/redoc`.

## Developer portal pages

| Page | URL | Purpose |
|------|-----|---------|
| Dashboard | `/developer` | Overview & quick actions |
| API Keys | `/developer/api-keys` | Create/revoke API keys |
| API Docs | `/developer/docs` | Interactive API documentation |
| Widget Integration | `/developer/widget` | Generate embed code |
| API Testing | `/developer/api-test` | Test endpoints / connectivity / chatbots |

### API testing page

Three tabs:

- **Internal APIs** — pick any endpoint to call it with your auth.
- **External Connectivity** — "Run Connectivity Test" verifies PostgreSQL,
  Redis, Qdrant, OpenAI, and Anthropic reachability
  (`GET /api/v1/developer/connectivity-test`).
- **Chatbot Test** — select a chatbot, send a message, inspect the full
  pipeline response (`POST /api/v1/developer/test-chatbot/{chatbot_id}`).

## Authentication

JWT bearer tokens:

```bash
# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"..."}'
# -> { access_token, refresh_token }

# Use the token
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <access_token>"
```

- `POST /api/v1/auth/refresh` — rotate access token.
- `POST /api/v1/auth/logout` — revoke the refresh token.
- `GET /api/v1/auth/me` — current user.
- `POST /api/v1/auth/mfa/*` — set up and verify TOTP two-factor auth (see
  `docs/guides/client-guide.md`).

> Accounts are provisioned by a platform admin (seeded via
> `scripts/seed_test_data.py`); there is **no public registration endpoint**.

## API reference

Base URL: `/api/v1` (see `backend/app/api/router.py`).

### Chatbots

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/chatbots` | List org chatbots |
| POST | `/api/v1/chatbots` | Create chatbot (name, behavior tier, sources) |
| GET | `/api/v1/chatbots/{chatbot_id}` | Get chatbot |
| PATCH | `/api/v1/chatbots/{chatbot_id}` | Update chatbot (rename, tier, sources, config) |
| DELETE | `/api/v1/chatbots/{chatbot_id}` | Delete chatbot |

### Knowledge sources

Sources are namespaced under the chatbot that owns them:

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/chatbots/{chatbot_id}/knowledge-sources` | List sources |
| POST | `/api/v1/chatbots/{chatbot_id}/knowledge-sources` | Create source (website / file / sql / api / git) |
| GET | `/api/v1/chatbots/{chatbot_id}/knowledge-sources/{source_id}` | Get source + sync status |
| DELETE | `/api/v1/chatbots/{chatbot_id}/knowledge-sources/{source_id}` | Delete source |
| POST | `/api/v1/chatbots/{chatbot_id}/knowledge-sources/{source_id}/sync` | Trigger sync |

### Policies

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/chatbots/{chatbot_id}/policies` | List policies |
| POST | `/api/v1/chatbots/{chatbot_id}/policies` | Create source_filter / content_filter |
| DELETE | `/api/v1/chatbots/{chatbot_id}/policies/{policy_id}` | Delete policy |

### Widget API (public)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/widget/sessions` | Create session (returns short-lived JWT) |
| POST | `/api/v1/widget/messages` | Send message, get AI response (session token) |

### Developer API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/developer/api-keys` | List API keys |
| POST | `/api/v1/developer/api-keys` | Create API key |
| DELETE | `/api/v1/developer/api-keys/{key_id}` | Revoke API key |
| GET | `/api/v1/developer/widget-snippet` | Get embed code |
| POST | `/api/v1/developer/api-test` | Test any endpoint |
| GET | `/api/v1/developer/connectivity-test` | Check external services |
| GET | `/api/v1/developer/endpoints` | List testable endpoints |
| POST | `/api/v1/developer/test-chatbot/{chatbot_id}` | Full pipeline chatbot test |

### Admin API (platform admins only)

See `docs/guides/admin-guide.md` for the full list. Headline endpoints:
`GET /api/v1/admin/organizations`, `PATCH|DELETE /api/v1/admin/organizations/{org_id}`,
`POST /api/v1/admin/organizations/{org_id}/offboard[/confirm]`,
`GET /api/v1/admin/stats`, `GET /api/v1/admin/audit-logs`,
`GET /api/v1/admin/health`, `GET/PUT /api/v1/admin/system-config`.

## API keys

Keys use the `sco_` prefix and authenticate via header:

```bash
curl -H "X-API-Key: sco_xxxxxxxxxxxx" http://localhost:8000/api/v1/chatbots
```

Create at `/developer/api-keys` or `POST /api/v1/developer/api-keys`; the full
key is shown once at creation. Revoke anytime; all requests are audited.

## Embedding the widget

### 1. Get your embed code

Create a chatbot, then go to **Developer → Widget Integration**
(`/developer/widget`), pick the chatbot and a light/dark theme, and copy the
generated snippet (also available via `GET /api/v1/developer/widget-snippet`).

### 2. Basic embed (plain HTML)

```html
<!-- Scout.io Chat Widget — add before </body> -->
<script src="https://cdn.scout.io/widget/v1/scout-widget.js" defer></script>
<script>
  window.addEventListener('load', function () {
    ScoutWidget.init({
      chatbotId: 'YOUR_CHATBOT_ID',
      apiUrl: 'https://your-scout-instance.com', // or http://localhost:8000 in dev
      theme: 'light' // or 'dark'
    });
  });
</script>
```

### 3. NPM package (React / Next.js / Vue)

```bash
npm install @scout/widget
```

```tsx
import { ChatWidget, ThemeProvider } from '@scout/widget';
import '@scout/widget/styles.css';

function App() {
  return (
    <ThemeProvider theme="light">
      <ChatWidget
        chatbotId="YOUR_CHATBOT_ID"
        apiUrl="https://your-scout-instance.com"
        onMessage={(msg) => console.log('User:', msg)}
        onResponse={(resp) => console.log('Bot:', resp)}
      />
    </ThemeProvider>
  );
}
```

### Configuration

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `chatbotId` | string | Yes | — | Your chatbot's ID |
| `apiUrl` | string | Yes | — | Backend API base URL |
| `theme` | `'light' \| 'dark'` | No | `'light'` | Widget theme |
| `position` | `'bottom-right' \| 'bottom-left'` | No | `'bottom-right'` | Screen position |
| `primaryColor` | string | No | `'#2563eb'` | Brand color (hex) |
| `welcomeMessage` | string | No | `'Hello! How can I help?'` | Initial bot message |
| `placeholder` | string | No | `'Type a message...'` | Input placeholder |
| `showAvatar` | boolean | No | `true` | Show bot avatar |
| `customStyles` | object | No | `{}` | CSS variable overrides |

### Programmatic control

```javascript
ScoutWidget.open();
ScoutWidget.close();
ScoutWidget.sendMessage('Hello from code!');

ScoutWidget.on('message:received', (data) => console.log('User:', data.message));
ScoutWidget.on('response:received', (data) => console.log('Bot:', data.response));

ScoutWidget.destroy(); // SPA navigation
```

Custom theming via CSS variables:

```javascript
ScoutWidget.init({
  chatbotId: 'YOUR_CHATBOT_ID',
  apiUrl: 'https://your-scout-instance.com',
  theme: 'dark',
  primaryColor: '#7c3aed',
  customStyles: {
    '--scout-radius': '12px',
    '--scout-font-family': 'Inter, sans-serif',
    '--scout-shadow': '0 10px 40px rgba(0,0,0,0.15)'
  }
});
```

### Sessions & security

- A session is created automatically on first message
  (`POST /api/v1/widget/sessions`); the session JWT is stored in `localStorage`
  under `scout_widget_session`. Remove that key to reset.
- Sessions expire after 1 hour of inactivity (server-side).
- Widget requests are CORS-restricted, rate-limited, and the session JWT is
  short-lived. Session tokens are separate from user JWTs — users can't be
  impersonated through the widget.

### Troubleshooting

- **Widget not appearing**: check the browser console, verify `chatbotId` and
  `apiUrl`, ensure no CORS errors or ad-blocker interference.
- **Messages not sending**: 401/403 means the session token expired — start a
  new session; verify the chatbot exists and is active.
- **Styling issues**: use `customStyles` to override variables; check for CSS
  conflicts with your site.

## Common workflow

```bash
# 1. Create a chatbot
curl -X POST http://localhost:8000/api/v1/chatbots \
  -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"name":"Support Bot","behaviour":"balanced"}'

# 2. Add a knowledge source
curl -X POST http://localhost:8000/api/v1/chatbots/{chatbot_id}/knowledge-sources \
  -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"name":"FAQ","type":"website","content_url":"https://example.com/faq"}'

# 3. Test the pipeline
curl -X POST http://localhost:8000/api/v1/developer/test-chatbot/{chatbot_id} \
  -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"message":"What do you do?"}'

# 4. Embed the widget (or POST /widget/sessions + /widget/messages directly)
```

## Related

- `docs/integrations/llm-providers.md` — model tiers and fallback behavior
- `docs/integrations/webhooks.md` — event notifications
- `docs/architecture/system-architecture.md` — pipeline internals
- `sdk/` — JavaScript and Python SDK READMEs