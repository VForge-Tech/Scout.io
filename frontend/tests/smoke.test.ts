import { describe, it, expect, vi, afterEach } from 'vitest';
import { api, fetchArray, extractApiError } from '../src/lib/api';

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('api client smoke tests', () => {
  it('exposes the expected request helpers', () => {
    expect(api.get).toBeTypeOf('function');
    expect(api.post).toBeTypeOf('function');
    expect(api.put).toBeTypeOf('function');
    expect(api.patch).toBeTypeOf('function');
    expect(api.delete).toBeTypeOf('function');
    expect(api.upload).toBeTypeOf('function');
  });

  it('fetchArray returns [] on request failure instead of throwing', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 500, statusText: 'boom', json: async () => ({ detail: 'boom' }) }));
    const result = await fetchArray('/chatbots');
    expect(result).toEqual([]);
  });

  it('fetchArray returns the array on success', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => [{ id: 'cb_1' }] }));
    const result = await fetchArray('/chatbots');
    expect(result).toEqual([{ id: 'cb_1' }]);
  });

  it('extractApiError returns detail from JSON error bodies', async () => {
    const res = { ok: false, status: 409, text: async () => JSON.stringify({ detail: 'Email already registered' }) } as Response;
    expect(await extractApiError(res)).toBe('Email already registered');
  });

  it('extractApiError returns raw text for non-JSON bodies', async () => {
    const res = { ok: false, status: 500, text: async () => 'Internal Server Error' } as Response;
    expect(await extractApiError(res)).toBe('Internal Server Error');
  });

  it('extractApiError returns a fallback when the body is empty', async () => {
    const res = { ok: false, status: 500, statusText: 'boom', text: async () => '' } as Response;
    expect(await extractApiError(res)).toBe('Request failed (500 boom)');
  });
});