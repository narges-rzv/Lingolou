import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '../test-utils'
import { server } from '../mocks/server'
import { http, HttpResponse } from 'msw'
import TaskProgress from '../../components/TaskProgress'

describe('TaskProgress', () => {
  beforeEach(() => {
    localStorage.setItem('token', 'valid-token')
    vi.useFakeTimers({ shouldAdvanceTime: true })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('polls task status and shows progress', async () => {
    render(<TaskProgress taskId="test-task-1" />)

    await waitFor(() => {
      expect(screen.getByText('Generating chapter 1...')).toBeInTheDocument()
    })

    expect(screen.getByText('50%')).toBeInTheDocument()
  })

  it('calls onComplete when status is completed', async () => {
    const onComplete = vi.fn()

    server.use(
      http.get('http://localhost:5173/api/stories/tasks/:taskId', () => {
        return HttpResponse.json({
          task_id: 'test-task',
          status: 'completed',
          progress: 100,
          message: 'Done!',
          result: { story_id: 1 },
        })
      })
    )

    render(<TaskProgress taskId="test-task" onComplete={onComplete} />)

    await waitFor(() => {
      expect(onComplete).toHaveBeenCalledWith({ story_id: 1 })
    })
  })

  it('calls onError when status is failed', async () => {
    const onError = vi.fn()

    server.use(
      http.get('http://localhost:5173/api/stories/tasks/:taskId', () => {
        return HttpResponse.json({
          task_id: 'test-task',
          status: 'failed',
          progress: 0,
          message: 'OpenAI error',
        })
      })
    )

    render(<TaskProgress taskId="test-task" onError={onError} />)

    await waitFor(() => {
      expect(onError).toHaveBeenCalledWith('OpenAI error')
    })
  })

  it('shows cancel button when running', async () => {
    render(<TaskProgress taskId="test-task-1" />)

    await waitFor(() => {
      expect(screen.getByText('Cancel')).toBeInTheDocument()
    })
  })

  it('returns null when no status yet', () => {
    const { container } = render(<TaskProgress taskId={null} />)
    expect(container.querySelector('.task-progress')).not.toBeInTheDocument()
  })
})
