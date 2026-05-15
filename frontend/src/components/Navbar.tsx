import { useState, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';
import { LANGUAGES, ALL_LANGUAGES } from '../languages';
import { apiFetch } from '../api';
import type { NewFollowersResponse } from '../types';

export default function Navbar() {
  const { user, isAuthenticated, logout } = useAuth();
  const { language, setLanguage } = useLanguage();
  const navigate = useNavigate();
  const location = useLocation();
  const [newFollowerCount, setNewFollowerCount] = useState(0);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) {
      setNewFollowerCount(0);
      return;
    }
    apiFetch<NewFollowersResponse>('/follows/new-followers')
      .then((data) => setNewFollowerCount(data.count))
      .catch(() => {});
  }, [isAuthenticated]);

  // Close menu whenever the route changes
  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname]);

  const closeMenu = () => setMenuOpen(false);

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
          <Link to="/" className="navbar-logo" onClick={closeMenu}>Lingolou</Link>
          <select
            className="navbar-language-select"
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
          >
            <option value={ALL_LANGUAGES}>Any</option>
            {LANGUAGES.map((lang) => (
              <option key={lang} value={lang}>{lang}</option>
            ))}
          </select>
        </div>

        {/* Hamburger — only visible on mobile */}
        <button
          className={`navbar-hamburger${menuOpen ? ' open' : ''}`}
          onClick={() => setMenuOpen((o) => !o)}
          aria-label={menuOpen ? 'Close menu' : 'Open menu'}
          aria-expanded={menuOpen}
        >
          <span />
          <span />
          <span />
        </button>

        <div className={`navbar-right${menuOpen ? ' navbar-menu-open' : ''}`}>
          {isAuthenticated ? (
            <>
              <Link to="/timeline" className="btn btn-ghost btn-sm" onClick={closeMenu}>Timeline</Link>
              <Link to="/dashboard" className="btn btn-ghost btn-sm" onClick={closeMenu}>My Stories</Link>
              <Link to="/bookmarks" className="btn btn-ghost btn-sm" onClick={closeMenu}>Bookmarks</Link>
              <Link to="/worlds" className="btn btn-ghost btn-sm" onClick={closeMenu}>Worlds</Link>
              <Link to="/settings" className="btn btn-ghost btn-sm" onClick={closeMenu}>Settings</Link>
              <button
                className="btn btn-ghost btn-sm"
                onClick={() => { closeMenu(); handleFollowersBadgeClick(); }}
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
              <span className="navbar-user">{user?.display_name || user?.username}</span>
              <button className="btn btn-ghost btn-sm" onClick={() => { closeMenu(); logout(); }}>
                Log out
              </button>
            </>
          ) : (
            <Link to="/login" className="btn btn-ghost btn-sm" onClick={closeMenu}>Log in</Link>
          )}
        </div>
      </div>
    </nav>
  );
}
