import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '../test-utils'
import ShareButton from '../../components/ShareButton'

vi.mock('qrcode', () => ({
  default: { toDataURL: vi.fn().mockResolvedValue('data:image/png;base64,QQ==') },
}))

const URL = 'https://lingolou.app/share/abc123'

describe('ShareButton', () => {
  beforeEach(() => {
    Object.assign(navigator, {
      clipboard: { writeText: vi.fn().mockResolvedValue(undefined) },
    })
  })

  afterEach(() => {
    vi.clearAllMocks()
    // Remove native share between tests so default is the fallback path.
    delete (navigator as { share?: unknown }).share
  })

  it('opens the panel and shows the share URL and channels', () => {
    render(<ShareButton url={URL} title="My Story" />)
    fireEvent.click(screen.getByRole('button', { name: /share/i }))

    expect(screen.getByLabelText('Share link')).toHaveValue(URL)
    expect(screen.getByRole('menuitem', { name: 'WhatsApp' })).toHaveAttribute(
      'href',
      expect.stringContaining('wa.me'),
    )
    expect(screen.getByRole('menuitem', { name: 'X' })).toHaveAttribute(
      'href',
      expect.stringContaining(encodeURIComponent(URL)),
    )
    expect(screen.getByRole('menuitem', { name: 'Reddit' })).toBeInTheDocument()
    expect(screen.getByRole('menuitem', { name: 'Email' })).toHaveAttribute(
      'href',
      expect.stringContaining('mailto:'),
    )
  })

  it('copies the link to the clipboard', async () => {
    render(<ShareButton url={URL} title="My Story" />)
    fireEvent.click(screen.getByRole('button', { name: /share/i }))
    fireEvent.click(screen.getByRole('button', { name: 'Copy' }))

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(URL)
    await waitFor(() => expect(screen.getByRole('button', { name: 'Copied!' })).toBeInTheDocument())
  })

  it('renders a QR code image when opened', async () => {
    render(<ShareButton url={URL} title="My Story" />)
    fireEvent.click(screen.getByRole('button', { name: /share/i }))
    await waitFor(() =>
      expect(screen.getByAltText('QR code for this story link')).toHaveAttribute(
        'src',
        'data:image/png;base64,QQ==',
      ),
    )
  })

  it('uses the native share sheet when available', async () => {
    const share = vi.fn().mockResolvedValue(undefined)
    Object.assign(navigator, { share })
    render(<ShareButton url={URL} title="My Story" description="A tale" />)
    fireEvent.click(screen.getByRole('button', { name: /^↗ Share$/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Share…' }))

    await waitFor(() =>
      expect(share).toHaveBeenCalledWith({ title: 'My Story', text: 'A tale', url: URL }),
    )
  })

  it('does not show the native share option when unsupported', async () => {
    render(<ShareButton url={URL} title="My Story" />)
    fireEvent.click(screen.getByRole('button', { name: /share/i }))
    expect(screen.queryByRole('button', { name: 'Share…' })).not.toBeInTheDocument()
    // Let the async QR state update settle to avoid an act() warning.
    await waitFor(() => expect(screen.getByAltText('QR code for this story link')).toBeInTheDocument())
  })
})
