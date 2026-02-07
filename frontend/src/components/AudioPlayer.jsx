function formatDuration(seconds) {
  if (!seconds) return '';
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export default function AudioPlayer({ storyId, chapterNumber, duration, showDownload = true }) {
  // Cache-bust with duration so regenerated audio is never served from browser cache
  const cacheBust = duration ? `?v=${Math.round(duration * 100)}` : `?v=${Date.now()}`;
  const src = `/static/audio/${storyId}/ch${chapterNumber}.mp3${cacheBust}`;

  return (
    <div className="audio-player">
      <audio controls preload="metadata" src={src} />
      <div className="audio-player-footer">
        {duration > 0 && (
          <span className="audio-duration">{formatDuration(duration)}</span>
        )}
        {showDownload && (
          <a href={src} download={`chapter-${chapterNumber}.mp3`} className="btn btn-ghost btn-sm">
            Download
          </a>
        )}
      </div>
    </div>
  );
}
