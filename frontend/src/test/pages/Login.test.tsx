import { describe, it, expect, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '../test-utils'
import Login from '../../pages/Login'

describe('Login', () => {
  beforeEach(() => {
    localStorage.clear()
    window.history.replaceState({}, '', '/login')
  })

  it('renders login form by default', async () => {
    render(<Login />)

    await waitFor(() => {
      expect(screen.getByLabelText('Username')).toBeInTheDocument()
    })

    expect(screen.getByLabelText('Password')).toBeInTheDocument()
    expect(screen.getByText('Log in', { selector: 'button[type="submit"]' })).toBeInTheDocument()
  })

  it('switches to register tab', async () => {
    const user = userEvent.setup()
    render(<Login />)

    await waitFor(() => {
      expect(screen.getByText('Register')).toBeInTheDocument()
    })

    await user.click(screen.getByText('Register'))

    expect(screen.getByLabelText('Email')).toBeInTheDocument()
    expect(screen.getByLabelText('Username')).toBeInTheDocument()
    expect(screen.getByLabelText('Password')).toBeInTheDocument()
    expect(screen.getByText('Create account')).toBeInTheDocument()
  })

  it('shows Google OAuth button', async () => {
    render(<Login />)

    await waitFor(() => {
      expect(screen.getByText('Sign in with Google')).toBeInTheDocument()
    })
  })

  it('shows oauth error from URL', async () => {
    window.history.replaceState({}, '', '/login?error=oauth_failed')
    render(<Login />)

    await waitFor(() => {
      expect(screen.getByText(/Social sign-in failed/)).toBeInTheDocument()
    })
  })
})
