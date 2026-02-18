import { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { publicApiFetch, apiFetch } from '../api';
import AudioPlayer from '../components/AudioPlayer';
import PublicChapterList from '../components/PublicChapterList';
import type { PublicStoryResponse } from '../types';

interface PublicStoryDetailProps {
  preloadedStory?: PublicStoryResponse | null;
}

function statusClass(status: string | undefined): string {
  return `status-badge status-${status || 'created'}`;
}

export default function PublicStoryDetail({ preloadedStory }: PublicStoryDetailProps) {
  const { id } = useParams();
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const [story, setStory] = useState<PublicStoryResponse | null>(preloadedStory || null);
  const [loading, setLoading] = useState(!preloadedStory);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);
  const [voting, setVoting] = useState(false);
  const [forking, setForking] = useState(false);
  const [showReport, setShowReport] = useState(false);
  const [reportReason, setReportReason] = useState('');
  const [reporting, setReporting] = useState(false);
  const [reportDone, setReportDone] = useState(false);
  const [bookmarked, setBookmarked] = useState(false);
  const [bookmarking, setBookmarking] = useState(false);

  useEffect(() => {
    if (preloadedStory) {
      setStory(preloadedStory);
      setBookmarked(!!preloadedStory.is_bookmarked);
      setLoading(false);
      return;
    }
    if (!id) return;
    const token = localStorage.getItem('token');
    const headers: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};
    publicApiFetch(`/public/stories/${id}`, { headers })
      .then((data: PublicStoryResponse) => {
        setStory(data);
        setBookmarked(!!data.is_bookmarked);
      })
      .catch((err: unknown) => setError((err as Error).message))
      .finally(() => setLoading(false));
  }, [id, preloadedStory]);

  const handleVote = async (voteType: string) => {
    if (!isAuthenticated || !story) return;
    setVoting(true);
    try {
      const newType = story.user_vote === voteType ? null : voteType;
      const data = await apiFetch(`/votes/stories/${story.id}`, {
        method: 'POST',
        json: { vote_type: newType },
      }) as { upvotes: number; downvotes: number; user_vote: string | null };
      setStory((s) => {
        if (!s) return s;
        return {
          ...s,
          upvotes: data.upvotes,
          downvotes: data.downvotes,
          user_vote: data.user_vote,
        };
      });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setVoting(false);
    }
  };

  const handleReport = async () => {
    if (!story) return;
    setReporting(true);
    setError(null);
    try {
      await apiFetch(`/reports/stories/${story.id}`, {
        method: 'POST',
        json: { reason: reportReason },
      });
      setReportDone(true);
      setShowReport(false);
      setReportReason('');
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setReporting(false);
    }
  };

  const handleDownloadFull = async () => {
    if (!story) return;
    setDownloading(true);
    setError(null);
    try {
      const resp = await fetch(`/api/public/stories/${story.id}/audio/combined`);
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

  const handleFork = async () => {
    if (!story) return;
    setForking(true);
    setError(null);
    try {
      const data = await apiFetch(`/public/stories/${story.id}/fork`, { method: 'POST' }) as { id: number };
      navigate(`/stories/${data.id}`);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setForking(false);
    }
  };

  const handleBookmark = async () => {
    if (!isAuthenticated || !story) return;
    setBookmarking(true);
    try {
      const data = await apiFetch(`/bookmarks/stories/${story.id}`, { method: 'POST' }) as { bookmarked: boolean };
      setBookmarked(data.bookmarked);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBookmarking(false);
    }
  };

  if (loading) return <div className="loading">Loading story...</div>;
  if (!story) return <div className="error-message">{error || 'Story not found'}</div>;

  const chapters = story.chapters || [];
  const sorted = [...chapters].sort((a, b) => a.chapter_number - b.chapter_number);
  const audioChapters = sorted.filter((ch) => ch.audio_path);
  const hasAudio = audioChapters.length > 0;
  const netScore = (story.upvotes || 0) - (story.downvotes || 0);

  return (
    <div>
      <div className="story-detail-header">
        <div>
          <h1>{story.title}</h1>
          <div className="story-meta">
            <span className={statusClass(story.status)}>{story.status}</span>
            <span style={{ color: 'var(--color-text-secondary)', fontSize: '0.85rem' }}>
              {chapters.length} chapter{chapters.length !== 1 ? 's' : ''}
              {' \u00b7 '}
              by {story.owner_name}
            </span>
          </div>
          {story.description && (
            <p className="description" style={{ color: 'var(--color-text-secondary)', fontSize: '0.9rem' }}>
              {story.description}
            </p>
          )}
        </div>
      </div>

      {/* Vote controls */}
      <div className="vote-controls">
        <button
          className={`btn-vote${story.user_vote === 'up' ? ' voted' : ''}`}
          onClick={() => handleVote('up')}
          disabled={voting || !isAuthenticated}
          title={isAuthenticated ? 'Upvote' : 'Log in to vote'}
        >
          &#9650;
        </button>
        <span className="vote-score">{netScore}</span>
        <button
          className={`btn-vote${story.user_vote === 'down' ? ' voted' : ''}`}
          onClick={() => handleVote('down')}
          disabled={voting || !isAuthenticated}
          title={isAuthenticated ? 'Downvote' : 'Log in to vote'}
        >
          &#9660;
        </button>
        {!isAuthenticated && (
          <span style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)', marginLeft: '0.5rem' }}>
            <Link to="/login">Log in</Link> to vote
          </span>
        )}
        {isAuthenticated && (
          <button
            className={`btn btn-sm${bookmarked ? ' btn-primary' : ' btn-ghost'}`}
            style={{ marginLeft: 'auto' }}
            onClick={handleBookmark}
            disabled={bookmarking}
            title={bookmarked ? 'Remove bookmark' : 'Bookmark this story'}
          >
            {bookmarked ? '\u2605 Bookmarked' : '\u2606 Bookmark'}
          </button>
        )}
        {isAuthenticated && (
          <button
            className="btn btn-primary btn-sm"
            style={{ marginLeft: '0.5rem' }}
            onClick={handleFork}
            disabled={forking}
          >
            {forking ? 'Forking...' : 'Fork Story'}
          </button>
        )}
        {isAuthenticated && !reportDone && (
          <button
            className="btn btn-ghost btn-sm"
            style={{ marginLeft: '0.5rem' }}
            onClick={() => setShowReport(true)}
          >
            Report
          </button>
        )}
        {reportDone && (
          <span style={{ marginLeft: 'auto', fontSize: '0.8rem', color: 'var(--color-success)' }}>
            Report submitted
          </span>
        )}
      </div>

      {error && <div className="error-message">{error}</div>}

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
                storyId={story.id}
                chapterNumber={ch.chapter_number}
                duration={ch.audio_duration}
                showDownload={false}
              />
            </div>
          ))}
        </div>
      )}

      <h2 className="section-title">Chapters</h2>
      <PublicChapterList chapters={chapters} storyId={story.id} />

      <div style={{ marginTop: '2rem', textAlign: 'center' }}>
        <Link to="/" className="btn btn-ghost">Back to Public Stories</Link>
        {!isAuthenticated && (
          <Link to="/login" className="btn btn-primary" style={{ marginLeft: '0.5rem' }}>
            Log in
          </Link>
        )}
      </div>

      {/* Report modal */}
      {showReport && (
        <div className="confirm-overlay" onClick={() => setShowReport(false)}>
          <div className="confirm-dialog" onClick={(e) => e.stopPropagation()}>
            <h3 style={{ marginBottom: '0.75rem' }}>Report Story</h3>
            <div className="form-group">
              <textarea
                placeholder="Describe why this story is inappropriate (min 10 characters)..."
                value={reportReason}
                onChange={(e) => setReportReason(e.target.value)}
                rows={4}
                style={{ width: '100%' }}
              />
            </div>
            <div className="confirm-actions">
              <button className="btn btn-ghost" onClick={() => setShowReport(false)}>
                Cancel
              </button>
              <button
                className="btn btn-danger"
                onClick={handleReport}
                disabled={reporting || reportReason.trim().length < 10}
              >
                {reporting ? 'Submitting...' : 'Submit Report'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
