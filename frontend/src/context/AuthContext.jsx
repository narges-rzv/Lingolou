import { createContext, useContext, useState, useEffect } from 'react';
import { apiFetch, loginRequest, registerRequest } from '../api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Handle OAuth redirect: ?token= or ?error= in URL
    const params = new URLSearchParams(window.location.search);
    const oauthToken = params.get('token');
    const oauthError = params.get('error');

    if (oauthToken) {
      localStorage.setItem('token', oauthToken);
      window.history.replaceState({}, '', window.location.pathname);
    } else if (oauthError) {
      window.history.replaceState({}, '', window.location.pathname + '?error=' + oauthError);
    }

    const token = localStorage.getItem('token');
    if (token) {
      apiFetch('/auth/me')
        .then(setUser)
        .catch(() => localStorage.removeItem('token'))
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = async (username, password) => {
    const data = await loginRequest(username, password);
    localStorage.setItem('token', data.access_token);
    const me = await apiFetch('/auth/me');
    setUser(me);
  };

  const register = async (email, username, password) => {
    await registerRequest(email, username, password);
    await login(username, password);
  };

  const logout = () => {
    localStorage.removeItem('token');
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{ user, isAuthenticated: !!user, loading, login, register, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
