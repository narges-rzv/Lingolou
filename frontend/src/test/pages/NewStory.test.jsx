import { describe, it, expect, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '../test-utils'
import NewStory from '../../pages/NewStory'

describe('NewStory', () => {
  beforeEach(() => {
    localStorage.clear()
    localStorage.setItem('token', 'valid-token')
  })

  it('renders form with all fields', async () => {
    render(<NewStory />)

    await waitFor(() => {
      expect(screen.getByLabelText('Title')).toBeInTheDocument()
    })

    expect(screen.getByLabelText(/Description/)).toBeInTheDocument()
    expect(screen.getByLabelText('Target Language')).toBeInTheDocument()
    expect(screen.getByLabelText('Chapters')).toBeInTheDocument()
    expect(screen.getByLabelText('Learning Theme')).toBeInTheDocument()
    expect(screen.getByLabelText('Story Plot')).toBeInTheDocument()
    expect(screen.getByText('Create Story')).toBeInTheDocument()
  })

  it('auto-generates prompt', async () => {
    render(<NewStory />)

    await waitFor(() => {
      const promptArea = screen.getByLabelText(/Generated Prompt/)
      expect(promptArea.value).toContain('story')
    })
  })

  it('shows world selector', async () => {
    render(<NewStory />)

    await waitFor(() => {
      expect(screen.getByLabelText('Story World')).toBeInTheDocument()
    })

    expect(screen.getByText('Custom (no world)')).toBeInTheDocument()
  })

  it('manual prompt edit sets promptEdited flag (shows Reset)', async () => {
    const user = userEvent.setup()
    render(<NewStory />)

    await waitFor(() => {
      expect(screen.getByLabelText(/Generated Prompt/)).toBeInTheDocument()
    })

    const promptArea = screen.getByLabelText(/Generated Prompt/)
    await user.type(promptArea, ' extra text')

    expect(screen.getByText('Reset')).toBeInTheDocument()
  })

  it('reset button restores auto-generated prompt', async () => {
    const user = userEvent.setup()
    render(<NewStory />)

    await waitFor(() => {
      expect(screen.getByLabelText(/Generated Prompt/)).toBeInTheDocument()
    })

    const promptArea = screen.getByLabelText(/Generated Prompt/)
    const original = promptArea.value
    await user.type(promptArea, ' manual edit')

    await user.click(screen.getByText('Reset'))
    expect(promptArea.value).toBe(original)
  })

  it('shows BudgetBanner', async () => {
    render(<NewStory />)

    await waitFor(() => {
      expect(screen.getByText(/Community pool/)).toBeInTheDocument()
    })
  })

  it('shows key status: free tier usage', async () => {
    render(<NewStory />)

    await waitFor(() => {
      expect(screen.getByText(/free tier/i)).toBeInTheDocument()
    })
  })
})
