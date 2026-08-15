import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import React from 'react';
import { ThemeProvider, useTheme } from '../src/components/ThemeProvider';

function Probe() {
  const { mode } = useTheme();
  return <span data-testid="probe">{mode}</span>;
}

describe('ThemeProvider smoke test', () => {
  it('renders children within the provider', () => {
    const { getByTestId } = render(
      <ThemeProvider theme="light">
        <Probe />
      </ThemeProvider>,
    );
    expect(getByTestId('probe').textContent).toBe('light');
  });

  it('defaults to light mode when no theme is given', () => {
    const { getByTestId } = render(
      <ThemeProvider>
        <Probe />
      </ThemeProvider>,
    );
    expect(getByTestId('probe').textContent).toBe('light');
  });
});