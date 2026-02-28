import { describe, it, expect, beforeEach, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '../test-utils'
import UserProfile from '../../pages/UserProfile'

// Mock useParams
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useParams: () => ({ id: '2' }),
  }
})

describe('UserProfile', () => {
  beforeEach(() => {
    localStorage.setItem('token', 'valid-token')
  })

  it('renders user profile with stats', async () => {
    render(<UserProfile />)

    await waitFor(() => {
      expect(screen.getByText('otheruser')).toBeInTheDocument()
    })

    expect(screen.getByText(/5 stories/)).toBeInTheDocument()
    expect(screen.getByText(/10 followers/)).toBeInTheDocument()
  })

  it('shows follow button for other users', async () => {
    render(<UserProfile />)

    await waitFor(() => {
      expect(screen.getByText('Follow')).toBeInTheDocument()
    })
  })

  it('toggles follow on click', async () => {
    const user = userEvent.setup()
    render(<UserProfile />)

    await waitFor(() => {
      expect(screen.getByText('Follow')).toBeInTheDocument()
    })

    await user.click(screen.getByText('Follow'))

    await waitFor(() => {
      expect(screen.getByText('Following')).toBeInTheDocument()
    })
  })

  it('shows block button', async () => {
    render(<UserProfile />)

    await waitFor(() => {
      expect(screen.getByText('Block')).toBeInTheDocument()
    })
  })

  it('renders stories tab by default with story cards', async () => {
    render(<UserProfile />)

    await waitFor(() => {
      expect(screen.getByText('Profile Story')).toBeInTheDocument()
    })

    expect(screen.getByRole('button', { name: 'Stories' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Worlds' })).toBeInTheDocument()
  })

  it('switches to worlds tab and shows worlds', async () => {
    const user = userEvent.setup()
    render(<UserProfile />)

    await waitFor(() => {
      expect(screen.getByText('otheruser')).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: 'Worlds' }))

    await waitFor(() => {
      expect(screen.getByText('Profile World')).toBeInTheDocument()
    })
  })
})
