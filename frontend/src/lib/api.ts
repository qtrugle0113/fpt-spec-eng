import type { components } from './api.generated';

export type Connection = components['schemas']['Connection'];
export type ConnectionCreate = components['schemas']['ConnectionCreate'];
export type ConnectionPatch = components['schemas']['ConnectionPatch'];
export type ConnectionPage = components['schemas']['ConnectionPage'];
export type TestResult = components['schemas']['TestResult'];
type ErrorBody = components['schemas']['ErrorResponse']['error'];

export function newIdempotencyKey(): string {
  if (typeof crypto.randomUUID === 'function') return crypto.randomUUID();
  // getRandomValues is also available on local HTTP origins. Preserve UUID v4
  // entropy and variant bits without requiring a secure-context-only API.
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = Array.from(bytes, byte => byte.toString(16).padStart(2, '0')).join('');
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

export class APIError extends Error {
  constructor(public status: number, public detail: ErrorBody) { super(detail.message); }
}

function errorBody(value: unknown): value is { error: ErrorBody } {
  if (typeof value !== 'object' || value === null || !('error' in value)) return false;
  const error = value.error;
  return typeof error === 'object' && error !== null && 'message' in error && typeof error.message === 'string'
    && 'code' in error && typeof error.code === 'string' && 'request_id' in error && typeof error.request_id === 'string';
}

export async function requestJSON<T>(path: string, options: { method?: string; body?: unknown; form?: FormData; key?: string; etag?: string; signal?: AbortSignal } = {}) {
  const headers: Record<string, string> = { Accept: 'application/json' };
  if (options.body !== undefined) headers['Content-Type'] = 'application/json';
  if (options.etag) headers['If-Match'] = options.etag;
  if (options.key) headers['Idempotency-Key'] = options.key;
  const response = await fetch('/api/v1' + path, {
    method: options.method ?? 'GET', headers, credentials: 'same-origin', cache: 'no-store',
    signal: options.signal ? AbortSignal.any([options.signal, AbortSignal.timeout(35_000)]) : AbortSignal.timeout(35_000),
    body: options.form ?? (options.body === undefined ? undefined : JSON.stringify(options.body)),
  });
  let data: unknown;
  if (response.status !== 204) {
    try { data = await response.json(); }
    catch {
      if (response.status === 413) throw new Error('Upload exceeds the allowed size.');
      throw new Error('The service could not complete the request. Check saved results before retrying.');
    }
  }
  if (!response.ok) {
    if (errorBody(data)) throw new APIError(response.status, data.error);
    throw new Error('The service returned an unexpected response.');
  }
  return { data: data as T, etag: response.headers.get('ETag') };
}

export const listConnections = async (filters: { search: string; database_type: string; status: string; offset: number }, signal?: AbortSignal) => {
  const query = new URLSearchParams({ limit: '50', offset: String(filters.offset) });
  for (const key of ['search', 'database_type', 'status'] as const) if (filters[key]) query.set(key, filters[key]);
  return (await requestJSON<ConnectionPage>('/connections?' + query, { signal })).data;
};
export const getConnection = async (id: string) => requestJSON<Connection>('/connections/' + encodeURIComponent(id));
export const createConnection = async (body: ConnectionCreate) => requestJSON<Connection>('/connections', { method: 'POST', body });
export const patchConnection = async (id: string, etag: string, body: ConnectionPatch) =>
  requestJSON<Connection>('/connections/' + encodeURIComponent(id), { method: 'PATCH', body, etag });
export const deleteConnection = async (id: string, etag: string) =>
  requestJSON<undefined>('/connections/' + encodeURIComponent(id), { method: 'DELETE', etag });
export const testConnection = async (id: string) => requestJSON<TestResult>('/connections/' + encodeURIComponent(id) + '/test', { method: 'POST' });

export async function pollOperation(id: string, signal: AbortSignal, timeoutMs = 120_000) {
  const deadline = Date.now() + timeoutMs;
  let interval = 1000;
  while (!signal.aborted && Date.now() < deadline) {
    const { data } = await requestJSON<components['schemas']['Operation']>('/operations/' + encodeURIComponent(id), { signal });
    if (['SUCCEEDED', 'PARTIALLY_SUCCEEDED', 'FAILED', 'NEEDS_RECONCILIATION'].includes(data.state)) return data;
    await new Promise<void>((resolve, reject) => {
      const abort = () => { clearTimeout(timer); reject(new DOMException('Request cancelled.', 'AbortError')); };
      const timer = setTimeout(() => { signal.removeEventListener('abort', abort); resolve(); }, interval);
      signal.addEventListener('abort', abort, { once: true });
      if (signal.aborted) abort();
    });
    interval = Math.min(5000, interval + 1000);
  }
  throw new Error(signal.aborted ? 'Request cancelled.' : 'The operation is taking longer than expected. Check its current status before retrying.');
}
