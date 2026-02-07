import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { apiFetch } from '../api';
import StoryCard from '../components/StoryCard';

export default function Dashboard() {
  const [stories, setStories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    apiFetch('/stories/')
      .then(setStories)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading">Loading stories...</div>;

  return (
    <div>
      <div className="dashboard-header">
        <h1>My Stories</h1>
        <Link to="/stories/new" className="btn btn-primary">
          New Story
        </Link>
      </div>

      {error && <div className="error-message">{error}</div>}

      {stories.length === 0 ? (
        <div className="empty-state">
          <p>You haven't created any stories yet.</p>
          <Link to="/stories/new" className="btn btn-primary">
            Create your first story
          </Link>
        </div>
      ) : (
        <div className="story-grid">
          {stories.map((story) => (
            <StoryCard key={story.id} story={story} />
          ))}
        </div>
      )}
    </div>
  );
}
