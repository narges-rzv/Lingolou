import { describe, it, expect, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '../test-utils'
import { server } from '../mocks/server'
import { http, HttpResponse } from 'msw'
import Settings from '../../pages/Settings'

const BASE = 'http://localhost:5173/api'

describe('Settings', () => {
  beforeEach(() => {
    localStorage.clear()
    localStorage.setItem('token', 'valid-token')
  })

  it('loads and displays current key status', async () => {
    render(<Settings />)

    await waitFor(() => {
      expect(screen.getAllByText('Not set').length).toBeGreaterThanOrEqual(1)
    })
  })

  it('save button disabled when no input', async () => {
    render(<Settings />)

    await waitFor(() => {
      expect(screen.getByText('Save Keys')).toBeInTheDocument()
    })

    expect(screen.getByText('Save Keys')).toBeDisabled()
  })

  it('saving keys shows success message', async () => {
    const user = userEvent.setup()
    render(<Settings />)

    await waitFor(() => {
      expect(screen.getByText('Save Keys')).toBeInTheDocument()
    })

    const openaiInput = screen.getByPlaceholderText('sk-...')
    await user.type(openaiInput, 'sk-test123')
    await user.click(screen.getByText('Save Keys'))

    await waitFor(() => {
      expect(screen.getByText('Keys saved successfully.')).toBeInTheDocument()
    })
  })

  it('shows Configured when key is set', async () => {
    server.use(
      http.get(`${BASE}/auth/api-keys`, () => {
        return HttpResponse.json({
          has_openai_key: true,
          has_elevenlabs_key: false,
          free_stories_used: 1,
          free_stories_limit: 20,
          free_audio_used: 0,
          free_audio_limit: 5,
        })
      })
    )

    render(<Settings />)

    await waitFor(() => {
      expect(screen.getByText('Configured')).toBeInTheDocument()
    })
  })

  it('shows free tier usage info', async () => {
    render(<Settings />)

    await waitFor(() => {
      expect(screen.getByText(/Free story generations used/)).toBeInTheDocument()
    })

    expect(screen.getByText(/0 \/ 20/)).toBeInTheDocument()
  })
})
