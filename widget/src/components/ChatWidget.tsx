import React from 'react';

export interface ChatWidgetProps {
  apiUrl?: string;
  wsUrl?: string;
  theme?: Record<string, string>;
}

export const ChatWidget: React.FC<ChatWidgetProps> = () => {
  return null;
};
