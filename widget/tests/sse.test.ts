import { beforeEach, describe, expect, it, vi } from 'vitest';
import { consumeSSE } from '../src/lib/sse';

function streamFrom(text: string): ReadableStream<Uint8Array> {
  const bytes = new TextEncoder().encode(text);
  return new ReadableStream({
    start(controller) {
      controller.enqueue(bytes);
      controller.close();
    },
  });
}

describe('consumeSSE', () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
  });

  it('parses data: frames and invokes onEvent per event', async () => {
    const events: any[] = [];
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        body: streamFrom(
          'data: {"type":"meta","session_id":"s"}\n\n' +
            'data: {"type":"token","content":"Hel"}\n' +
            'data: {"type":"token","content":"lo"}\n\n' +
            'data: {"type":"done","reply":"Hello"}\n\n',
        ),
      }),
    );

    await consumeSSE('http://x/stream', { method: 'POST' }, (evt) => events.push(evt));

    expect(events.map((e) => e.type)).toEqual(['meta', 'token', 'token', 'done']);
    expect(events[1].content).toBe('Hel');
    expect(events[3].reply).toBe('Hello');
  });

  it('handles tokens split across read() chunks', async () => {
    const events: any[] = [];
    const encoder = new TextEncoder();
    const bytes = encoder.encode(
      'data: {"type":"token","content":"one"}\n\n' +
        'data: {"type":"token","content":"two"}\n\n',
    );
    const stream = new ReadableStream({
      start(controller) {
        // Deliver one byte at a time to force buffer-split handling.
        for (const byte of bytes) controller.enqueue(new Uint8Array([byte]));
        controller.close();
      },
    });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, body: stream }));

    await consumeSSE('http://x/stream', {}, (evt) => events.push(evt));
    expect(events.map((e) => e.content)).toEqual(['one', 'two']);
  });

  it('throws on non-ok responses with the API detail', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        json: async () => ({ detail: 'nope' }),
      }),
    );
    await expect(consumeSSE('http://x/stream', {}, () => {})).rejects.toThrow('nope');
  });
});