import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';
import { publicApiFetch, apiFetch } from '../api';
import { LANGUAGES } from '../languages';
import BudgetBanner from '../components/BudgetBanner';
import StoryCard from '../components/StoryCard';
import PublicStoryCard from '../components/PublicStoryCard';
import InfoFooter from '../components/InfoFooter';

export default function PublicStories() {
  const { isAuthenticated } = useAuth();
  const { language, setLanguage } = useLanguage();
  const [publicStories, setPublicStories] = useState([]);
  const [userStories, setUserStories] = useState([]);
  const [loadingPublic, setLoadingPublic] = useState(true);
  const [loadingUser, setLoadingUser] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoadingPublic(true);
    const url = `/public/stories?language=${encodeURIComponent(language)}`;
    publicApiFetch(url)
      .then(setPublicStories)
      .catch((err) => setError(err.message))
      .finally(() => setLoadingPublic(false));
  }, [language]);

  useEffect(() => {
    if (!isAuthenticated) {
      setUserStories([]);
      return;
    }
    setLoadingUser(true);
    apiFetch('/stories/')
      .then(setUserStories)
      .catch(() => setUserStories([]))
      .finally(() => setLoadingUser(false));
  }, [isAuthenticated]);

  return (
    <div className="home-page">
      {/* Hero Section */}
      <div className="hero-section">
        <h1 className="hero-title">Lingolou</h1>
        <p className="hero-description">
          Lingolou is a basic service that helps you create an audio file of a story for your kid,
          to teach them the language of your choice. The starting point is stories that connect
          with your child, which introduce new characters in the language you want, and allow you
          to customize the story fully. Select the language that you are interested in.
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

      {/* Two-column layout */}
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
            {isAuthenticated && (
              <Link to="/stories/new" className="btn btn-primary btn-sm">New Story</Link>
            )}
          </div>
          {!isAuthenticated ? (
            <div className="empty-state">
              <p>Log in to create and manage your own stories.</p>
              <Link to="/login" className="btn btn-primary">Log in</Link>
            </div>
          ) : loadingUser ? (
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
