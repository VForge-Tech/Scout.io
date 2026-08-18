import { useEffect, useRef } from 'react';

export function usePolling(callback: () => void | Promise<void>, intervalMs = 15000) {
  const savedCallback = useRef(callback);
  savedCallback.current = callback;

  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      if (cancelled) return;
      try {
        await savedCallback.current();
      } catch {
        // polling must never crash the page; keep the last rendered data
      }
    };
    const id = setInterval(tick, intervalMs);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [intervalMs]);
}