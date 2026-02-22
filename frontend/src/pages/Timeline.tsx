import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { apiFetch } from '../api';
import type { TimelineStoryItem, TimelineWorldItem } from '../types';

type Tab = 'stories' | 'worlds';

export default function Timeline() {
  const [tab, setTab] = useState<Tab>('stories');
  const [stories, setStories] = useState<TimelineStoryItem[]>([]);
  const [worlds, setWorlds] = useState<TimelineWorldItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    if (tab === 'stories') {
      apiFetch<TimelineStoryItem[]>('/follows/timeline')
        .then(setStories)
        .catch(() => setStories([]))
        .finally(() => setLoading(false));
    } else {
      apiFetch<TimelineWorldItem[]>('/follows/timeline/worlds')
        .then(setWorlds)
        .catch(() => setWorlds([]))
        .finally(() => setLoading(false));
    }
  }, [tab]);

  return (
    <div>
      <h1>Timeline</h1>
      <p style={{ color: 'var(--color-text-secondary)', marginBottom: '1rem' }}>
        Stories and worlds from people you follow
      </p>

      <div className="tab-bar" style={{ marginBottom: '1rem' }}>
        <button
          className={`btn btn-sm${tab === 'stories' ? ' btn-primary' : ' btn-ghost'}`}
          onClick={() => setTab('stories')}
        >
          Stories
        </button>
        <button
          className={`btn btn-sm${tab === 'worlds' ? ' btn-primary' : ' btn-ghost'}`}
          onClick={() => setTab('worlds')}
          style={{ marginLeft: '0.5rem' }}
        >
          Worlds
        </button>
      </div>

      {loading && <div className="loading">Loading...</div>}

      {!loading && tab === 'stories' && stories.length === 0 && (
        <div className="empty-state">
          <p>No stories yet. Follow some users to see their stories here!</p>
          <Link to="/" className="btn btn-primary" style={{ marginTop: '0.5rem' }}>
            Browse Public Stories
          </Link>
        </div>
      )}

      {!loading && tab === 'stories' && stories.length > 0 && (
        <div className="story-grid">
          {stories.map((s) => (
            <Link to={`/public/stories/${s.id}`} key={s.id} className="story-card">
              <h3>{s.title}</h3>
              {s.description && <p className="description">{s.description}</p>}
              <div className="story-meta">
                <span>{s.chapter_count} ch</span>
                {s.language && <span>{s.language}</span>}
                <span>
                  by <Link to={`/users/${s.owner_id}`} onClick={(e) => e.stopPropagation()}>{s.owner_name}</Link>
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}

      {!loading && tab === 'worlds' && worlds.length === 0 && (
        <div className="empty-state">
          <p>No worlds yet from people you follow.</p>
        </div>
      )}

      {!loading && tab === 'worlds' && worlds.length > 0 && (
        <div className="story-grid">
          {worlds.map((w) => (
            <Link to={`/worlds/${w.id}`} key={w.id} className="story-card">
              <h3>{w.name}</h3>
              {w.description && <p className="description">{w.description}</p>}
              <div className="story-meta">
                <span>{w.story_count} stories</span>
                <span>
                  by <Link to={`/users/${w.owner_id}`} onClick={(e) => e.stopPropagation()}>{w.owner_name}</Link>
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
