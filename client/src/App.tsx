import React, { useState, useEffect } from 'react';
import { ThemeProvider } from './contexts/ThemeContext';
import Home from './pages/Home';
import Dashboard from './pages/Dashboard';
import NotFound from './pages/NotFound';

/**
 * Simple hash-based router.
 * Routes:
 *   /           → Home
 *   /dashboard  → Dashboard
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

function Router() {
  const path = useRoute();

  switch (path) {
    case '/':
      return <Home />;
    case '/dashboard':
      return <Dashboard />;
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
