import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { apiFetch } from '../api';
import FollowButton from '../components/FollowButton';
import type { FollowUserItem } from '../types';

type Tab = 'followers' | 'following';

export default function Followers() {
  const { user } = useAuth();
  const [tab, setTab] = useState<Tab>('followers');
  const [items, setItems] = useState<FollowUserItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    apiFetch<FollowUserItem[]>(`/follows/${tab}`)
      .then(setItems)
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, [tab]);

  return (
    <div>
      <h1>Followers</h1>

      <div className="tab-bar" style={{ marginBottom: '1rem' }}>
        <button
          className={`btn btn-sm${tab === 'followers' ? ' btn-primary' : ' btn-ghost'}`}
          onClick={() => setTab('followers')}
        >
          Followers
        </button>
        <button
          className={`btn btn-sm${tab === 'following' ? ' btn-primary' : ' btn-ghost'}`}
          onClick={() => setTab('following')}
          style={{ marginLeft: '0.5rem' }}
        >
          Following
        </button>
      </div>

      {loading && <div className="loading">Loading...</div>}

      {!loading && items.length === 0 && (
        <div className="empty-state">
          <p>{tab === 'followers' ? 'No followers yet.' : 'You are not following anyone yet.'}</p>
          {tab === 'following' && (
            <Link to="/" className="btn btn-primary" style={{ marginTop: '0.5rem' }}>
              Browse Public Stories
            </Link>
          )}
        </div>
      )}

      {!loading && items.length > 0 && (
        <div className="story-grid">
          {items.map((item) => (
            <div key={item.id} className="story-card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <Link to={`/users/${item.id}`} style={{ fontWeight: 600, fontSize: '1.1rem' }}>
                  {item.username}
                </Link>
                <div className="story-meta" style={{ marginTop: '0.25rem' }}>
                  <span>{item.story_count} stories</span>
                </div>
              </div>
              {item.id !== user?.id && (
                <FollowButton userId={item.id} initialFollowing={item.is_following} />
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
