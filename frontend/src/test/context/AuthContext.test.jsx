import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { AuthProvider, useAuth } from '../../context/AuthContext'
import { LanguageProvider } from '../../context/LanguageContext'
import { server } from '../mocks/server'
import { http, HttpResponse } from 'msw'

function wrapper({ children }) {
  return (
    <BrowserRouter>
      <LanguageProvider>
        <AuthProvider>{children}</AuthProvider>
      </LanguageProvider>
    </BrowserRouter>
  )
}

describe('AuthContext', () => {
  beforeEach(() => {
    localStorage.clear()
    window.history.replaceState({}, '', '/')
  })

  it('sets user when valid token in localStorage', async () => {
    localStorage.setItem('token', 'valid-token')

    const { result } = renderHook(() => useAuth(), { wrapper })

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.isAuthenticated).toBe(true)
    expect(result.current.user.username).toBe('testuser')
  })

  it('sets isAuthenticated false with no token', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper })

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.user).toBeNull()
  })

  it('login stores token and fetches user', async () => {
    // Override login endpoint to accept the URLSearchParams body
    // (MSW+jsdom has a known incompatibility with URLSearchParams body)
    server.use(
      http.post('http://localhost:5173/api/auth/login', async () => {
        return HttpResponse.json({
          access_token: 'mock-token-123',
          token_type: 'bearer',
        })
      })
    )

    const { result } = renderHook(() => useAuth(), { wrapper })

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // Patch fetch to convert URLSearchParams body to string before calling real fetch
    const origFetch = globalThis.fetch
    globalThis.fetch = async (url, init = {}) => {
      if (init.body instanceof URLSearchParams) {
        init = { ...init, body: init.body.toString() }
      }
      return origFetch(url, init)
    }

    try {
      await act(async () => {
        await result.current.login('testuser', 'pass123')
      })

      expect(localStorage.getItem('token')).toBe('mock-token-123')
      expect(result.current.isAuthenticated).toBe(true)
    } finally {
      globalThis.fetch = origFetch
    }
  })

  it('logout clears token and user', async () => {
    localStorage.setItem('token', 'valid-token')

    const { result } = renderHook(() => useAuth(), { wrapper })

    await waitFor(() => {
      expect(result.current.isAuthenticated).toBe(true)
    })

    act(() => {
      result.current.logout()
    })

    expect(localStorage.getItem('token')).toBeNull()
    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.user).toBeNull()
  })

  it('extracts token from ?token= URL param (OAuth redirect)', async () => {
    window.history.replaceState({}, '', '/?token=oauth-token-abc')

    const { result } = renderHook(() => useAuth(), { wrapper })

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(localStorage.getItem('token')).toBe('oauth-token-abc')
    expect(result.current.isAuthenticated).toBe(true)
  })

  it('does not store token on ?error= URL param', async () => {
    window.history.replaceState({}, '', '/?error=oauth_failed')

    server.use(
      http.get('http://localhost:5173/api/auth/me', () => {
        return HttpResponse.json({ detail: 'Not authenticated' }, { status: 401 })
      })
    )

    const { result } = renderHook(() => useAuth(), { wrapper })

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.isAuthenticated).toBe(false)
  })
})
