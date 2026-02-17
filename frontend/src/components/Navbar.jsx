import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';
import { LANGUAGES } from '../languages';

export default function Navbar() {
  const { user, isAuthenticated, logout } = useAuth();
  const { language, setLanguage } = useLanguage();

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
              <Link to="/dashboard" className="btn btn-ghost btn-sm">My Stories</Link>
              <Link to="/worlds" className="btn btn-ghost btn-sm">Worlds</Link>
              <Link to="/settings" className="btn btn-ghost btn-sm">Settings</Link>
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
