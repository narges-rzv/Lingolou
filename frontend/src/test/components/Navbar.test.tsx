import { describe, it, expect, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '../test-utils'
import Navbar from '../../components/Navbar'

describe('Navbar', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('shows "Log in" when not authenticated', async () => {
    render(<Navbar />)

    await waitFor(() => {
      expect(screen.getByText('Log in')).toBeInTheDocument()
    })

    expect(screen.queryByText('My Stories')).not.toBeInTheDocument()
    expect(screen.queryByText('Log out')).not.toBeInTheDocument()
  })

  it('shows user nav when authenticated', async () => {
    localStorage.setItem('token', 'valid-token')
    render(<Navbar />)

    await waitFor(() => {
      expect(screen.getByText('testuser')).toBeInTheDocument()
    })

    expect(screen.getByText('My Stories')).toBeInTheDocument()
    expect(screen.getByText('Settings')).toBeInTheDocument()
    expect(screen.getByText('Log out')).toBeInTheDocument()
  })

  it('renders language selector with options', async () => {
    render(<Navbar />)

    const select = screen.getByRole('combobox')
    expect(select).toBeInTheDocument()
    // Should have all LANGUAGES options
    expect((select as HTMLSelectElement).options.length).toBeGreaterThan(10)
  })

  it('logout button clears auth', async () => {
    localStorage.setItem('token', 'valid-token')
    const user = userEvent.setup()
    render(<Navbar />)

    await waitFor(() => {
      expect(screen.getByText('Log out')).toBeInTheDocument()
    })

    await user.click(screen.getByText('Log out'))

    await waitFor(() => {
      expect(screen.getByText('Log in')).toBeInTheDocument()
    })
    expect(localStorage.getItem('token')).toBeNull()
  })
})
