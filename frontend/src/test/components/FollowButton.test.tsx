import { describe, it, expect, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '../test-utils'
import FollowButton from '../../components/FollowButton'

describe('FollowButton', () => {
  beforeEach(() => {
    localStorage.setItem('token', 'valid-token')
  })

  it('renders Follow when not following', () => {
    render(<FollowButton userId={2} initialFollowing={false} />)
    expect(screen.getByText('Follow')).toBeInTheDocument()
  })

  it('renders Following when already following', () => {
    render(<FollowButton userId={2} initialFollowing={true} />)
    expect(screen.getByText('Following')).toBeInTheDocument()
  })

  it('toggles to Following on click', async () => {
    const user = userEvent.setup()
    render(<FollowButton userId={2} initialFollowing={false} />)

    await user.click(screen.getByText('Follow'))

    await waitFor(() => {
      expect(screen.getByText('Following')).toBeInTheDocument()
    })
  })
})
