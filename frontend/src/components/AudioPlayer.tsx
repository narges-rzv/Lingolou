import { useState, useEffect, useRef } from 'react';
import { apiFetch, publicApiFetch } from '../api';

interface AudioPlayerProps {
  storyId: string;
  chapterNumber: number;
  duration?: number | null;
  showDownload?: boolean;
  isPublic?: boolean;
}

function formatDuration(seconds: number | null | undefined): string {
  if (!seconds) return '';
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export default function AudioPlayer({ storyId, chapterNumber, duration, showDownload = true, isPublic = false }: AudioPlayerProps) {
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const fetchedRef = useRef(false);

  useEffect(() => {
    if (fetchedRef.current) return;
    fetchedRef.current = true;

    const path = isPublic
      ? `/public/stories/${storyId}/chapters/${chapterNumber}/audio`
      : `/stories/${storyId}/chapters/${chapterNumber}/audio`;

    const fetcher = isPublic ? publicApiFetch : apiFetch;
    fetcher<{ url: string }>(path)
      .then((data) => setAudioUrl(data.url))
      .catch(() => setAudioUrl(null));
  }, [storyId, chapterNumber, isPublic]);

  if (!audioUrl) return null;

  return (
    <div className="audio-player">
      <audio controls preload="metadata" src={audioUrl} />
      <div className="audio-player-footer">
        {(duration ?? 0) > 0 && (
          <span className="audio-duration">{formatDuration(duration)}</span>
        )}
        {showDownload && (
          <a href={audioUrl} download={`chapter-${chapterNumber}.mp3`} className="btn btn-ghost btn-sm">
            Download
          </a>
        )}
      </div>
    </div>
  );
}
