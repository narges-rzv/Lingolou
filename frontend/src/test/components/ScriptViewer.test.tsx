import { describe, it, expect, beforeEach } from 'vitest'
import { waitFor } from '@testing-library/react'
import { render } from '../test-utils'
import { server } from '../mocks/server'
import { http, HttpResponse } from 'msw'
import ScriptViewer from '../../components/ScriptViewer'

const BASE = 'http://localhost:5173/api'

const SCRIPT = [
  { type: 'scene', title: 'Opening' },
  { type: 'line', speaker: 'NARRATOR', lang: 'en', text: 'Hello there.' },
  { type: 'pause', seconds: 0.5 },
  { type: 'line', speaker: 'HERO', lang: 'fa', text: 'Salam!' },
]

describe('ScriptViewer', () => {
  beforeEach(() => {
    localStorage.setItem('token', 'valid-token')
    server.use(
      http.get(`${BASE}/stories/:storyId/chapters/:num/script`, () => {
        return HttpResponse.json(SCRIPT)
      })
    )
  })

  it('renders play and regenerate buttons when hasLineAudio is true', async () => {
    const { container } = render(
      <ScriptViewer storyId="test-story" chapterNumber={1} hasLineAudio={true} />
    )

    await waitFor(() => {
      const controls = container.querySelectorAll('.line-audio-controls')
      // Only line entries (index 1 and 3) get controls
      expect(controls.length).toBe(2)
    })

    // Each control has a play and a regenerate button
    const playBtns = container.querySelectorAll('.btn-line-audio:not(.btn-line-regen)')
    const regenBtns = container.querySelectorAll('.btn-line-regen')
    expect(playBtns.length).toBe(2)
    expect(regenBtns.length).toBe(2)
  })

  it('hides line audio buttons when hasLineAudio is false', async () => {
    const { container } = render(
      <ScriptViewer storyId="test-story" chapterNumber={1} hasLineAudio={false} />
    )

    await waitFor(() => {
      // Script should be rendered (check for speaker name)
      expect(container.textContent).toContain('NARRATOR')
    })

    const controls = container.querySelectorAll('.line-audio-controls')
    expect(controls.length).toBe(0)
  })

  it('hides line audio buttons when hasLineAudio is undefined (legacy)', async () => {
    const { container } = render(
      <ScriptViewer storyId="test-story" chapterNumber={1} />
    )

    await waitFor(() => {
      expect(container.textContent).toContain('NARRATOR')
    })

    const controls = container.querySelectorAll('.line-audio-controls')
    expect(controls.length).toBe(0)
  })
})
