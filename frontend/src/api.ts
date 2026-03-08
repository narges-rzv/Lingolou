import type { LoginResponse } from './types';

const API_BASE = '/api';
export const RETRY_CONFIG = {
  maxRetries: 5,
  initialBackoffMs: 1000,
};

interface ApiFetchOptions extends Omit<RequestInit, 'body'> {
  json?: unknown;
  body?: BodyInit;
  onRetry?: (attempt: number) => void;
}

function parseErrorDetail(err: { detail?: unknown }, fallback: string): string {
  if (Array.isArray(err.detail)) {
    return err.detail.map((e: { msg?: string }) => e.msg ?? 'Invalid input').join('. ');
  }
  if (typeof err.detail === 'string') return err.detail;
  return fallback;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function apiFetch<T>(path: string, options: ApiFetchOptions = {}): Promise<T> {
  const token = localStorage.getItem('token');
  const headers: Record<string, string> = { ...(options.headers as Record<string, string>) };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // Prepare body from json option (only once, before retry loop)
  let body: BodyInit | undefined = options.body;
  if (options.json !== undefined) {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(options.json);
  }

  const { json: _json, onRetry, ...fetchOptions } = options;

  for (let attempt = 0; attempt <= RETRY_CONFIG.maxRetries; attempt++) {
    const res = await fetch(`${API_BASE}${path}`, { ...fetchOptions, headers, body });

    if (res.status === 503 && attempt < RETRY_CONFIG.maxRetries) {
      const backoff = RETRY_CONFIG.initialBackoffMs * Math.pow(2, attempt);
      onRetry?.(attempt + 1);
      await sleep(backoff);
      continue;
    }

    if (res.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
      throw new Error('Unauthorized');
    }

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(parseErrorDetail(err, 'Request failed'));
    }

    if (res.status === 204) return null as T;
    return res.json() as Promise<T>;
  }

  // Should not reach here, but satisfy TypeScript
  throw new Error('Request failed after retries');
}

export async function publicApiFetch<T>(path: string, options: ApiFetchOptions = {}): Promise<T> {
  const headers: Record<string, string> = { ...(options.headers as Record<string, string>) };

  if (options.json !== undefined) {
    headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(options.json);
    delete options.json;
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(parseErrorDetail(err, 'Request failed'));
  }

  if (res.status === 204) return null as T;
  return res.json() as Promise<T>;
}

export async function loginRequest(username: string, password: string): Promise<LoginResponse> {
  const body = new URLSearchParams({ username, password });
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(parseErrorDetail(err, 'Login failed'));
  }

  return res.json() as Promise<LoginResponse>;
}

export async function registerRequest(email: string, username: string, password: string): Promise<unknown> {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, username, password }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(parseErrorDetail(err, 'Registration failed'));
  }

  return res.json();
}
