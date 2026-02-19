import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '../test-utils'
import VoiceAssignmentModal from '../../components/VoiceAssignmentModal'

describe('VoiceAssignmentModal', () => {
  beforeEach(() => {
    localStorage.clear()
    localStorage.setItem('token', 'valid-token')
  })

  it('renders loading state initially', () => {
    render(
      <VoiceAssignmentModal storyId={1} onConfirm={() => {}} onCancel={() => {}} />
    )
    expect(screen.getByText('Loading voice config...')).toBeInTheDocument()
  })

  it('displays speakers and voice dropdowns after loading', async () => {
    render(
      <VoiceAssignmentModal storyId={1} onConfirm={() => {}} onCancel={() => {}} />
    )

    await waitFor(() => {
      expect(screen.getByText('NARRATOR')).toBeInTheDocument()
    })

    expect(screen.getByText('WINNIE')).toBeInTheDocument()
    expect(screen.getByText('Voice Assignments')).toBeInTheDocument()
    expect(screen.getByText('Confirm & Generate')).toBeInTheDocument()
    expect(screen.getByText('Cancel')).toBeInTheDocument()
  })

  it('shows available voices in dropdowns', async () => {
    render(
      <VoiceAssignmentModal storyId={1} onConfirm={() => {}} onCancel={() => {}} />
    )

    await waitFor(() => {
      expect(screen.getByText('NARRATOR')).toBeInTheDocument()
    })

    // Voice options should appear in select elements
    const options = screen.getAllByRole('option')
    const optionLabels = options.map((o) => o.textContent)
    expect(optionLabels).toContain('Alice')
    expect(optionLabels).toContain('Bob')
    expect(optionLabels).toContain('Charlie')
  })

  it('calls onCancel when Cancel is clicked', async () => {
    const onCancel = vi.fn()
    const user = userEvent.setup()

    render(
      <VoiceAssignmentModal storyId={1} onConfirm={() => {}} onCancel={onCancel} />
    )

    await waitFor(() => {
      expect(screen.getByText('Cancel')).toBeInTheDocument()
    })

    await user.click(screen.getByText('Cancel'))
    expect(onCancel).toHaveBeenCalledOnce()
  })

  it('calls onConfirm with voice override on confirm', async () => {
    const onConfirm = vi.fn()
    const user = userEvent.setup()

    render(
      <VoiceAssignmentModal storyId={1} onConfirm={onConfirm} onCancel={() => {}} />
    )

    await waitFor(() => {
      expect(screen.getByText('Confirm & Generate')).toBeInTheDocument()
    })

    await user.click(screen.getByText('Confirm & Generate'))
    expect(onConfirm).toHaveBeenCalledOnce()

    // Should include voice overrides for speakers that have assignments
    const override = onConfirm.mock.calls[0][0]
    expect(override.NARRATOR).toBeDefined()
    expect(override.NARRATOR.voice_id).toBe('abc123')
    expect(override.WINNIE.voice_id).toBe('def456')
  })
})
