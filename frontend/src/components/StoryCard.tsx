import { Link } from 'react-router-dom';
import type { StoryListResponse } from '../types';

interface StoryCardProps {
  story: StoryListResponse;
}

function statusClass(status: string | undefined): string {
  return `status-badge status-${status || 'created'}`;
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

export default function StoryCard({ story }: StoryCardProps) {
  return (
    <Link to={`/stories/${story.id}`} className="story-card">
      <h3>{story.title}</h3>
      {story.description && (
        <p className="description">{story.description}</p>
      )}
      <div className="story-card-footer">
        <span className={statusClass(story.status)}>{story.status}</span>
        <span>
          {story.world_name && `${story.world_name} \u00b7 `}
          {story.chapter_count} chapter{story.chapter_count !== 1 ? 's' : ''}
          {' \u00b7 '}
          {formatDate(story.created_at)}
        </span>
      </div>
    </Link>
  );
}
