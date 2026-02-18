import { Link } from 'react-router-dom';
import type { PublicStoryListItem } from '../types';

interface PublicStoryCardProps {
  story: PublicStoryListItem;
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

export default function PublicStoryCard({ story }: PublicStoryCardProps) {
  return (
    <Link to={`/public/stories/${story.id}`} className="story-card">
      <h3>{story.title}</h3>
      {story.description && (
        <p className="description">{story.description}</p>
      )}
      <div className="story-card-footer">
        <span className="status-badge status-completed">{story.status}</span>
        <span>
          {story.chapter_count} chapter{story.chapter_count !== 1 ? 's' : ''}
          {' \u00b7 '}
          {formatDate(story.created_at)}
        </span>
      </div>
      <div style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)', marginTop: '0.25rem', display: 'flex', justifyContent: 'space-between' }}>
        <span>by {story.owner_name}{story.world_name ? ` \u00b7 ${story.world_name}` : ''}</span>
        <span className="vote-score-inline">
          &#9650; {(story.upvotes || 0) - (story.downvotes || 0)}
        </span>
      </div>
    </Link>
  );
}
