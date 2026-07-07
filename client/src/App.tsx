import React, { useState, useEffect } from 'react';
import { ThemeProvider } from './contexts/ThemeContext';
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
        const newPath = anchor.pathname;
        if (newPath !== window.location.pathname) {
          window.history.pushState(null, '', newPath);
          setPath(newPath);
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

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('token');
  if (!token) {
    window.location.replace('/login');
    return null;
  }
  return <>{children}</>;
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
