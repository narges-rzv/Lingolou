import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';
import { LANGUAGES } from '../languages';
import { apiFetch } from '../api';
import type { NewFollowersResponse } from '../types';

export default function Navbar() {
  const { user, isAuthenticated, logout } = useAuth();
  const { language, setLanguage } = useLanguage();
  const navigate = useNavigate();
  const [newFollowerCount, setNewFollowerCount] = useState(0);

  useEffect(() => {
    if (!isAuthenticated) {
      setNewFollowerCount(0);
      return;
    }
    apiFetch<NewFollowersResponse>('/follows/new-followers')
      .then((data) => setNewFollowerCount(data.count))
      .catch(() => {});
  }, [isAuthenticated]);

  const handleFollowersBadgeClick = async () => {
    if (user) {
      try {
        await apiFetch('/follows/new-followers/seen', { method: 'POST' });
        setNewFollowerCount(0);
      } catch {
        // ignore
      }
      navigate('/followers');
    }
  };

  return (
    <nav className="navbar">
      <div className="navbar-inner">
        <div className="navbar-left">
          <Link to="/" className="navbar-logo">Lingolou</Link>
          <select
            className="navbar-language-select"
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
          >
            {LANGUAGES.map((lang) => (
              <option key={lang} value={lang}>{lang}</option>
            ))}
          </select>
        </div>
        <div className="navbar-right">
          {isAuthenticated ? (
            <>
              <Link to="/timeline" className="btn btn-ghost btn-sm">Timeline</Link>
              <Link to="/dashboard" className="btn btn-ghost btn-sm">My Stories</Link>
              <Link to="/bookmarks" className="btn btn-ghost btn-sm">Bookmarks</Link>
              <Link to="/worlds" className="btn btn-ghost btn-sm">Worlds</Link>
              <Link to="/settings" className="btn btn-ghost btn-sm">Settings</Link>
              <button
                className="btn btn-ghost btn-sm"
                onClick={handleFollowersBadgeClick}
                style={{ position: 'relative' }}
              >
                Followers
                {newFollowerCount > 0 && (
                  <span
                    data-testid="new-followers-badge"
                    style={{
                      position: 'absolute',
                      top: '-4px',
                      right: '-4px',
                      background: 'var(--color-danger, #e53e3e)',
                      color: '#fff',
                      borderRadius: '50%',
                      width: '18px',
                      height: '18px',
                      fontSize: '0.7rem',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontWeight: 700,
                    }}
                  >
                    {newFollowerCount}
                  </span>
                )}
              </button>
              <span className="navbar-user">{user?.username}</span>
              <button className="btn btn-ghost btn-sm" onClick={logout}>
                Log out
              </button>
            </>
          ) : (
            <Link to="/login" className="btn btn-ghost btn-sm">Log in</Link>
          )}
        </div>
      </div>
    </nav>
  );
}
