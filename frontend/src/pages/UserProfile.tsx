import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { apiFetch } from '../api';
import FollowButton from '../components/FollowButton';
import type {
  UserProfileResponse,
  BlockResponse,
  PublicStoryListItem,
  WorldListItem,
} from '../types';

type Tab = 'stories' | 'worlds';

export default function UserProfile() {
  const { id } = useParams();
  const { user } = useAuth();
  const [profile, setProfile] = useState<UserProfileResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [blocking, setBlocking] = useState(false);

  const [tab, setTab] = useState<Tab>('stories');
  const [stories, setStories] = useState<PublicStoryListItem[]>([]);
  const [worlds, setWorlds] = useState<WorldListItem[]>([]);
  const [contentLoading, setContentLoading] = useState(true);

  // Load profile + stories together in one effect (StrictMode-safe)
  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    setProfile(null);
    setTab('stories');
    setStories([]);
    setWorlds([]);
    setContentLoading(true);

    Promise.all([
      apiFetch<UserProfileResponse>(`/follows/users/${id}/profile`),
      apiFetch<PublicStoryListItem[]>(`/follows/users/${id}/stories`),
    ])
      .then(([profileData, storiesData]) => {
        if (cancelled) return;
        setProfile(profileData);
        setStories(storiesData);
        setContentLoading(false);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError((err as Error).message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [id]);

  const switchTab = (newTab: Tab) => {
    if (newTab === tab || !id) return;
    setTab(newTab);
    setContentLoading(true);
    if (newTab === 'stories') {
      apiFetch<PublicStoryListItem[]>(`/follows/users/${id}/stories`)
        .then(setStories)
        .catch(() => setStories([]))
        .finally(() => setContentLoading(false));
    } else {
      apiFetch<WorldListItem[]>(`/follows/users/${id}/worlds`)
        .then(setWorlds)
        .catch(() => setWorlds([]))
        .finally(() => setContentLoading(false));
    }
  };

  const handleBlock = async () => {
    if (!profile) return;
    setBlocking(true);
    try {
      const data = await apiFetch<BlockResponse>(`/blocks/users/${profile.id}`, {
        method: 'POST',
      });
      setProfile((p) =>
        p ? { ...p, is_blocked: data.blocked, is_following: data.blocked ? false : p.is_following } : p,
      );
    } catch {
      // ignore
    } finally {
      setBlocking(false);
    }
  };

  if (loading) return <div className="loading">Loading profile...</div>;
  if (error || !profile) return <div className="error-message">{error || 'User not found'}</div>;

  const isOwnProfile = user?.id === profile.id;

  return (
    <div>
      {/* Profile header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '0.5rem' }}>
        <h1 style={{ margin: 0 }}>{profile.username}</h1>
        {!isOwnProfile && !profile.is_blocked && (
          <FollowButton
            userId={profile.id}
            initialFollowing={profile.is_following}
            onToggle={(following) =>
              setProfile((p) =>
                p
                  ? {
                      ...p,
                      is_following: following,
                      follower_count: p.follower_count + (following ? 1 : -1),
                    }
                  : p,
              )
            }
          />
        )}
        {!isOwnProfile && (
          <button
            className={`btn btn-sm${profile.is_blocked ? ' btn-ghost' : ' btn-danger'}`}
            onClick={handleBlock}
            disabled={blocking}
          >
            {profile.is_blocked ? 'Unblock' : 'Block'}
          </button>
        )}
      </div>

      <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.85rem', marginBottom: '1.5rem' }}>
        {profile.story_count} stories &middot; {profile.world_count} worlds
        &middot; {profile.follower_count} followers &middot; {profile.following_count} following
        &middot; Joined {new Date(profile.created_at).toLocaleDateString()}
      </p>

      {/* Tabs — same style as Timeline */}
      <div className="tab-bar" style={{ marginBottom: '1rem' }}>
        <button
          className={`btn btn-sm${tab === 'stories' ? ' btn-primary' : ' btn-ghost'}`}
          onClick={() => switchTab('stories')}
        >
          Stories
        </button>
        <button
          className={`btn btn-sm${tab === 'worlds' ? ' btn-primary' : ' btn-ghost'}`}
          onClick={() => switchTab('worlds')}
          style={{ marginLeft: '0.5rem' }}
        >
          Worlds
        </button>
      </div>

      {contentLoading && <div className="loading">Loading...</div>}

      {/* Stories tab */}
      {!contentLoading && tab === 'stories' && stories.length === 0 && (
        <div className="empty-state">
          <p>No stories to show.</p>
        </div>
      )}

      {!contentLoading && tab === 'stories' && stories.length > 0 && (
        <div className="story-grid">
          {stories.map((s) => (
            <Link to={`/public/stories/${s.id}`} key={s.id} className="story-card">
              <h3>{s.title}</h3>
              {s.description && <p className="description">{s.description}</p>}
              <div className="story-meta">
                <span>{s.chapter_count} ch</span>
                {s.language && <span>{s.language}</span>}
              </div>
              <div style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)', marginTop: '0.25rem', display: 'flex', justifyContent: 'space-between' }}>
                <span>{s.world_name ? s.world_name : ''}</span>
                <span className="vote-score-inline">&#9650; {(s.upvotes || 0) - (s.downvotes || 0)}</span>
              </div>
            </Link>
          ))}
        </div>
      )}

      {/* Worlds tab */}
      {!contentLoading && tab === 'worlds' && worlds.length === 0 && (
        <div className="empty-state">
          <p>No worlds to show.</p>
        </div>
      )}

      {!contentLoading && tab === 'worlds' && worlds.length > 0 && (
        <div className="story-grid">
          {worlds.map((w) => (
            <Link to={`/worlds/${w.id}`} key={w.id} className="story-card">
              <h3>{w.name}</h3>
              {w.description && <p className="description">{w.description}</p>}
              <div className="story-meta">
                <span>{w.story_count} stories</span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
