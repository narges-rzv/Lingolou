interface AudioPlayerProps {
  src: string;
  chapterNumber: number;
  duration?: number | null;
  showDownload?: boolean;
}

function formatDuration(seconds: number | null | undefined): string {
  if (!seconds) return '';
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export default function AudioPlayer({ src, chapterNumber, duration, showDownload = true }: AudioPlayerProps) {
  const cacheBust = duration ? `?v=${Math.round(duration * 100)}` : `?v=${Date.now()}`;
  const audioSrc = `${src}${cacheBust}`;

  return (
    <div className="audio-player">
      <audio controls preload="metadata" src={audioSrc} />
      <div className="audio-player-footer">
        {(duration ?? 0) > 0 && (
          <span className="audio-duration">{formatDuration(duration)}</span>
        )}
        {showDownload && (
          <a href={audioSrc} download={`chapter-${chapterNumber}.mp3`} className="btn btn-ghost btn-sm">
            Download
          </a>
        )}
      </div>
    </div>
  );
}
