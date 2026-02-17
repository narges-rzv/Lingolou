import { describe, it, expect, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '../test-utils'
import { server } from '../mocks/server'
import { http, HttpResponse } from 'msw'
import PublicStories from '../../pages/PublicStories'

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
    expect(select.value).toBe('Chinese (Mandarin)')
  })
})
