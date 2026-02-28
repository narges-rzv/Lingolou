import type { LoginResponse } from './types';

const API_BASE = '/api';

interface ApiFetchOptions extends Omit<RequestInit, 'body'> {
  json?: unknown;
  body?: BodyInit;
}

function parseErrorDetail(err: { detail?: unknown }, fallback: string): string {
  if (Array.isArray(err.detail)) {
    return err.detail.map((e: { msg?: string }) => e.msg ?? 'Invalid input').join('. ');
  }
  if (typeof err.detail === 'string') return err.detail;
  return fallback;
}

export async function apiFetch<T>(path: string, options: ApiFetchOptions = {}): Promise<T> {
  const token = localStorage.getItem('token');
  const headers: Record<string, string> = { ...(options.headers as Record<string, string>) };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  if (options.json !== undefined) {
    headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(options.json);
    delete options.json;
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

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
