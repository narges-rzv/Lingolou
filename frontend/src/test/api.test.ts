import { describe, it, expect, beforeEach } from 'vitest'
import { server } from './mocks/server'
import { http, HttpResponse } from 'msw'

import { apiFetch, publicApiFetch, registerRequest, RETRY_CONFIG } from '../api'

describe('apiFetch', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('adds Bearer token from localStorage', async () => {
    localStorage.setItem('token', 'my-test-token')
    let capturedAuth: string | null = null
    server.use(
      http.get('http://localhost:5173/api/test', ({ request }) => {
        capturedAuth = request.headers.get('Authorization')
        return HttpResponse.json({ ok: true })
      })
    )

    await apiFetch<{ ok: boolean }>('/test')
    expect(capturedAuth).toBe('Bearer my-test-token')
  })

  it('handles 401 by clearing token', async () => {
    localStorage.setItem('token', 'expired-token')

    server.use(
      http.get('http://localhost:5173/api/test', () => {
        return HttpResponse.json({ detail: 'Unauthorized' }, { status: 401 })
      })
    )

    await expect(apiFetch('/test')).rejects.toThrow('Unauthorized')
    expect(localStorage.getItem('token')).toBeNull()
  })

  it('parses JSON error responses', async () => {
    server.use(
      http.get('http://localhost:5173/api/test', () => {
        return HttpResponse.json({ detail: 'Custom error message' }, { status: 400 })
      })
    )

    await expect(apiFetch('/test')).rejects.toThrow('Custom error message')
  })

  it('sends JSON body when json option is provided', async () => {
    let capturedBody: unknown = null
    let capturedContentType: string | null = null
    server.use(
      http.post('http://localhost:5173/api/test', async ({ request }) => {
        capturedContentType = request.headers.get('Content-Type')
        capturedBody = await request.json()
        return HttpResponse.json({ ok: true })
      })
    )

    await apiFetch('/test', { method: 'POST', json: { foo: 'bar' } })
    expect(capturedContentType).toBe('application/json')
    expect(capturedBody).toEqual({ foo: 'bar' })
  })
})

describe('publicApiFetch', () => {
  it('does NOT add auth header', async () => {
    localStorage.setItem('token', 'should-not-be-sent')
    let capturedAuth: string | null = null
    server.use(
      http.get('http://localhost:5173/api/test', ({ request }) => {
        capturedAuth = request.headers.get('Authorization')
        return HttpResponse.json({ ok: true })
      })
    )

    await publicApiFetch('/test')
    expect(capturedAuth).toBeNull()
  })
})

describe('loginRequest', () => {
  it('sends URL-encoded form data', async () => {
    const body = new URLSearchParams({ username: 'user', password: 'pass' })
    expect(body.get('username')).toBe('user')
    expect(body.get('password')).toBe('pass')
    expect(body.toString()).toBe('username=user&password=pass')
  })
})

describe('apiFetch 503 retry', () => {
  const originalBackoff = RETRY_CONFIG.initialBackoffMs

  beforeEach(() => {
    localStorage.clear()
    RETRY_CONFIG.initialBackoffMs = 1 // Fast backoff for tests
  })

  afterEach(() => {
    RETRY_CONFIG.initialBackoffMs = originalBackoff
  })

  it('retries on 503 and succeeds', async () => {
    let callCount = 0
    server.use(
      http.get('http://localhost:5173/api/retry-test', () => {
        callCount++
        if (callCount <= 2) {
          return HttpResponse.json({ detail: 'Service starting up' }, { status: 503 })
        }
        return HttpResponse.json({ ok: true })
      })
    )

    const result = await apiFetch<{ ok: boolean }>('/retry-test')
    expect(result.ok).toBe(true)
    expect(callCount).toBe(3)
  })

  it('gives up after max retries', async () => {
    server.use(
      http.get('http://localhost:5173/api/always-503', () => {
        return HttpResponse.json({ detail: 'Service starting up' }, { status: 503 })
      })
    )

    await expect(apiFetch('/always-503')).rejects.toThrow()
  })

  it('does not retry non-503 errors', async () => {
    let callCount = 0
    server.use(
      http.get('http://localhost:5173/api/bad-request', () => {
        callCount++
        return HttpResponse.json({ detail: 'Bad request' }, { status: 400 })
      })
    )

    await expect(apiFetch('/bad-request')).rejects.toThrow('Bad request')
    expect(callCount).toBe(1)
  })

  it('calls onRetry callback with attempt number', async () => {
    let callCount = 0
    const retryAttempts: number[] = []

    server.use(
      http.get('http://localhost:5173/api/retry-callback', () => {
        callCount++
        if (callCount <= 2) {
          return HttpResponse.json({ detail: 'Starting up' }, { status: 503 })
        }
        return HttpResponse.json({ ok: true })
      })
    )

    await apiFetch<{ ok: boolean }>('/retry-callback', {
      onRetry: (attempt) => retryAttempts.push(attempt),
    })

    expect(retryAttempts).toEqual([1, 2])
  })
})

describe('registerRequest', () => {
  it('sends JSON body', async () => {
    let capturedBody: unknown = null
    server.use(
      http.post('http://localhost:5173/api/auth/register', async ({ request }) => {
        capturedBody = await request.json()
        return HttpResponse.json({ id: 1, email: 'a@b.com', username: 'user' })
      })
    )

    await registerRequest('a@b.com', 'user', 'pass123')
    expect(capturedBody).toEqual({ email: 'a@b.com', username: 'user', password: 'pass123' })
  })
})
