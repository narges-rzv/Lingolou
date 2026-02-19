import { describe, it, expect, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '../test-utils'
import Worlds from '../../pages/Worlds'

describe('Worlds', () => {
  beforeEach(() => {
    localStorage.clear()
    localStorage.setItem('token', 'valid-token')
  })

  it('renders world list page', async () => {
    render(<Worlds />)

    await waitFor(() => {
      expect(screen.getByText('Story Worlds')).toBeInTheDocument()
    })
  })

  it('displays built-in worlds section', async () => {
    render(<Worlds />)

    await waitFor(() => {
      expect(screen.getByText('Built-in Worlds')).toBeInTheDocument()
    })

    expect(screen.getByText('Winnie the Pooh')).toBeInTheDocument()
  })

  it('has create world button', async () => {
    render(<Worlds />)

    await waitFor(() => {
      expect(screen.getByText('Create World')).toBeInTheDocument()
    })
  })

  it('shows create form when clicking create button', async () => {
    const user = userEvent.setup()
    render(<Worlds />)

    await waitFor(() => {
      expect(screen.getByText('Create World')).toBeInTheDocument()
    })

    await user.click(screen.getByText('Create World'))

    await waitFor(() => {
      expect(screen.getByText('Create a New World')).toBeInTheDocument()
    })

    expect(screen.getByLabelText('World Name')).toBeInTheDocument()
    expect(screen.getByLabelText('Description')).toBeInTheDocument()
    expect(screen.getByLabelText('Visibility')).toBeInTheDocument()
  })

  it('displays world description in list', async () => {
    render(<Worlds />)

    await waitFor(() => {
      expect(screen.getByText(/Hundred Acre Wood/)).toBeInTheDocument()
    })
  })

  it('shows built-in badge on built-in worlds', async () => {
    render(<Worlds />)

    await waitFor(() => {
      expect(screen.getByText('Built-in')).toBeInTheDocument()
    })
  })

  it('shows story count in world card', async () => {
    render(<Worlds />)

    await waitFor(() => {
      expect(screen.getByText('5 stories')).toBeInTheDocument()
    })
  })
})
