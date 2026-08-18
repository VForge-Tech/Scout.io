export interface SSEEvent {
  type: string;
  [key: string]: unknown;
}

/**
 * POST to a Server-Sent-Events endpoint and invoke `onEvent` for each
 * JSON `data:` frame as it arrives (token-by-token).
 *
 * Throws on non-2xx responses or network failures so the caller can fall back
 * to the non-streaming endpoint.
 */
export async function consumeSSE(
  url: string,
  init: RequestInit,
  onEvent: (event: SSEEvent) => void,
): Promise<void> {
  const res = await fetch(url, init);
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const data = await res.json();
      if (data && typeof data.detail === 'string') detail = data.detail;
    } catch {
      // ignore parse failures; use the status-based message
    }
    throw new Error(detail);
  }
  if (!res.body) throw new Error('Streaming is not supported by this browser');

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const frames = buffer.split('\n\n');
    buffer = frames.pop() ?? '';
    for (const frame of frames) {
      const dataLines = frame
        .split('\n')
        .filter((line) => line.startsWith('data:'))
        .map((line) => line.slice(5).trim());
      for (const data of dataLines) {
        if (!data) continue;
        try {
          onEvent(JSON.parse(data) as SSEEvent);
        } catch {
          // skip malformed events
        }
      }
    }
  }
}