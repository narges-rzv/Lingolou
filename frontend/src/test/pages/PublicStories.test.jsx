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

  it('shows "Log in" when not authenticated', async () => {
    render(<PublicStories />)

    await waitFor(() => {
      expect(screen.getByText('Log in')).toBeInTheDocument()
    })
  })

  it('shows "My Stories" when authenticated', async () => {
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

  it('language filter toggle works', async () => {
    const user = userEvent.setup()
    render(<PublicStories />)

    await waitFor(() => {
      expect(screen.getByText(/Show all languages/)).toBeInTheDocument()
    })

    await user.click(screen.getByText('Show all languages'))

    await waitFor(() => {
      expect(screen.getByText(/All Languages/)).toBeInTheDocument()
    })
  })
})
