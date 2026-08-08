import React from 'react';
import { useTheme } from './ThemeProvider';

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  metadata?: Record<string, unknown>;
}

export interface MessageListProps {
  messages: Message[];
  isLoading?: boolean;
}

const MessageBubble: React.FC<{ message: Message; theme: ReturnType<typeof useTheme>['theme'] }> = ({
  message,
  theme,
}) => {
  const isUser = message.role === 'user';
  const alignStyle = isUser ? { marginLeft: 'auto', marginRight: 0 } : { marginLeft: 0, marginRight: 'auto' };

  const bubbleStyle: React.CSSProperties = {
    ...alignStyle,
    maxWidth: '85%',
    padding: `${theme.spacing.sm} ${theme.spacing.md}`,
    borderRadius: isUser
      ? `${theme.radii.lg} ${theme.radii.lg} ${theme.radii.sm} ${theme.radii.lg}`
      : `${theme.radii.lg} ${theme.radii.lg} ${theme.radii.lg} ${theme.radii.sm}`,
    backgroundColor: isUser ? theme.colors.userMessage : theme.colors.botMessage,
    color: isUser ? theme.colors.userMessageText : theme.colors.botMessageText,
    boxShadow: theme.shadows.sm,
    wordWrap: 'break-word',
    lineHeight: 1.5,
    fontSize: '14px',
    animation: 'fadeIn 0.2s ease-out',
  };

  const timeStyle: React.CSSProperties = {
    marginTop: theme.spacing.xs,
    fontSize: '10px',
    opacity: 0.7,
    textAlign: isUser ? 'right' : 'left',
  };

  return (
    <>
      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
      <div style={bubbleStyle}>
        {message.content}
        <div style={timeStyle}>
          {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </div>
      </div>
    </>
  );
};

const TypingIndicator: React.FC<{ theme: ReturnType<typeof useTheme>['theme'] }> = ({ theme }) => (
  <>
    <style>{`
      @keyframes bounce {
        0%, 80%, 100% { transform: scale(0); }
        40% { transform: scale(1); }
      }
    `}</style>
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: theme.spacing.xs,
        padding: `${theme.spacing.sm} ${theme.spacing.md}`,
        maxWidth: '60px',
        backgroundColor: theme.colors.botMessage,
        borderRadius: `${theme.radii.lg} ${theme.radii.lg} ${theme.radii.lg} ${theme.radii.sm}`,
        boxShadow: theme.shadows.sm,
      }}
    >
      <span
        style={{
          width: '6px',
          height: '6px',
          borderRadius: theme.radii.full,
          backgroundColor: theme.colors.textMuted,
          animation: 'bounce 1.4s infinite ease-in-out both',
        }}
      />
      <span
        style={{
          width: '6px',
          height: '6px',
          borderRadius: theme.radii.full,
          backgroundColor: theme.colors.textMuted,
          animation: 'bounce 1.4s infinite ease-in-out both 0.16s',
        }}
      />
      <span
        style={{
          width: '6px',
          height: '6px',
          borderRadius: theme.radii.full,
          backgroundColor: theme.colors.textMuted,
          animation: 'bounce 1.4s infinite ease-in-out both 0.32s',
        }}
      />
    </div>
  </>
);

export const MessageList: React.FC<MessageListProps> = ({ messages, isLoading }) => {
  const { theme } = useTheme();
  const messagesEndRef = React.useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  React.useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  if (messages.length === 0 && !isLoading) {
    return (
      <div
        style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: theme.spacing.xl,
          color: theme.colors.textMuted,
          textAlign: 'center',
        }}
      >
        <svg
          width="48"
          height="48"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          style={{ marginBottom: theme.spacing.md, opacity: 0.5 }}
        >
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
        <p style={{ fontSize: '14px', marginBottom: theme.spacing.xs }}>Start a conversation</p>
        <p style={{ fontSize: '12px', opacity: 0.7 }}>Type a message below to begin</p>
      </div>
    );
  }

  return (
    <div
      style={{
        flex: 1,
        overflowY: 'auto',
        padding: theme.spacing.md,
        display: 'flex',
        flexDirection: 'column',
        gap: theme.spacing.sm,
        backgroundColor: theme.colors.background,
      }}
      role="log"
      aria-live="polite"
      aria-label="Chat messages"
    >
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} theme={theme} />
      ))}
      {isLoading && <TypingIndicator theme={theme} />}
      <div ref={messagesEndRef} />
    </div>
  );
};