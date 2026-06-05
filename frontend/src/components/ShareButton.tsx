import { useEffect, useRef, useState } from 'react';
import QRCode from 'qrcode';

interface ShareButtonProps {
  url: string;
  title: string;
  description?: string | null;
}

interface Channel {
  label: string;
  href: string;
}

function buildChannels(url: string, title: string, description?: string | null): Channel[] {
  const u = encodeURIComponent(url);
  const t = encodeURIComponent(title);
  const body = encodeURIComponent(`${description ? description + '\n\n' : ''}${url}`);
  return [
    { label: 'WhatsApp', href: `https://wa.me/?text=${encodeURIComponent(`${title} ${url}`)}` },
    { label: 'X', href: `https://twitter.com/intent/tweet?text=${t}&url=${u}` },
    { label: 'Reddit', href: `https://www.reddit.com/submit?url=${u}&title=${t}` },
    { label: 'Facebook', href: `https://www.facebook.com/sharer/sharer.php?u=${u}` },
    { label: 'Email', href: `mailto:?subject=${t}&body=${body}` },
  ];
}

export default function ShareButton({ url, title, description }: ShareButtonProps) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const [qr, setQr] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const canNativeShare = typeof navigator !== 'undefined' && typeof navigator.share === 'function';

  // Generate the QR code lazily when the panel opens.
  useEffect(() => {
    if (open && !qr) {
      QRCode.toDataURL(url, { width: 160, margin: 1 })
        .then(setQr)
        .catch(() => setQr(null));
    }
  }, [open, qr, url]);

  // Close the panel when clicking outside of it.
  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, [open]);

  const handleNativeShare = async () => {
    try {
      await navigator.share({ title, text: description ?? title, url });
      setOpen(false);
    } catch {
      /* user cancelled or share failed — keep the panel open */
    }
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  };

  const channels = buildChannels(url, title, description);

  return (
    <div ref={containerRef} style={{ position: 'relative', display: 'inline-block' }}>
      <button
        className="btn btn-primary btn-sm"
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="true"
        aria-expanded={open}
      >
        {'↗ Share'}
      </button>

      {open && (
        <div className="share-panel" role="menu" aria-label="Share options">
          {canNativeShare && (
            <button className="btn btn-primary btn-sm share-native" onClick={handleNativeShare}>
              Share…
            </button>
          )}

          <div className="share-copy-row">
            <input className="share-url-input" type="text" readOnly value={url} aria-label="Share link" />
            <button className="btn btn-sm btn-ghost" onClick={handleCopy}>
              {copied ? 'Copied!' : 'Copy'}
            </button>
          </div>

          <div className="share-channels">
            {channels.map((c) => (
              <a
                key={c.label}
                className="btn btn-sm btn-ghost"
                href={c.href}
                target="_blank"
                rel="noopener noreferrer"
                role="menuitem"
              >
                {c.label}
              </a>
            ))}
          </div>

          {qr && <img className="share-qr" src={qr} alt="QR code for this story link" width={160} height={160} />}
        </div>
      )}
    </div>
  );
}
