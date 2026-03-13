import { describe, it, expect, beforeEach } from 'vitest'
import { waitFor } from '@testing-library/react'
import { render } from '../test-utils'
import { server } from '../mocks/server'
import { http, HttpResponse } from 'msw'
import AudioPlayer from '../../components/AudioPlayer'

const BASE = 'http://localhost:5173/api'

describe('AudioPlayer', () => {
  beforeEach(() => {
    localStorage.setItem('token', 'valid-token')
  })

  it('fetches audio URL and renders audio element', async () => {
    server.use(
      http.get(`${BASE}/stories/:storyId/chapters/:num/audio`, () => {
        return HttpResponse.json({ url: 'https://example.com/audio.mp3' })
      })
    )

    const { container } = render(
      <AudioPlayer storyId="test-story" chapterNumber={1} />
    )

    await waitFor(() => {
      const audio = container.querySelector('audio')
      expect(audio).toBeInTheDocument()
      expect(audio?.getAttribute('src')).toBe('https://example.com/audio.mp3')
    })
  })

  it('uses public endpoint when isPublic is true', async () => {
    server.use(
      http.get(`${BASE}/public/stories/:storyId/chapters/:num/audio`, () => {
        return HttpResponse.json({ url: 'https://example.com/public-audio.mp3' })
      })
    )

    const { container } = render(
      <AudioPlayer storyId="test-story" chapterNumber={1} isPublic />
    )

    await waitFor(() => {
      const audio = container.querySelector('audio')
      expect(audio).toBeInTheDocument()
      expect(audio?.getAttribute('src')).toBe('https://example.com/public-audio.mp3')
    })
  })

  it('forwards auth token in public mode for followers-only stories', async () => {
    let receivedAuth: string | null = null
    server.use(
      http.get(`${BASE}/public/stories/:storyId/chapters/:num/audio`, ({ request }) => {
        receivedAuth = request.headers.get('Authorization')
        return HttpResponse.json({ url: 'https://example.com/followers-audio.mp3' })
      })
    )

    const { container } = render(
      <AudioPlayer storyId="test-story" chapterNumber={1} isPublic />
    )

    await waitFor(() => {
      expect(container.querySelector('audio')).toBeInTheDocument()
    })
    expect(receivedAuth).toBe('Bearer valid-token')
  })

  it('renders nothing while loading', () => {
    server.use(
      http.get(`${BASE}/stories/:storyId/chapters/:num/audio`, () => {
        return new Promise(() => {}) // never resolves
      })
    )

    const { container } = render(
      <AudioPlayer storyId="test-story" chapterNumber={1} />
    )

    expect(container.querySelector('audio')).not.toBeInTheDocument()
  })

  it('renders nothing on fetch error', async () => {
    server.use(
      http.get(`${BASE}/stories/:storyId/chapters/:num/audio`, () => {
        return HttpResponse.json({ detail: 'Not found' }, { status: 404 })
      })
    )

    const { container } = render(
      <AudioPlayer storyId="test-story" chapterNumber={1} />
    )

    // Wait for fetch to complete, then verify still nothing rendered
    await new Promise((r) => setTimeout(r, 50))
    expect(container.querySelector('audio')).not.toBeInTheDocument()
  })
})
