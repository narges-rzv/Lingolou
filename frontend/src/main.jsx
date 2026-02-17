import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { LanguageProvider } from './context/LanguageContext';
import App from './App';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import NewStory from './pages/NewStory';
import EditStory from './pages/EditStory';
import StoryDetail from './pages/StoryDetail';
import PublicStories from './pages/PublicStories';
import PublicStoryDetail from './pages/PublicStoryDetail';
import SharedStoryView from './pages/SharedStoryView';
import Worlds from './pages/Worlds';
import WorldDetail from './pages/WorldDetail';
import Settings from './pages/Settings';
import './app.css';

function PrivateRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return <div className="loading">Loading...</div>;
  return isAuthenticated ? children : <Navigate to="/login" />;
}

function LoginRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return <div className="loading">Loading...</div>;
  return isAuthenticated ? <Navigate to="/dashboard" /> : children;
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <LanguageProvider>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginRoute><Login /></LoginRoute>} />
          <Route element={<App />}>
            <Route path="/" element={<PublicStories />} />
            <Route path="/public/stories/:id" element={<PublicStoryDetail />} />
            <Route path="/share/:shareCode" element={<SharedStoryView />} />
            <Route path="/dashboard" element={<PrivateRoute><Dashboard /></PrivateRoute>} />
            <Route path="/stories/new" element={<PrivateRoute><NewStory /></PrivateRoute>} />
            <Route path="/stories/:id" element={<PrivateRoute><StoryDetail /></PrivateRoute>} />
            <Route path="/stories/:id/edit" element={<PrivateRoute><EditStory /></PrivateRoute>} />
            <Route path="/worlds" element={<PrivateRoute><Worlds /></PrivateRoute>} />
            <Route path="/worlds/:id" element={<PrivateRoute><WorldDetail /></PrivateRoute>} />
            <Route path="/settings" element={<PrivateRoute><Settings /></PrivateRoute>} />
          </Route>
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </AuthProvider>
      </LanguageProvider>
    </BrowserRouter>
  </StrictMode>
);
