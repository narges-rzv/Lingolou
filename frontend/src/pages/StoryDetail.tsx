import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, useLocation, Link } from 'react-router-dom';
import { apiFetch } from '../api';
import ChapterList from '../components/ChapterList';
import AudioPlayer from '../components/AudioPlayer';
import TaskProgress from '../components/TaskProgress';
import VoiceAssignmentModal from '../components/VoiceAssignmentModal';
import type { StoryResponse, ShareLinkResponse } from '../types';

function statusClass(status: string | undefined): string {
  return `status-badge status-${status || 'created'}`;
}

export default function StoryDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const [story, setStory] = useState<StoryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [taskType, setTaskType] = useState<string | null>(null);
  const [showDelete, setShowDelete] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [showVoiceModal, setShowVoiceModal] = useState(false);
  const [autoExpand, setAutoExpand] = useState(0);

  const fetchStory = useCallback(async () => {
    try {
      const data = await apiFetch(`/stories/${id}`) as StoryResponse;
      setStory(data);

      // Auto-reconnect: if there's an active task and we're not already tracking one
      if (data.active_task && !taskId) {
        setTaskId(data.active_task.task_id);
        setTaskType(data.active_task.task_id.startsWith('audio_') ? 'audio' : 'script');
        setGenerating(true);
      }
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, [id, taskId]);

  useEffect(() => {
    fetchStory();
  }, [fetchStory]);

  // Poll story data while generating so chapter badges update live
  useEffect(() => {
    if (!generating) return;
    const interval = setInterval(() => {
      apiFetch(`/stories/${id}`).then(setStory).catch(() => {});
    }, 3000);
    return () => clearInterval(interval);
  }, [generating, id]);

  // Pick up task ID passed from EditStory via navigation state
  useEffect(() => {
    const state = location.state as { taskId?: string; taskType?: string } | null;
    if (state?.taskId) {
      setTaskId(state.taskId);
      setTaskType(state.taskType || 'script');
      setGenerating(true);
      // Clear the state so refreshing the page doesn't re-trigger
      window.history.replaceState({}, '');
    }
  }, [location.state]);

  const handleGenerate = () => {
    navigate(`/stories/${id}/edit`);
  };

  const handleGenerateAllAudio = () => {
    setShowVoiceModal(true);
  };

  const handleVoiceConfirm = async (voiceOverride: Record<string, Record<string, unknown>>) => {
    setShowVoiceModal(false);
    setError(null);
    setGenerating(true);
    try {
      const data = await apiFetch(`/stories/${id}/generate-audio`, {
        method: 'POST',
        json: {
          story_id: Number(id),
          voice_override: Object.keys(voiceOverride).length > 0 ? voiceOverride : null,
        },
      }) as { task_id: string };
      setTaskId(data.task_id);
      setTaskType('audio');
    } catch (err) {
      setError((err as Error).message);
      setGenerating(false);
    }
  };

  const handleTaskComplete = () => {
    setTaskId(null);
    setTaskType(null);
    setGenerating(false);
    setAutoExpand((c) => c + 1);
    fetchStory();
  };

  const handleTaskError = (msg: string) => {
    setTaskId(null);
    setTaskType(null);
    setGenerating(false);
    setError(msg);
    fetchStory();
  };

  const [downloading, setDownloading] = useState(false);
  const [updatingVisibility, setUpdatingVisibility] = useState(false);
  const [copySuccess, setCopySuccess] = useState(false);

  const handleVisibilityChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newVisibility = e.target.value;
    setUpdatingVisibility(true);
    setError(null);
    try {
      const data = await apiFetch(`/stories/${id}`, {
        method: 'PATCH',
        json: { visibility: newVisibility },
      }) as StoryResponse;
      setStory(data);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setUpdatingVisibility(false);
    }
  };

  const handleCopyShareLink = async () => {
    try {
      const data = await apiFetch(`/stories/${id}/generate-share-link`, {
        method: 'POST',
      }) as ShareLinkResponse;
      await navigator.clipboard.writeText(data.share_url);
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const handleDownloadFull = async () => {
    setDownloading(true);
    setError(null);
    try {
      const token = localStorage.getItem('token');
      const resp = await fetch(`/api/stories/${id}/audio/combined`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!resp.ok) {
        const text = await resp.text();
        let msg = `Download failed (${resp.status})`;
        try { msg = JSON.parse(text).detail || msg; } catch { /* ignore parse error */ }
        throw new Error(msg);
      }
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${story?.title || 'story'}.mp3`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setDownloading(false);
    }
  };

  const handleDelete = async () => {
    try {
      await apiFetch(`/stories/${id}`, { method: 'DELETE' });
      navigate('/dashboard');
    } catch (err) {
      setError((err as Error).message);
      setShowDelete(false);
    }
  };

  if (loading) return <div className="loading">Loading story...</div>;
  if (!story) return <div className="error-message">{error || 'Story not found'}</div>;

  const chapters = story.chapters || [];
  const sorted = [...chapters].sort((a, b) => a.chapter_number - b.chapter_number);
  const hasScripts = chapters.some(
    (ch) => ch.status === 'completed' || ch.status === 'generating_audio'
  );
  const audioChapters = sorted.filter((ch) => ch.audio_path);
  const hasAudio = audioChapters.length > 0;
  const allAudio = chapters.length > 0 && chapters.every((ch) => ch.audio_path);
  const someWithoutAudio = hasScripts && !allAudio;
  const canGenerate = story.status !== 'generating' && !generating;

  return (
    <div>
      <div className="story-detail-header">
        <div>
          <h1>{story.title}</h1>
          <div className="story-meta">
            <span className={statusClass(story.status)}>{story.status}</span>
            {story.visibility === 'public' && <span className="status-badge status-completed">Public</span>}
            {story.visibility === 'followers' && <span className="status-badge status-created">Followers</span>}
            {story.visibility === 'link_only' && <span className="status-badge status-created">Link-only</span>}
            {story.world_name && (
              <Link to={`/worlds/${story.world_id}`} style={{ fontSize: '0.85rem' }}>
                {story.world_name}
              </Link>
            )}
            <span style={{ color: 'var(--color-text-secondary)', fontSize: '0.85rem' }}>
              {chapters.length} chapter{chapters.length !== 1 ? 's' : ''}
            </span>
          </div>
          {story.description && (
            <p className="description" style={{ color: 'var(--color-text-secondary)', fontSize: '0.9rem' }}>
              {story.description}
            </p>
          )}
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}

      {taskId && (
        <TaskProgress
          taskId={taskId}
          onComplete={handleTaskComplete}
          onError={handleTaskError}
        />
      )}

      {/* Play Story section */}
      {hasAudio && (
        <div className="play-story-section">
          <div className="play-story-header">
            <h2 className="section-title" style={{ marginBottom: 0, borderBottom: 'none', paddingBottom: 0 }}>
              Play Story
            </h2>
            <button
              className="btn btn-primary btn-sm"
              onClick={handleDownloadFull}
              disabled={downloading}
            >
              {downloading ? 'Downloading...' : 'Download Full Story'}
            </button>
          </div>
          {audioChapters.map((ch) => (
            <div key={ch.id} className="play-story-item">
              <span className="play-story-label">
                Ch {ch.chapter_number}: {ch.title || `Chapter ${ch.chapter_number}`}
              </span>
              <AudioPlayer
                src={ch.audio_path as string}
                chapterNumber={ch.chapter_number}
                duration={ch.audio_duration}
              />
            </div>
          ))}
        </div>
      )}

      <div className="story-actions">
        <button
          className="btn btn-primary"
          onClick={handleGenerate}
          disabled={!canGenerate}
        >
          {story.status === 'created' ? 'Generate Story' : 'Regenerate Story'}
        </button>
        {someWithoutAudio && (
          <button
            className="btn btn-primary"
            onClick={handleGenerateAllAudio}
            disabled={generating}
          >
            Generate All Audio
          </button>
        )}
        <div className="visibility-controls">
          <select
            value={story.visibility}
            onChange={handleVisibilityChange}
            disabled={updatingVisibility}
            className="visibility-select"
          >
            <option value="private">Private</option>
            <option value="followers">Followers</option>
            <option value="link_only">Link-only</option>
            <option value="public">Public</option>
          </select>
          {story.visibility !== 'private' && story.visibility !== 'followers' && (
            <button className="btn btn-ghost btn-sm" onClick={handleCopyShareLink}>
              {copySuccess ? 'Copied!' : 'Copy Share Link'}
            </button>
          )}
        </div>
        <button
          className="btn btn-danger"
          onClick={() => setShowDelete(true)}
        >
          Delete Story
        </button>
      </div>

      <h2 className="section-title">Chapters</h2>
      <ChapterList
        chapters={chapters}
        storyId={story.id}
        autoExpand={autoExpand}
        onRefresh={fetchStory}
      />

      {showVoiceModal && (
        <VoiceAssignmentModal
          storyId={story.id}
          onConfirm={handleVoiceConfirm}
          onCancel={() => setShowVoiceModal(false)}
        />
      )}

      {showDelete && (
        <div className="confirm-overlay" onClick={() => setShowDelete(false)}>
          <div className="confirm-dialog" onClick={(e) => e.stopPropagation()}>
            <p>Delete "{story.title}"? This cannot be undone.</p>
            <div className="confirm-actions">
              <button className="btn btn-ghost" onClick={() => setShowDelete(false)}>
                Cancel
              </button>
              <button className="btn btn-danger" onClick={handleDelete}>
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
