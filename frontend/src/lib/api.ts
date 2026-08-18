export function resolveApiBase(raw?: string): string {
  const trimmed = (raw || 'http://localhost:8000').replace(/\/+$/, '');
  return trimmed.endsWith('/api/v1') ? trimmed : `${trimmed}/api/v1`;
}

export async function extractApiError(res: Response): Promise<string> {
  const text = await res.text().catch(() => '');
  if (!text) return `Request failed (${res.status} ${res.statusText})`;
  try {
    const data = JSON.parse(text);
    if (data && typeof data.detail === 'string') return data.detail;
    if (data && typeof data.detail === 'object' && Array.isArray(data.detail)) {
      return data.detail.map((d: any) => d.msg || JSON.stringify(d)).join('; ');
    }
    return text;
  } catch {
    return text || `Request failed (${res.status} ${res.statusText})`;
  }
}

const API_BASE = resolveApiBase(process.env.NEXT_PUBLIC_API_URL);

interface RequestOptions {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
  formData?: FormData;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const isFormData = !!options.formData;
  const headers: Record<string, string> = {
    ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
    ...options.headers,
  };

  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('access_token');
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
  }

  const res = await fetch(`${API_BASE}${path}`, {
    method: options.method || 'GET',
    headers,
    body: options.formData
      ? options.formData
      : options.body
        ? JSON.stringify(options.body)
        : undefined,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    // Handle auth errors
    if (res.status === 401 || res.status === 403) {
      if (typeof window !== 'undefined') {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/auth/login';
      }
    }
    throw new Error(error.detail || 'Request failed');
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: 'POST', body }),
  put: <T>(path: string, body?: unknown) => request<T>(path, { method: 'PUT', body }),
  patch: <T>(path: string, body?: unknown) => request<T>(path, { method: 'PATCH', body }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
  upload: <T>(path: string, file: File) => {
    const form = new FormData();
    form.append('file', file);
    return request<T>(path, {
      method: 'POST',
      headers: {}, // do NOT set Content-Type; let the browser set the multipart boundary
      formData: form,
    });
  },
};

export interface SSEEvent {
  type: string;
  [key: string]: unknown;
}

/**
 * POST to a Server-Sent-Events endpoint and invoke `onEvent` for each JSON
 * `data:` frame as it arrives. Used by the Streaming Playground to render
 * tokens as they stream in. Throws on non-2xx responses / network failures.
 */
export async function streamRequest(
  path: string,
  body: unknown,
  onEvent: (event: SSEEvent) => void,
): Promise<void> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('access_token');
    if (token) headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  });

  if (!res.ok || !res.body) {
    throw new Error(await extractApiError(res));
  }

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

// Helper for pages that need to fetch arrays with proper error handling
export async function fetchArray<T>(path: string): Promise<T[]> {
  try {
    const data = await api.get<T[]>(path);
    return Array.isArray(data) ? data : [];
  } catch (e) {
    console.error(`Failed to fetch ${path}:`, e);
    return [];
  }
}
