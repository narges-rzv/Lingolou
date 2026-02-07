import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import App from './App';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import NewStory from './pages/NewStory';
import EditStory from './pages/EditStory';
import StoryDetail from './pages/StoryDetail';
import './app.css';

function PrivateRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return <div className="loading">Loading...</div>;
  return isAuthenticated ? children : <Navigate to="/login" />;
}

function PublicRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return <div className="loading">Loading...</div>;
  return isAuthenticated ? <Navigate to="/" /> : children;
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<PublicRoute><Login /></PublicRoute>} />
          <Route element={<App />}>
            <Route path="/" element={<PrivateRoute><Dashboard /></PrivateRoute>} />
            <Route path="/stories/new" element={<PrivateRoute><NewStory /></PrivateRoute>} />
            <Route path="/stories/:id" element={<PrivateRoute><StoryDetail /></PrivateRoute>} />
            <Route path="/stories/:id/edit" element={<PrivateRoute><EditStory /></PrivateRoute>} />
          </Route>
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>
);
