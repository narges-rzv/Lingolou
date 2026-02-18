import { describe, it, expect, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { render } from '../test-utils'
import { server } from '../mocks/server'
import { http, HttpResponse } from 'msw'
import BudgetBanner from '../../components/BudgetBanner'

describe('BudgetBanner', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('fetches budget and renders spending info', async () => {
    render(<BudgetBanner />)

    await waitFor(() => {
      expect(screen.getByText(/Community pool/)).toBeInTheDocument()
    })

    expect(screen.getByText(/\$5\.00/)).toBeInTheDocument()
    expect(screen.getByText(/\$50\.00/)).toBeInTheDocument()
  })

  it('shows progress bar at correct width', async () => {
    render(<BudgetBanner />)

    await waitFor(() => {
      expect(screen.getByText(/Community pool/)).toBeInTheDocument()
    })

    const fill = document.querySelector('.budget-progress-fill')
    expect(fill).toBeInTheDocument()
    // 5/50 = 10%
    expect((fill as HTMLElement).style.width).toBe('10%')
  })

  it('shows exhausted message when budget used up', async () => {
    server.use(
      http.get('http://localhost:5173/api/public/budget', () => {
        return HttpResponse.json({
          total_budget: 50.0,
          total_spent: 50.0,
          free_stories_generated: 100,
          free_stories_per_user: 3,
        })
      })
    )

    render(<BudgetBanner />)

    await waitFor(() => {
      expect(screen.getByText(/used up/)).toBeInTheDocument()
    })
  })

  it('returns null if fetch fails', async () => {
    server.use(
      http.get('http://localhost:5173/api/public/budget', () => {
        return HttpResponse.error()
      })
    )

    const { container } = render(<BudgetBanner />)

    // Wait a tick for the effect to run
    await new Promise((r) => setTimeout(r, 100))
    expect(container.querySelector('.budget-banner')).not.toBeInTheDocument()
  })
})
