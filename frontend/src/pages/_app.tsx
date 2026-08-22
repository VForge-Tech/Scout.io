import type { AppProps } from 'next/app';
import { useEffect, useState } from 'react';
import '../styles/globals.css';

export default function App({ Component, pageProps }: AppProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    if (typeof window !== 'undefined') {
      (window as any).__NEXT_BASE_PATH__ = process.env.NEXT_PUBLIC_BASE_PATH || '';
    }
  }, []);

  if (!mounted) {
    return <Component {...pageProps} />;
  }

  return <Component {...pageProps} />;
}
