import React, { useState, useEffect } from 'react';
import { ThemeProvider } from './contexts/ThemeContext';
import { SessionContext, type SessionUser } from './contexts/SessionContext';
import { apiFetch } from './lib/api';
import Home from './pages/Home';
import Dashboard from './pages/Dashboard';
import NotFound from './pages/NotFound';

import Login from './pages/Login';

/**
 * Simple hash-based router.
 * Routes:
 *   /           → Home
 *   /login      → Login
 *   /dashboard  → Dashboard (Protected)
 *   *           → NotFound
 */
function useRoute() {
  const [path, setPath] = useState(window.location.pathname);

  useEffect(() => {
    const onPopState = () => setPath(window.location.pathname);
    window.addEventListener('popstate', onPopState);

    // Intercept <a> clicks for SPA navigation
    const onClick = (e: MouseEvent) => {
      const anchor = (e.target as HTMLElement).closest('a');
      if (
        anchor &&
        anchor.href &&
        anchor.origin === window.location.origin &&
        !anchor.hasAttribute('download') &&
        anchor.target !== '_blank'
      ) {
        e.preventDefault();
        // Keep the query and hash so links like /dashboard?view=explainability survive.
        const target = anchor.pathname + anchor.search + anchor.hash;
        if (target !== window.location.pathname + window.location.search + window.location.hash) {
          window.history.pushState(null, '', target);
          setPath(anchor.pathname);
        }
      }
    };

    document.addEventListener('click', onClick);
    return () => {
      window.removeEventListener('popstate', onPopState);
      document.removeEventListener('click', onClick);
    };
  }, []);

  return path;
}

// The server decides who is signed in: the dashboard renders only after /api/auth/me
// accepts the HttpOnly session cookie. A 401 there redirects to /login (see apiFetch).
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<SessionUser | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    apiFetch<SessionUser>('/api/auth/me')
      .then(u => { if (active) setUser(u); })
      .catch((err: Error) => { if (active) setError(err.message); });
    return () => { active = false; };
  }, []);

  if (user) return <SessionContext.Provider value={user}>{children}</SessionContext.Provider>;
  return (
    <div className="session-gate" role="status">
      {error ? <>Could not confirm your session ({error}). <a href="/login">Sign in again</a>.</> : 'Checking your session'}
    </div>
  );
}

function Router() {
  const path = useRoute();

  switch (path) {
    case '/':
      return <Home />;
    case '/login':
      return <Login />;
    case '/dashboard':
      return (
        <ProtectedRoute>
          <Dashboard />
        </ProtectedRoute>
      );
    default:
      return <NotFound />;
  }
}

const App: React.FC = () => {
  return (
    <ThemeProvider defaultTheme="dark">
      <Router />
    </ThemeProvider>
  );
};

export default App;
