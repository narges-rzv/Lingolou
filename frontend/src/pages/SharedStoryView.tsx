import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { publicApiFetch } from '../api';
import PublicStoryDetail from './PublicStoryDetail';
import type { PublicStoryResponse } from '../types';

export default function SharedStoryView() {
  const { shareCode } = useParams();
  const [story, setStory] = useState<PublicStoryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = localStorage.getItem('token');
    const headers: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};
    publicApiFetch(`/public/share/${shareCode}`, { headers })
      .then(setStory)
      .catch((err: unknown) => setError((err as Error).message))
      .finally(() => setLoading(false));
  }, [shareCode]);

  if (loading) return <div className="loading">Loading story...</div>;
  if (error) return <div className="error-message">{error}</div>;

  return <PublicStoryDetail preloadedStory={story} />;
}
