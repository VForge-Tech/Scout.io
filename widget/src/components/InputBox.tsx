import React, { useState, useRef, useEffect, KeyboardEvent, FormEvent } from 'react';
import { useTheme } from './ThemeProvider';

export interface InputBoxProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export const InputBox: React.FC<InputBoxProps> = ({ onSend, disabled = false, placeholder = 'Type a message...' }) => {
  const { theme } = useTheme();
  const [value, setValue] = useState('');
  const [height, setHeight] = useState(44);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      const newHeight = Math.min(textareaRef.current.scrollHeight, 120);
      setHeight(newHeight);
      textareaRef.current.style.height = `${newHeight}px`;
    }
  }, [value]);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = value.trim();
    if (trimmed && !disabled) {
      onSend(trimmed);
      setValue('');
      setHeight(44);
      if (textareaRef.current) {
        textareaRef.current.style.height = '44px';
      }
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: theme.spacing.xs }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-end',
          gap: theme.spacing.sm,
          backgroundColor: theme.colors.surface,
          border: `1px solid ${theme.colors.border}`,
          borderRadius: theme.radii.lg,
          padding: theme.spacing.sm,
          paddingBottom: theme.spacing.xs,
          transition: `border-color ${theme.transitions.fast}, box-shadow ${theme.transitions.fast}`,
        }}
      >
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder={placeholder}
          rows={1}
          style={{
            flex: 1,
            minHeight: '44px',
            maxHeight: '120px',
            resize: 'none',
            border: 'none',
            outline: 'none',
            background: 'transparent',
            color: theme.colors.text,
            fontSize: '14px',
            lineHeight: 1.5,
            fontFamily: 'inherit',
            padding: 0,
            width: '100%',
            overflow: 'hidden',
          }}
          aria-label="Message input"
        />
        <button
          type="submit"
          disabled={disabled || !value.trim()}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '36px',
            height: '36px',
            borderRadius: theme.radii.full,
            backgroundColor: value.trim() && !disabled ? theme.colors.primary : theme.colors.border,
            color: value.trim() && !disabled ? '#fff' : theme.colors.textMuted,
            border: 'none',
            cursor: value.trim() && !disabled ? 'pointer' : 'not-allowed',
            transition: `background-color ${theme.transitions.fast}, transform ${theme.transitions.fast}`,
            flexShrink: 0,
          }}
          aria-label="Send message"
        >
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <line x1="22" y1="2" x2="11" y2="13" />
            <polygon points="22 2 15 22 11 13 2 9 22 2" />
          </svg>
        </button>
      </div>
      <p
        style={{
          fontSize: '11px',
          color: theme.colors.textMuted,
          textAlign: 'center',
          margin: 0,
        }}
      >
        Press Enter to send, Shift+Enter for new line
      </p>
    </form>
  );
};