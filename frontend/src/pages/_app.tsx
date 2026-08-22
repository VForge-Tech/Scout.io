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
      // https://github.com/rafgraph/spa-github-pages
      const redirectData = sessionStorage.getItem('spa-github-pages-redirect');
      if (redirectData) {
        sessionStorage.removeItem('spa-github-pages-redirect');
        const { path, search, hash } = JSON.parse(redirectData);
        router.replace(path + search + hash, undefined, { shallow: true });
      }
    }
  }, [router]);

  if (!mounted) {
    return <Component {...pageProps} />;
  }

  return <Component {...pageProps} />;
}
