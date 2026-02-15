import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { publicApiFetch, apiFetch } from '../api';
import AudioPlayer from '../components/AudioPlayer';
import PublicChapterList from '../components/PublicChapterList';

function statusClass(status) {
  return `status-badge status-${status || 'created'}`;
}

export default function PublicStoryDetail({ preloadedStory }) {
  const { id } = useParams();
  const { isAuthenticated } = useAuth();
  const [story, setStory] = useState(preloadedStory || null);
  const [loading, setLoading] = useState(!preloadedStory);
  const [error, setError] = useState(null);
  const [downloading, setDownloading] = useState(false);
  const [voting, setVoting] = useState(false);
  const [showReport, setShowReport] = useState(false);
  const [reportReason, setReportReason] = useState('');
  const [reporting, setReporting] = useState(false);
  const [reportDone, setReportDone] = useState(false);

  useEffect(() => {
    if (preloadedStory) {
      setStory(preloadedStory);
      setLoading(false);
      return;
    }
    if (!id) return;
    const token = localStorage.getItem('token');
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    publicApiFetch(`/public/stories/${id}`, { headers })
      .then(setStory)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [id, preloadedStory]);

  const handleVote = async (voteType) => {
    if (!isAuthenticated) return;
    setVoting(true);
    try {
      const newType = story.user_vote === voteType ? null : voteType;
      const data = await apiFetch(`/votes/stories/${story.id}`, {
        method: 'POST',
        json: { vote_type: newType },
      });
      setStory((s) => ({
        ...s,
        upvotes: data.upvotes,
        downvotes: data.downvotes,
        user_vote: data.user_vote,
      }));
    } catch (err) {
      setError(err.message);
    } finally {
      setVoting(false);
    }
  };

  const handleReport = async () => {
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
      setError(err.message);
    } finally {
      setReporting(false);
    }
  };

  const handleDownloadFull = async () => {
    setDownloading(true);
    setError(null);
    try {
      const resp = await fetch(`/api/public/stories/${story.id}/audio/combined`);
      if (!resp.ok) {
        const text = await resp.text();
        let msg = `Download failed (${resp.status})`;
        try { msg = JSON.parse(text).detail || msg; } catch {}
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
      setError(err.message);
    } finally {
      setDownloading(false);
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
        {isAuthenticated && !reportDone && (
          <button
            className="btn btn-ghost btn-sm"
            style={{ marginLeft: 'auto' }}
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
