import { describe, it, expect, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '../test-utils'
import { server } from '../mocks/server'
import { http, HttpResponse } from 'msw'
import Timeline from '../../pages/Timeline'

describe('Timeline', () => {
  beforeEach(() => {
    localStorage.setItem('token', 'valid-token')
  })

  it('renders timeline stories', async () => {
    render(<Timeline />)

    await waitFor(() => {
      expect(screen.getByText('Timeline Story')).toBeInTheDocument()
    })

    expect(screen.getByText('by')).toBeTruthy()
  })

  it('shows empty state when no follows', async () => {
    server.use(
      http.get('http://localhost:5173/api/follows/timeline', () => {
        return HttpResponse.json([])
      })
    )

    render(<Timeline />)

    await waitFor(() => {
      expect(screen.getByText(/No stories yet/)).toBeInTheDocument()
    })

    expect(screen.getByText('Browse Public Stories')).toBeInTheDocument()
  })

  it('switches to worlds tab', async () => {
    render(<Timeline />)
    const user = userEvent.setup()

    await waitFor(() => {
      expect(screen.getByText('Stories')).toBeInTheDocument()
    })

    await user.click(screen.getByText('Worlds'))

    await waitFor(() => {
      expect(screen.getByText('Timeline World')).toBeInTheDocument()
    })
  })
})
