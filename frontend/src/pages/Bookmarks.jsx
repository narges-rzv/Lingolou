import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { apiFetch } from '../api';

export default function Bookmarks() {
  const [stories, setStories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    apiFetch('/bookmarks/stories')
      .then(setStories)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading">Loading bookmarks...</div>;
  if (error) return <div className="error-message">{error}</div>;

  return (
    <div>
      <h1>Bookmarked Stories</h1>
      {stories.length === 0 ? (
        <div className="empty-state">
          <p>No bookmarked stories yet.</p>
          <Link to="/" className="btn btn-primary">Browse Public Stories</Link>
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
              <div className="story-meta">
                <span className={`status-badge status-${story.status}`}>{story.status}</span>
                {story.language && <span>{story.language}</span>}
                <span>by {story.owner_name}</span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
