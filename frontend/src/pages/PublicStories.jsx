import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';
import { publicApiFetch } from '../api';
import BudgetBanner from '../components/BudgetBanner';

function formatDate(dateStr) {
  return new Date(dateStr).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

export default function PublicStories() {
  const { isAuthenticated } = useAuth();
  const { language } = useLanguage();
  const [stories, setStories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showAll, setShowAll] = useState(false);

  useEffect(() => {
    setLoading(true);
    const url = showAll
      ? '/public/stories'
      : `/public/stories?language=${encodeURIComponent(language)}`;
    publicApiFetch(url)
      .then(setStories)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [language, showAll]);

  if (loading) return <div className="loading">Loading stories...</div>;

  return (
    <div>
      <BudgetBanner />
      <div className="dashboard-header">
        <div>
          <h1>
            {showAll ? 'Public Stories — All Languages' : `Public Stories — ${language}`}
          </h1>
          <button
            className="btn btn-ghost btn-sm"
            style={{ marginTop: '0.25rem' }}
            onClick={() => setShowAll(!showAll)}
          >
            {showAll ? `Show only ${language}` : 'Show all languages'}
          </button>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          {isAuthenticated ? (
            <Link to="/dashboard" className="btn btn-primary">My Stories</Link>
          ) : (
            <Link to="/login" className="btn btn-primary">Log in</Link>
          )}
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}

      {stories.length === 0 ? (
        <div className="empty-state">
          <p>No public stories yet{showAll ? '' : ` for ${language}`}.</p>
        </div>
      ) : (
        <div className="story-grid">
          {stories.map((story) => (
            <Link
              key={story.id}
              to={`/public/stories/${story.id}`}
              className="story-card"
            >
              <h3>{story.title}</h3>
              {story.description && (
                <p className="description">{story.description}</p>
              )}
              <div className="story-card-footer">
                <span className="status-badge status-completed">{story.status}</span>
                <span>
                  {story.chapter_count} chapter{story.chapter_count !== 1 ? 's' : ''}
                  {' \u00b7 '}
                  {formatDate(story.created_at)}
                </span>
              </div>
              <div style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)', marginTop: '0.25rem', display: 'flex', justifyContent: 'space-between' }}>
                <span>by {story.owner_name}</span>
                <span className="vote-score-inline">
                  &#9650; {(story.upvotes || 0) - (story.downvotes || 0)}
                </span>
              </div>
              {story.language && (
                <div style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)', marginTop: '0.15rem' }}>
                  {story.language}
                </div>
              )}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
