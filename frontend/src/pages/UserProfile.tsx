import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { apiFetch } from '../api';
import FollowButton from '../components/FollowButton';
import type { UserProfileResponse } from '../types';

export default function UserProfile() {
  const { id } = useParams();
  const { user } = useAuth();
  const [profile, setProfile] = useState<UserProfileResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    apiFetch<UserProfileResponse>(`/follows/users/${id}/profile`)
      .then(setProfile)
      .catch((err: unknown) => setError((err as Error).message))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="loading">Loading profile...</div>;
  if (error || !profile) return <div className="error-message">{error || 'User not found'}</div>;

  const isOwnProfile = user?.id === profile.id;

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1.5rem' }}>
        <h1 style={{ margin: 0 }}>{profile.username}</h1>
        {!isOwnProfile && (
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
      </div>

      <div className="stats-row" style={{ display: 'flex', gap: '2rem', marginBottom: '1.5rem' }}>
        <div>
          <strong>{profile.story_count}</strong>
          <span style={{ color: 'var(--color-text-secondary)', marginLeft: '0.25rem' }}>stories</span>
        </div>
        <div>
          <strong>{profile.world_count}</strong>
          <span style={{ color: 'var(--color-text-secondary)', marginLeft: '0.25rem' }}>worlds</span>
        </div>
        <div>
          <strong>{profile.follower_count}</strong>
          <span style={{ color: 'var(--color-text-secondary)', marginLeft: '0.25rem' }}>followers</span>
        </div>
        <div>
          <strong>{profile.following_count}</strong>
          <span style={{ color: 'var(--color-text-secondary)', marginLeft: '0.25rem' }}>following</span>
        </div>
      </div>

      <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.85rem' }}>
        Joined {new Date(profile.created_at).toLocaleDateString()}
      </p>
    </div>
  );
}
