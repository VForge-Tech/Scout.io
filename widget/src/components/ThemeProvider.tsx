import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

export interface Theme {
  colors: {
    primary: string;
    primaryHover: string;
    background: string;
    surface: string;
    surfaceHover: string;
    border: string;
    text: string;
    textSecondary: string;
    textMuted: string;
    userMessage: string;
    userMessageText: string;
    botMessage: string;
    botMessageText: string;
    error: string;
    success: string;
  };
  radii: {
    sm: string;
    md: string;
    lg: string;
    full: string;
  };
  spacing: {
    xs: string;
    sm: string;
    md: string;
    lg: string;
    xl: string;
  };
  shadows: {
    sm: string;
    md: string;
    lg: string;
  };
  transitions: {
    fast: string;
    normal: string;
  };
}

export interface ThemeProviderProps {
  theme?: 'light' | 'dark' | Theme;
  children?: ReactNode;
}

const lightTheme: Theme = {
  colors: {
    primary: '#2563eb',
    primaryHover: '#1d4ed8',
    background: '#ffffff',
    surface: '#f8fafc',
    surfaceHover: '#f1f5f9',
    border: '#e2e8f0',
    text: '#0f172a',
    textSecondary: '#475569',
    textMuted: '#94a3b8',
    userMessage: '#2563eb',
    userMessageText: '#ffffff',
    botMessage: '#f1f5f9',
    botMessageText: '#0f172a',
    error: '#ef4444',
    success: '#22c55e',
  },
  radii: {
    sm: '4px',
    md: '8px',
    lg: '12px',
    full: '9999px',
  },
  spacing: {
    xs: '4px',
    sm: '8px',
    md: '16px',
    lg: '24px',
    xl: '32px',
  },
  shadows: {
    sm: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
    md: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
    lg: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
  },
  transitions: {
    fast: '150ms ease',
    normal: '200ms ease',
  },
};

const darkTheme: Theme = {
  colors: {
    primary: '#3b82f6',
    primaryHover: '#60a5fa',
    background: '#0f172a',
    surface: '#1e293b',
    surfaceHover: '#334155',
    border: '#334155',
    text: '#f8fafc',
    textSecondary: '#cbd5e1',
    textMuted: '#64748b',
    userMessage: '#3b82f6',
    userMessageText: '#ffffff',
    botMessage: '#1e293b',
    botMessageText: '#f8fafc',
    error: '#f87171',
    success: '#4ade80',
  },
  radii: {
    sm: '4px',
    md: '8px',
    lg: '12px',
    full: '9999px',
  },
  spacing: {
    xs: '4px',
    sm: '8px',
    md: '16px',
    lg: '24px',
    xl: '32px',
  },
  shadows: {
    sm: '0 1px 2px 0 rgb(0 0 0 / 0.3)',
    md: '0 4px 6px -1px rgb(0 0 0 / 0.4), 0 2px 4px -2px rgb(0 0 0 / 0.3)',
    lg: '0 10px 15px -3px rgb(0 0 0 / 0.4), 0 4px 6px -4px rgb(0 0 0 / 0.3)',
  },
  transitions: {
    fast: '150ms ease',
    normal: '200ms ease',
  },
};

interface ThemeContextType {
  theme: Theme;
  mode: 'light' | 'dark';
  toggleTheme: () => void;
  setTheme: (theme: 'light' | 'dark') => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const ThemeProvider: React.FC<ThemeProviderProps> = ({ theme = 'light', children }) => {
  const [mode, setMode] = useState<'light' | 'dark'>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('scout-widget-theme') as 'light' | 'dark' | null;
      if (saved) return saved;
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    return 'light';
  });

  const [resolvedTheme, setResolvedTheme] = useState<Theme>(lightTheme);

  useEffect(() => {
    if (typeof theme === 'object') {
      setResolvedTheme(theme);
    } else {
      const newTheme = theme === 'dark' ? darkTheme : lightTheme;
      setResolvedTheme(newTheme);
      setMode(theme);
      localStorage.setItem('scout-widget-theme', theme);
    }
  }, [theme]);

  const toggleTheme = () => {
    const newMode = mode === 'light' ? 'dark' : 'light';
    setMode(newMode);
    setResolvedTheme(newMode === 'dark' ? darkTheme : lightTheme);
    localStorage.setItem('scout-widget-theme', newMode);
  };

  const setTheme = (newMode: 'light' | 'dark') => {
    setMode(newMode);
    setResolvedTheme(newMode === 'dark' ? darkTheme : lightTheme);
    localStorage.setItem('scout-widget-theme', newMode);
  };

  return (
    <ThemeContext.Provider value={{ theme: resolvedTheme, mode, toggleTheme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = (): ThemeContextType => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};