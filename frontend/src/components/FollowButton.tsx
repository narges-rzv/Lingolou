import { useState } from 'react';
import { apiFetch } from '../api';
import type { FollowResponse } from '../types';

interface FollowButtonProps {
  userId: number;
  initialFollowing: boolean;
  onToggle?: (following: boolean) => void;
}

export default function FollowButton({ userId, initialFollowing, onToggle }: FollowButtonProps) {
  const [following, setFollowing] = useState(initialFollowing);
  const [loading, setLoading] = useState(false);

  const handleClick = async () => {
    setLoading(true);
    try {
      const data = await apiFetch<FollowResponse>(`/follows/users/${userId}`, {
        method: 'POST',
      });
      setFollowing(data.following);
      onToggle?.(data.following);
    } catch {
      // silently ignore — user will see button state didn't change
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      className={`btn btn-sm${following ? ' btn-ghost' : ' btn-primary'}`}
      onClick={handleClick}
      disabled={loading}
    >
      {following ? 'Following' : 'Follow'}
    </button>
  );
}
