import { describe, it, expect, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { render } from '../test-utils'
import { server } from '../mocks/server'
import { http, HttpResponse } from 'msw'
import Bookmarks from '../../pages/Bookmarks'

describe('Bookmarks', () => {
  beforeEach(() => {
    localStorage.setItem('token', 'valid-token')
  })

  it('renders bookmarked stories', async () => {
    render(<Bookmarks />)

    await waitFor(() => {
      expect(screen.getByText('Bookmarked Story')).toBeInTheDocument()
    })

    expect(screen.getByText('by otheruser')).toBeInTheDocument()
  })

  it('shows empty state when no bookmarks', async () => {
    server.use(
      http.get('http://localhost:5173/api/bookmarks/stories', () => {
        return HttpResponse.json([])
      })
    )

    render(<Bookmarks />)

    await waitFor(() => {
      expect(screen.getByText('No bookmarked stories yet.')).toBeInTheDocument()
    })

    expect(screen.getByText('Browse Public Stories')).toBeInTheDocument()
  })
})
