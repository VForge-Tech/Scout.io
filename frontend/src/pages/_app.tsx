import type { AppProps } from 'next/app';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import '../styles/globals.css';

export default function App({ Component, pageProps }: AppProps) {
  const [mounted, setMounted] = useState(false);
  const router = useRouter();

  useEffect(() => {
    setMounted(true);
    if (typeof window !== 'undefined') {
      (window as any).__NEXT_BASE_PATH__ = process.env.NEXT_PUBLIC_BASE_PATH || '';
      
      // SPA GitHub Pages redirect handling
      // Check if we were redirected from 404.html with route in query string
      const params = new URLSearchParams(window.location.search);
      const route = params.get('route') || params.get('path');
      if (route) {
        // Clean up the URL and navigate to the actual route
        const cleanUrl = window.location.pathname + (window.location.hash || '');
        window.history.replaceState({}, '', cleanUrl);
        router.replace(decodeURIComponent(route) + window.location.hash, undefined, { shallow: true });
      }
    }
  }, [router]);

  if (!mounted) {
    return <Component {...pageProps} />;
  }

  return <Component {...pageProps} />;
}
