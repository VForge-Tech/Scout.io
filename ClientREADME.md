# Scout.io Widget Integration Guide

## Overview

The Scout.io Chat Widget is a lightweight, embeddable React component that allows you to add an AI-powered chatbot to any website. The widget communicates with your Scout.io backend via REST API and WebSocket.

## Quick Start

### 1. Get Your Embed Code

After creating a chatbot in the Scout.io Developer Portal, go to **Developer → Widget Integration** to generate your embed snippet.

### 2. Basic Embedding

Add this to your HTML page (preferably before `</body>`):

```html
<!-- Scout.io Chat Widget -->
<script src="https://cdn.scout.io/widget/v1/scout-widget.js" defer></script>
<script>
  window.addEventListener('load', function() {
    ScoutWidget.init({
      chatbotId: 'YOUR_CHATBOT_ID',  // Replace with your chatbot ID
      apiUrl: 'https://your-scout-instance.com',  // Your Scout.io API URL
      theme: 'light'  // or 'dark'
    });
  });
</script>
```

### 3. NPM Installation (React/Next.js/Vue/etc.)

```bash
npm install @scout-io/widget
```

```tsx
import { ChatWidget, ThemeProvider } from '@scout-io/widget';
import '@scout-io/widget/styles.css'; // or import your own theme

function App() {
  return (
    <ThemeProvider theme="light">
      <ChatWidget
        chatbotId="YOUR_CHATBOT_ID"
        apiUrl="https://your-scout-instance.com"
        onMessage={(message) => console.log('User:', message)}
        onResponse={(response) => console.log('Bot:', response)}
      />
    </ThemeProvider>
  );
}
```

## Configuration Options

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `chatbotId` | string | Yes | - | Your chatbot's unique identifier |
| `apiUrl` | string | Yes | - | Base URL of your Scout.io API (e.g., `https://api.yourdomain.com`) |
| `theme` | `'light' \| 'dark'` | No | `'light'` | Widget theme |
| `position` | `'bottom-right' \| 'bottom-left'` | No | `'bottom-right'` | Widget position on screen |
| `primaryColor` | string | No | `'#2563eb'` | Primary brand color (hex) |
| `welcomeMessage` | string | No | `'Hi! How can I help?'` | Initial message from bot |
| `placeholder` | string | No | `'Type a message...'` | Input placeholder text |
| `showAvatar` | boolean | No | `true` | Show bot avatar |
| `customStyles` | object | No | `{}` | Custom CSS overrides |

## Advanced Usage

### Programmatic Control

```javascript
// Open/close widget
ScoutWidget.open();
ScoutWidget.close();

// Send message programmatically
ScoutWidget.sendMessage('Hello from code!');

// Listen for events
ScoutWidget.on('message:received', (data) => {
  console.log('User message:', data.message);
});

ScoutWidget.on('response:received', (data) => {
  console.log('Bot response:', data.response);
});

// Destroy widget (SPA navigation)
ScoutWidget.destroy();
```

### Custom Theme

```javascript
ScoutWidget.init({
  chatbotId: 'YOUR_CHATBOT_ID',
  apiUrl: 'https://your-scout-instance.com',
  theme: 'dark',
  primaryColor: '#7c3aed', // Purple
  customStyles: {
    '--scout-radius': '12px',
    '--scout-font-family': 'Inter, sans-serif',
    '--scout-shadow': '0 10px 40px rgba(0,0,0,0.15)'
  }
});
```

### React Integration with Hooks

```tsx
import { useScoutWidget } from '@scout-io/widget/react';

function ChatButton() {
  const { open, close, isOpen, sendMessage } = useScoutWidget({
    chatbotId: 'YOUR_CHATBOT_ID',
    apiUrl: 'https://your-scout-instance.com'
  });

  return (
    <button onClick={isOpen ? close : open}>
      {isOpen ? 'Close Chat' : 'Open Chat'}
    </button>
  );
}
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Your Website                           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              ScoutWidget (React/UMD)                │   │
│  │  ┌─────────┐  ┌─────────┐  ┌────────────────────┐  │   │
│  │  │ Header  │  │Messages │  │    Input Box       │  │   │
│  │  └─────────┘  └─────────┘  └────────────────────┘  │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTPS/WS
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Scout.io Backend                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  Widget API  │  │  AI Router   │  │ Knowledge Engine │  │
│  │  /sessions   │  │  (LiteLLM)   │  │    (Qdrant)      │  │
│  │  /messages   │  └──────────────┘  └──────────────────┘  │
│  └──────────────┘                                           │
└─────────────────────────────────────────────────────────────┘
```

## API Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/widget/sessions` | POST | Create new chat session |
| `/api/v1/widget/messages` | POST | Send message, get AI response |
| `/api/v1/widget/messages` | GET | Get message history (optional) |

## Session Management

- Sessions are created automatically on first message
- Session token is stored in `localStorage` (key: `scout_widget_session`)
- Sessions expire after 1 hour of inactivity (configurable server-side)
- To reset: `localStorage.removeItem('scout_widget_session')`

## Security

- All communication over HTTPS
- Widget sessions use short-lived JWT tokens
- CORS configured for your domain
- Rate limiting: 30 requests/minute per session
- Content Security Policy compatible

## Browser Support

| Browser | Version |
|---------|---------|
| Chrome | 90+ |
| Firefox | 88+ |
| Safari | 14+ |
| Edge | 90+ |
| Mobile Safari | 14+ |
| Chrome Android | 90+ |

## Troubleshooting

### Widget Not Appearing
1. Check browser console for errors
2. Verify `chatbotId` is correct
3. Ensure `apiUrl` is accessible (no CORS errors)
4. Check ad blockers aren't blocking the script

### Messages Not Sending
1. Verify authentication token hasn't expired
2. Check network tab for 401/403 responses
3. Ensure chatbot exists and is active

### Styling Issues
1. Check for CSS conflicts with your site
2. Use `customStyles` to override variables
3. Ensure no global `box-sizing` conflicts

## Migration from v0

```diff
// Old v0
ScoutWidget.mount('#chat-container', { botId: 'xxx' });

// New v1
ScoutWidget.init({ chatbotId: 'xxx', apiUrl: '...' });
```

## Support

- **Documentation**: https://docs.scout.io/widget
- **API Reference**: https://api.scout.io/docs
- **Issues**: GitHub Issues
- **Email**: support@scout.io

## License

MIT License - see LICENSE file for details.