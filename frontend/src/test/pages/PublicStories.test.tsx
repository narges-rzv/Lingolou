import { describe, it, expect, beforeEach, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '../test-utils'
import { server } from '../mocks/server'
import { http, HttpResponse } from 'msw'
import PublicStories from '../../pages/PublicStories'
import type { PublicStoryListItem } from '../../types'

describe('PublicStories', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('fetches and displays public stories', async () => {
    render(<PublicStories />)

    await waitFor(() => {
      expect(screen.getByText('Test Story')).toBeInTheDocument()
    })
  })

  it('shows BudgetBanner', async () => {
    render(<PublicStories />)

    await waitFor(() => {
      expect(screen.getByText(/Community pool/)).toBeInTheDocument()
    })
  })

  it('shows hero description and language selector', async () => {
    render(<PublicStories />)

    await waitFor(() => {
      expect(screen.getByText(/helps you create an audio file/)).toBeInTheDocument()
    })

    expect(screen.getByRole('combobox')).toBeInTheDocument()
  })

  it('shows "Log in" when not authenticated', async () => {
    render(<PublicStories />)

    await waitFor(() => {
      expect(screen.getByText('Log in')).toBeInTheDocument()
    })
  })

  it('shows "My Stories" column header when authenticated', async () => {
    localStorage.setItem('token', 'valid-token')
    render(<PublicStories />)

    await waitFor(() => {
      expect(screen.getByText('My Stories')).toBeInTheDocument()
    })
  })

  it('shows empty state when no stories', async () => {
    server.use(
      http.get('http://localhost:5173/api/public/stories', () => {
        return HttpResponse.json([])
      })
    )

    render(<PublicStories />)

    await waitFor(() => {
      expect(screen.getByText(/No public stories/)).toBeInTheDocument()
    })
  })

  it('language selector is present with default language', async () => {
    render(<PublicStories />)

    await waitFor(() => {
      expect(screen.getByText('Test Story')).toBeInTheDocument()
    })

    const select = screen.getByRole('combobox')
    expect((select as HTMLSelectElement).value).toBe('')
  })

  it('loads more stories when sentinel becomes visible', async () => {
    let observerCallback: IntersectionObserverCallback | null = null
    const mockDisconnect = vi.fn()
    const mockObserve = vi.fn()

    vi.stubGlobal('IntersectionObserver', class {
      constructor(cb: IntersectionObserverCallback) {
        observerCallback = cb
      }
      observe = mockObserve
      disconnect = mockDisconnect
      unobserve = vi.fn()
    })

    const makeStory = (id: string, title: string): PublicStoryListItem => ({
      id,
      title,
      description: 'desc',
      language: 'Persian (Farsi)',
      world_id: null,
      world_name: null,
      status: 'completed',
      chapter_count: 1,
      upvotes: 0,
      downvotes: 0,
      created_at: '2024-01-01T00:00:00',
      owner_name: 'user',
      owner_id: 1,
    })

    const page1 = Array.from({ length: 20 }, (_, i) => makeStory(`story-${i}`, `Story ${i}`))
    const page2 = [makeStory('story-20', 'Story From Page 2')]

    let callCount = 0
    server.use(
      http.get('http://localhost:5173/api/public/stories', () => {
        callCount++
        if (callCount === 1) return HttpResponse.json(page1)
        return HttpResponse.json(page2)
      })
    )

    render(<PublicStories />)

    await waitFor(() => {
      expect(screen.getByText('Story 0')).toBeInTheDocument()
    })

    // Simulate sentinel becoming visible
    observerCallback!(
      [{ isIntersecting: true } as IntersectionObserverEntry],
      {} as IntersectionObserver,
    )

    await waitFor(() => {
      expect(screen.getByText('Story From Page 2')).toBeInTheDocument()
    })

    // Page 1 stories should still be present
    expect(screen.getByText('Story 0')).toBeInTheDocument()

    vi.unstubAllGlobals()
  })
})
