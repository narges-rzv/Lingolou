import { useState, useEffect } from 'react';
import { apiFetch } from '../api';
import ScriptViewer from './ScriptViewer';
import AudioPlayer from './AudioPlayer';
import TaskProgress from './TaskProgress';

function statusClass(status) {
  return `status-badge status-${
    status === 'pending' ? 'created' :
    status === 'completed' ? 'completed' :
    status === 'failed' ? 'failed' : 'generating'
  }`;
}

export default function ChapterList({ chapters, storyId, autoExpand, onRefresh }) {
  const [expanded, setExpanded] = useState(null);
  const [chapterTasks, setChapterTasks] = useState({});

  useEffect(() => {
    if (autoExpand && chapters?.length > 0) {
      const sorted = [...chapters].sort((a, b) => a.chapter_number - b.chapter_number);
      setExpanded(sorted[0].chapter_number);
    }
  }, [autoExpand]);

  const generateChapterAudio = async (chapterNumber) => {
    try {
      const data = await apiFetch(`/stories/${storyId}/generate-audio`, {
        method: 'POST',
        json: { story_id: storyId, chapter_numbers: [chapterNumber] },
      });
      setChapterTasks((prev) => ({ ...prev, [chapterNumber]: data.task_id }));
    } catch (err) {
      setChapterTasks((prev) => ({ ...prev, [chapterNumber]: null }));
      alert(err.message);
    }
  };

  const handleChapterTaskComplete = (chapterNumber) => {
    setChapterTasks((prev) => ({ ...prev, [chapterNumber]: null }));
    onRefresh?.();
  };

  const handleChapterTaskError = (chapterNumber, msg) => {
    setChapterTasks((prev) => ({ ...prev, [chapterNumber]: null }));
    alert(msg);
    onRefresh?.();
  };

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
        const taskId = chapterTasks[ch.chapter_number];
        const isGenerating = !!taskId;

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
                {taskId && (
                  <TaskProgress
                    taskId={taskId}
                    onComplete={() => handleChapterTaskComplete(ch.chapter_number)}
                    onError={(msg) => handleChapterTaskError(ch.chapter_number, msg)}
                  />
                )}
                {hasAudio && (
                  <AudioPlayer
                    storyId={storyId}
                    chapterNumber={ch.chapter_number}
                    duration={ch.audio_duration}
                  />
                )}
                {hasScript && !hasAudio && !isGenerating && (
                  <button
                    className="btn btn-primary btn-sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      generateChapterAudio(ch.chapter_number);
                    }}
                    style={{ marginBottom: '0.75rem' }}
                  >
                    Generate Audio for This Chapter
                  </button>
                )}
                {hasScript && (
                  <ScriptViewer storyId={storyId} chapterNumber={ch.chapter_number} />
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
