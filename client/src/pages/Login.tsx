import React, { useState } from 'react';
import { apiFetch } from '../lib/api';
import { useTheme } from '../contexts/ThemeContext';
import { Sun, Moon } from 'lucide-react';

// Only same-site dashboard paths are accepted, so ?next= cannot redirect off the site.
function nextPath(): string {
  const next = new URLSearchParams(window.location.search).get('next') ?? '';
  return next.startsWith('/dashboard') ? next : '/dashboard';
}

function describeLoginError(err: unknown): string {
  const msg = err instanceof Error ? err.message : '';
  if (msg.startsWith('API error 401')) return 'Wrong username or password.';
  if (msg.startsWith('API error 429')) return 'Too many sign-in attempts. Wait a minute, then try again.';
  if (msg.startsWith('API error')) return `Sign-in failed (${msg.replace('API error ', '')}).`;
  return 'Cannot reach the server. Check that the backend is running, then try again.';
}

const Login: React.FC = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const { theme, toggleTheme } = useTheme();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password) {
      setError('Enter your username and password.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      const response = await apiFetch<{ role?: string }>('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ username: username.trim(), password }),
      });
      if (response?.role) {
        window.location.href = nextPath();
        return;
      }
      setError('Sign-in failed. Try again.');
    } catch (err) {
      setError(describeLoginError(err));
    }
    setBusy(false);
  };

  return (
    <div className="login">
      <header className="home-bar">
        <a href="/" className="home-wordmark" aria-label="ATLAS home">
          ATLAS <span>Predictive maintenance</span>
        </a>
        <button
          type="button"
          className="home-icon-btn"
          onClick={toggleTheme}
          aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
        >
          {theme === 'dark' ? <Sun size={18} aria-hidden="true" /> : <Moon size={18} aria-hidden="true" />}
        </button>
      </header>

      <main className="login-main">
        <form className="login-card" onSubmit={handleLogin} noValidate aria-labelledby="login-title">
          <h1 id="login-title">Sign in</h1>
          <p className="login-lede">Use the account your administrator created for you.</p>

          {error && <p className="login-error" role="alert">{error}</p>}

          <div className="login-field">
            <label htmlFor="login-username">Username</label>
            <input
              id="login-username"
              type="text"
              name="username"
              autoComplete="username"
              autoCapitalize="none"
              spellCheck={false}
              value={username}
              onChange={e => setUsername(e.target.value)}
              aria-invalid={!!error}
              autoFocus
              required
            />
          </div>

          <div className="login-field">
            <label htmlFor="login-password">Password</label>
            <span className="login-password">
              <input
                id="login-password"
                type={showPassword ? 'text' : 'password'}
                name="password"
                autoComplete="current-password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                aria-invalid={!!error}
                required
              />
              <button
                type="button"
                className="login-reveal"
                onClick={() => setShowPassword(s => !s)}
                aria-pressed={showPassword}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? 'Hide' : 'Show'}
              </button>
            </span>
          </div>

          <button type="submit" className="home-btn home-btn-primary login-submit" disabled={busy}>
            {busy ? 'Signing in' : 'Sign in'}
          </button>

          <p className="login-help">Forgot your password? Ask your administrator to reset it.</p>
        </form>
      </main>

      <footer className="home-footer">
        <span>ATLAS predictive maintenance and digital twin</span>
        <nav aria-label="Footer">
          <a href="/">Home</a>
        </nav>
      </footer>
    </div>
  );
};

export default Login;
