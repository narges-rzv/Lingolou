import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { publicApiFetch } from '../api';
import PublicStoryDetail from './PublicStoryDetail';

export default function SharedStoryView() {
  const { shareCode } = useParams();
  const [story, setStory] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const token = localStorage.getItem('token');
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    publicApiFetch(`/public/share/${shareCode}`, { headers })
      .then(setStory)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [shareCode]);

  if (loading) return <div className="loading">Loading story...</div>;
  if (error) return <div className="error-message">{error}</div>;

  return <PublicStoryDetail preloadedStory={story} />;
}
