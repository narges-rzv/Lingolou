import { useState } from 'react';
import { ChapterResponse } from '../types';
import AudioPlayer from './AudioPlayer';
import PublicScriptViewer from './PublicScriptViewer';

function statusClass(status: string): string {
  return `status-badge status-${
    status === 'pending' ? 'created' :
    status === 'completed' ? 'completed' :
    status === 'failed' ? 'failed' : 'generating'
  }`;
}

interface PublicChapterListProps {
  chapters: ChapterResponse[];
  storyId: number;
}

export default function PublicChapterList({ chapters, storyId }: PublicChapterListProps) {
  const [expanded, setExpanded] = useState<number | null>(null);

  if (!chapters || chapters.length === 0) {
    return <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.9rem' }}>No chapters yet.</p>;
  }

  const sorted = [...chapters].sort((a, b) => a.chapter_number - b.chapter_number);

  return (
    <div className="chapter-list">
      {sorted.map((ch) => {
        const isOpen = expanded === ch.chapter_number;
        const hasScript = ch.status === 'completed' || ch.status === 'generating_audio';
        const hasAudio = !!ch.audio_path;

        return (
          <div key={ch.id} className="chapter-item">
            <div
              className="chapter-header"
              onClick={() => setExpanded(isOpen ? null : ch.chapter_number)}
            >
              <div className="chapter-header-left">
                <span className="chapter-number">{ch.chapter_number}</span>
                <span className="chapter-title">
                  {ch.title || `Chapter ${ch.chapter_number}`}
                </span>
                {hasAudio && <span className="audio-icon" title="Audio available">&#9835;</span>}
              </div>
              <div className="chapter-header-right">
                <span className={statusClass(ch.status)}>{ch.status}</span>
                <span className={`expand-icon ${isOpen ? 'expanded' : ''}`}>
                  &#9660;
                </span>
              </div>
            </div>

            {isOpen && (
              <div className="chapter-body">
                {hasAudio && (
                  <AudioPlayer
                    storyId={storyId}
                    chapterNumber={ch.chapter_number}
                    duration={ch.audio_duration}
                    showDownload={false}
                  />
                )}
                {hasScript && (
                  <PublicScriptViewer storyId={storyId} chapterNumber={ch.chapter_number} />
                )}
                {!hasScript && !hasAudio && (
                  <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.85rem', padding: '0.5rem 0' }}>
                    {ch.status === 'pending'
                      ? 'Script has not been generated yet.'
                      : ch.error_message || `Status: ${ch.status}`}
                  </p>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
