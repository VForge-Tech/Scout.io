import React from 'react';

export interface ThemeProviderProps {
  theme?: Record<string, string>;
  children?: React.ReactNode;
}

export const ThemeProvider: React.FC<ThemeProviderProps> = ({ children }) => {
  return <>{children}</>;
};
