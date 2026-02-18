import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';
import { apiFetch, publicApiFetch } from '../api';
import { LANGUAGES } from '../languages';
import BudgetBanner from '../components/BudgetBanner';
import StoryCard from '../components/StoryCard';
import PublicStoryCard from '../components/PublicStoryCard';
import InfoFooter from '../components/InfoFooter';
import type { StoryListResponse, PublicStoryListItem } from '../types';

export default function Dashboard() {
  const { user } = useAuth();
  const { language, setLanguage } = useLanguage();
  const [userStories, setUserStories] = useState<StoryListResponse[]>([]);
  const [publicStories, setPublicStories] = useState<PublicStoryListItem[]>([]);
  const [loadingUser, setLoadingUser] = useState(true);
  const [loadingPublic, setLoadingPublic] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoadingUser(true);
    apiFetch('/stories/')
      .then(setUserStories)
      .catch((err: unknown) => setError((err as Error).message))
      .finally(() => setLoadingUser(false));
  }, []);

  useEffect(() => {
    setLoadingPublic(true);
    const url = `/public/stories?language=${encodeURIComponent(language)}`;
    publicApiFetch(url)
      .then(setPublicStories)
      .catch(() => setPublicStories([]))
      .finally(() => setLoadingPublic(false));
  }, [language]);

  return (
    <div className="home-page">
      {/* Welcome header with language picker */}
      <div className="hero-section">
        <h1 className="hero-title">Welcome back, {user?.username}</h1>
        <p className="hero-description">
          Pick a language and create a new story, or browse public stories from the community.
          Your stories and the public library are both shown below.
        </p>
        <div className="hero-language-picker">
          <select
            className="hero-language-select"
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
          >
            {LANGUAGES.map((lang) => (
              <option key={lang} value={lang}>{lang}</option>
            ))}
          </select>
        </div>
      </div>

      <BudgetBanner />

      {error && <div className="error-message">{error}</div>}

      {/* Two-column layout: public on left, user on right */}
      <div className="home-columns">
        {/* Left: Public Stories */}
        <div className="home-column">
          <div className="column-header">
            <h2>Public Stories — {language}</h2>
          </div>
          {loadingPublic ? (
            <p className="column-loading">Loading stories...</p>
          ) : publicStories.length === 0 ? (
            <div className="empty-state">
              <p>No public stories yet for {language}.</p>
            </div>
          ) : (
            <div className="column-story-list">
              {publicStories.map((story) => (
                <PublicStoryCard key={story.id} story={story} />
              ))}
            </div>
          )}
        </div>

        {/* Right: User Stories */}
        <div className="home-column">
          <div className="column-header">
            <h2>My Stories</h2>
            <Link to="/stories/new" className="btn btn-primary btn-sm">New Story</Link>
          </div>
          {loadingUser ? (
            <p className="column-loading">Loading your stories...</p>
          ) : userStories.length === 0 ? (
            <div className="empty-state">
              <p>You haven&apos;t created any stories yet.</p>
              <Link to="/stories/new" className="btn btn-primary">
                Create your first story
              </Link>
            </div>
          ) : (
            <div className="column-story-list">
              {userStories.map((story) => (
                <StoryCard key={story.id} story={story} />
              ))}
            </div>
          )}
        </div>
      </div>

      <InfoFooter />
    </div>
  );
}
