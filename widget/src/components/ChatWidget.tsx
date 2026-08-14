import React, { useState, useEffect, useRef, useCallback } from 'react';
import { ThemeProvider, useTheme, Theme } from './ThemeProvider';
import { MessageList } from './MessageList';
import { InputBox } from './InputBox';
import type { CSSProperties } from 'react';

export interface ChatWidgetProps {
  chatbotId: string;
  apiUrl?: string;
  wsUrl?: string;
  theme?: 'light' | 'dark' | Theme;
  position?: 'bottom-right' | 'bottom-left';
  primaryColor?: string;
  welcomeMessage?: string;
  placeholder?: string;
  showBranding?: boolean;
  onError?: (error: Error) => void;
  onMessageSent?: (message: string) => void;
  onMessageReceived?: (message: string) => void;
}

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  metadata?: Record<string, unknown>;
}

interface WidgetSession {
  session_id: string;
  token: string;
}

interface WidgetMessageResponse {
  reply: string;
  session_id: string;
}

const generateId = () => `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

const adjustColor = (color: string, amount: number): string => {
  const hex = color.replace('#', '');
  const num = parseInt(hex, 16);
  const r = Math.max(0, Math.min(255, (num >> 16) + amount));
  const g = Math.max(0, Math.min(255, ((num >> 8) & 0x00FF) + amount));
  const b = Math.max(0, Math.min(255, (num & 0x0000FF) + amount));
  return `#${((r << 16) | (g << 8) | b).toString(16).padStart(6, '0')}`;
};

const ChatWidgetInner: React.FC<ChatWidgetProps> = ({
  chatbotId,
  apiUrl = 'http://localhost:8000',
  wsUrl,
  theme = 'light',
  position = 'bottom-right',
  primaryColor,
  welcomeMessage = 'Hello! How can I help you today?',
  placeholder = 'Type a message...',
  showBranding = true,
  onError,
  onMessageSent,
  onMessageReceived,
}) => {
  const { theme: themeObj, mode, toggleTheme, setTheme } = useTheme();
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [session, setSession] = useState<WidgetSession | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [unreadCount, setUnreadCount] = useState(0);
  const widgetRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const effectiveTheme = primaryColor
    ? {
        ...themeObj,
        colors: {
          ...themeObj.colors,
          primary: primaryColor,
          primaryHover: adjustColor(primaryColor, -20),
          userMessage: primaryColor,
        },
      }
    : themeObj;

  const createSession = useCallback(async () => {
    try {
      const res = await fetch(`${apiUrl}/api/v1/widget/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chatbot_id: chatbotId }),
      });
      if (!res.ok) throw new Error('Failed to create session');
      const data: WidgetSession = await res.json();
      setSession(data);
      return data;
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to create session';
      setError(errorMsg);
      onError?.(err instanceof Error ? err : new Error(errorMsg));
      return null;
    }
  }, [apiUrl, chatbotId, onError]);

  const sendMessage = useCallback(async (content: string) => {
    if (!session) {
      const newSession = await createSession();
      if (!newSession) return;
    }

    const userMessage: Message = {
      id: generateId(),
      role: 'user',
      content,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);
    setError(null);
    onMessageSent?.(content);

    try {
      const res = await fetch(`${apiUrl}/api/v1/widget/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${session?.token}`,
        },
        body: JSON.stringify({ content, metadata: {} }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'Failed to send message');
      }

      const data: WidgetMessageResponse = await res.json();

      const botMessage: Message = {
        id: generateId(),
        role: 'assistant',
        content: data.reply,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, botMessage]);
      onMessageReceived?.(data.reply);

      if (!isOpen && !isMinimized) {
        setUnreadCount((c) => c + 1);
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to send message';
      setError(errorMsg);
      onError?.(err instanceof Error ? err : new Error(errorMsg));

      const errorMessage: Message = {
        id: generateId(),
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  }, [session, apiUrl, isOpen, isMinimized, onMessageSent, onMessageReceived, onError]);

  const toggleWidget = () => {
    if (isMinimized) {
      setIsMinimized(false);
      setIsOpen(true);
    } else {
      setIsOpen(!isOpen);
      if (isOpen) setIsMinimized(true);
    }
    setUnreadCount(0);
  };

  const closeWidget = () => {
    setIsOpen(false);
    setIsMinimized(false);
  };

  const minimizeWidget = () => {
    setIsMinimized(true);
    setIsOpen(false);
  };

  const clearError = () => setError(null);

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Escape') closeWidget();
  };

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('scout-widget-theme') as 'light' | 'dark' | null;
      if (saved && saved !== mode) setTheme(saved);
    }
  }, [mode, setTheme]);

  const positionStyles = {
    bottom: '24px',
    [position === 'bottom-right' ? 'right' : 'left']: '24px',
    zIndex: 9999,
  } as CSSProperties;

  const buttonStyles: CSSProperties = {
    position: 'fixed',
    ...positionStyles,
    width: '56px',
    height: '56px',
    borderRadius: '50%',
    backgroundColor: effectiveTheme.colors.primary,
    color: '#fff',
    border: 'none',
    cursor: 'pointer',
    boxShadow: effectiveTheme.shadows.lg,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: `transform ${effectiveTheme.transitions.normal}, box-shadow ${effectiveTheme.transitions.fast}`,
    animation: isMinimized ? 'pulse 2s infinite' : 'none',
  };

  const widgetStyles: CSSProperties = {
    position: 'fixed',
    ...positionStyles,
    width: '380px',
    maxWidth: 'calc(100vw - 48px)',
    height: '500px',
    maxHeight: 'calc(100vh - 96px)',
    backgroundColor: effectiveTheme.colors.background,
    borderRadius: effectiveTheme.radii.lg,
    boxShadow: effectiveTheme.shadows.lg,
    border: `1px solid ${effectiveTheme.colors.border}`,
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
    opacity: isOpen ? 1 : 0,
    transform: isOpen ? 'scale(1) translateY(0)' : 'scale(0.95) translateY(20px)',
    pointerEvents: isOpen ? 'auto' : 'none',
    transition: `opacity ${effectiveTheme.transitions.normal}, transform ${effectiveTheme.transitions.normal}`,
  };

  if (typeof window === 'undefined') return null;

  // Inject global styles for animations
  useEffect(() => {
    const style = document.createElement('style');
    style.textContent = `
      @keyframes pulse {
        0%, 100% { box-shadow: 0 0 0 0 rgba(37, 99, 235, 0.4); }
        50% { box-shadow: 0 0 0 10px rgba(37, 99, 235, 0); }
      }
      @keyframes slideUp {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
      }
    `;
    document.head.appendChild(style);
    return () => {
      document.head.removeChild(style);
    };
  }, []);

  return (
    <>

      {!isOpen && !isMinimized && (
        <button
          onClick={toggleWidget}
          style={buttonStyles}
          aria-label="Open chat"
          aria-expanded="false"
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
        </button>
      )}

      {(isOpen || isMinimized) && (
        <>
          <div
            style={{
              position: 'fixed',
              inset: 0,
              backgroundColor: 'rgba(0,0,0,0.3)',
              zIndex: 9998,
              opacity: isOpen ? 1 : 0,
              pointerEvents: isOpen ? 'auto' : 'none',
              transition: `opacity ${effectiveTheme.transitions.normal}`,
            }}
            onClick={closeWidget}
            aria-hidden="true"
          />
          <div ref={widgetRef} style={widgetStyles} role="dialog" aria-label="Chat widget" aria-modal="true">
            <header
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: `${effectiveTheme.spacing.md} ${effectiveTheme.spacing.lg}`,
                backgroundColor: effectiveTheme.colors.surface,
                borderBottom: `1px solid ${effectiveTheme.colors.border}`,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: effectiveTheme.spacing.sm }}>
                <div
                  style={{
                    width: '32px',
                    height: '32px',
                    borderRadius: effectiveTheme.radii.full,
                    backgroundColor: effectiveTheme.colors.primary,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#fff',
                  }}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                  </svg>
                </div>
                <div>
                  <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 600, color: effectiveTheme.colors.text }}>Scout Assistant</h3>
                  <span style={{ fontSize: '11px', color: effectiveTheme.colors.textMuted }}>Powered by Scout.io</span>
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: effectiveTheme.spacing.xs }}>
                <button
                  onClick={toggleTheme}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    width: '32px',
                    height: '32px',
                    borderRadius: effectiveTheme.radii.full,
                    backgroundColor: 'transparent',
                    border: `1px solid ${effectiveTheme.colors.border}`,
                    color: effectiveTheme.colors.text,
                    cursor: 'pointer',
                    transition: `background-color ${effectiveTheme.transitions.fast}`,
                  }}
                  aria-label={`Switch to ${mode === 'light' ? 'dark' : 'light'} mode`}
                >
                  {mode === 'light' ? (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <circle cx="12" cy="12" r="5" />
                      <line x1="12" y1="1" x2="12" y2="3" />
                      <line x1="12" y1="21" x2="12" y2="23" />
                      <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
                      <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
                      <line x1="1" y1="12" x2="3" y2="12" />
                      <line x1="21" y1="12" x2="23" y2="12" />
                      <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
                      <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
                    </svg>
                  ) : (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
                    </svg>
                  )}
                </button>
                <button
                  onClick={minimizeWidget}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    width: '32px',
                    height: '32px',
                    borderRadius: effectiveTheme.radii.full,
                    backgroundColor: 'transparent',
                    border: `1px solid ${effectiveTheme.colors.border}`,
                    color: effectiveTheme.colors.text,
                    cursor: 'pointer',
                    transition: `background-color ${effectiveTheme.transitions.fast}`,
                  }}
                  aria-label="Minimize"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="5" y1="12" x2="19" y2="12" />
                  </svg>
                </button>
                <button
                  onClick={closeWidget}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    width: '32px',
                    height: '32px',
                    borderRadius: effectiveTheme.radii.full,
                    backgroundColor: 'transparent',
                    border: `1px solid ${effectiveTheme.colors.border}`,
                    color: effectiveTheme.colors.text,
                    cursor: 'pointer',
                    transition: `background-color ${effectiveTheme.transitions.fast}`,
                  }}
                  aria-label="Close"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                </button>
              </div>
            </header>

            <MessageList
              messages={messages}
              isLoading={isLoading}
            />

            {error && (
              <div
                style={{
                  padding: `${effectiveTheme.spacing.sm} ${effectiveTheme.spacing.md}`,
                  backgroundColor: `${effectiveTheme.colors.error}15`,
                  borderTop: `1px solid ${effectiveTheme.colors.error}`,
                  color: effectiveTheme.colors.error,
                  fontSize: '12px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}
                role="alert"
              >
                <span>{error}</span>
                <button
                  onClick={clearError}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: effectiveTheme.colors.error,
                    cursor: 'pointer',
                    fontSize: '16px',
                    lineHeight: 1,
                    padding: 0,
                  }}
                  aria-label="Dismiss error"
                >
                  ×
                </button>
              </div>
            )}

            <div
              style={{
                padding: effectiveTheme.spacing.md,
                backgroundColor: effectiveTheme.colors.surface,
                borderTop: `1px solid ${effectiveTheme.colors.border}`,
              }}
            >
              <InputBox
                onSend={sendMessage}
                disabled={isLoading || !session}
                placeholder={placeholder}
              />
            </div>

            {showBranding && (
              <div
                style={{
                  padding: effectiveTheme.spacing.xs,
                  textAlign: 'center',
                  fontSize: '10px',
                  color: effectiveTheme.colors.textMuted,
                }}
              >
                Powered by <a href="https://scout.io" target="_blank" rel="noopener noreferrer" style={{ color: effectiveTheme.colors.primary, textDecoration: 'none' }}>Scout.io</a>
              </div>
            )}
          </div>
        </>
      )}

      {isMinimized && (
        <button
          onClick={() => { setIsMinimized(false); setIsOpen(true); }}
          style={{
            position: 'fixed',
            ...positionStyles,
            width: '56px',
            height: '56px',
            borderRadius: '50%',
            backgroundColor: effectiveTheme.colors.primary,
            color: '#fff',
            border: 'none',
            cursor: 'pointer',
            boxShadow: effectiveTheme.shadows.lg,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
            animation: 'pulse 2s infinite',
          }}
          aria-label="Open chat"
          aria-expanded="true"
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
          {unreadCount > 0 && (
            <span
              style={{
                position: 'absolute',
                top: '4px',
                right: '4px',
                minWidth: '18px',
                height: '18px',
                borderRadius: '9px',
                backgroundColor: effectiveTheme.colors.error,
                color: '#fff',
                fontSize: '10px',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '0 4px',
              }}
            >
              {unreadCount > 9 ? '9+' : unreadCount}
            </span>
          )}
        </button>
      )}
    </>
  );
};

export const ChatWidget: React.FC<ChatWidgetProps> = (props) => {
  return (
    <ThemeProvider theme={props.theme}>
      <ChatWidgetInner {...props} />
    </ThemeProvider>
  );
};

export const initWidget = (config: ChatWidgetProps) => {
  if (typeof window === 'undefined') return;

  const container = document.createElement('div');
  container.id = 'scout-widget-root';
  document.body.appendChild(container);

  const root = React.createElement(ChatWidget, config);
  import('react-dom/client').then(({ createRoot }) => {
    const reactRoot = createRoot(container);
    reactRoot.render(root);
  });

  return {
    destroy: () => {
      container.remove();
    },
    open: () => {},
    close: () => {},
  };
};

declare global {
  interface Window {
    ScoutWidget: {
      init: typeof initWidget;
    };
  }
}

if (typeof window !== 'undefined') {
  window.ScoutWidget = { init: initWidget };
}