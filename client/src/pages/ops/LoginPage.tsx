import { useId, useState, type FormEvent } from 'react';
import { Moon, Sun } from 'lucide-react';

import { Button } from '../../design/primitives';
import { useTheme } from '../../hooks/useTheme';
import { apiFetch, statusOf } from '../../lib/api';

/** Same-site paths only: "//host" or "/\host" would be an open redirect. */
function nextPath(): string {
  const next = new URLSearchParams(window.location.search).get('next') ?? '';
  return next.startsWith('/') && !next.startsWith('//') && !next.startsWith('/\\') ? next : '/fleet';
}

function describe(err: unknown): string {
  const s = statusOf(err);
  if (s === 401) return 'Wrong username or password.';
  if (s === 429) return 'Too many sign-in attempts. Wait a minute, then try again.';
  if (s !== null) return `Sign-in failed (error ${s}).`;
  return 'Cannot reach the server. Check that the backend is running, then try again.';
}

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [show, setShow] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const { theme, toggleTheme } = useTheme();
  const ids = { u: useId(), p: useId(), t: useId() };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password) {
      setError('Enter your username and password.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      const r = await apiFetch<{ role?: string }>('/api/auth/login', { method: 'POST', body: JSON.stringify({ username: username.trim(), password }) });
      if (r?.role) {
        window.location.href = nextPath();
        return;
      }
      setError('Sign-in failed. Try again.');
    } catch (err) {
      setError(describe(err));
    }
    setBusy(false);
  };

  return (
    <div className="ax-login">
      <header className="ax-login__bar">
        <strong>ATLAS</strong>
        <span className="ax-note">Adaptive machine cognition for predictive maintenance</span>
        <Button variant="ghost" iconOnly label={theme === 'dark' ? 'Light theme' : 'Dark theme'} icon={theme === 'dark' ? <Sun aria-hidden /> : <Moon aria-hidden />} onClick={toggleTheme} />
      </header>
      <main className="ax-login__main">
        <form className="ax-panel ax-login__card" onSubmit={submit} noValidate aria-labelledby={ids.t}>
          <h1 id={ids.t}>Sign in</h1>
          <p className="ax-note">Use the account your administrator created for you.</p>
          {error && (
            <p className="ax-error" role="alert">
              {error}
            </p>
          )}
          <label className="ax-field" htmlFor={ids.u}>
            <span className="ax-field__label">Username</span>
            <input id={ids.u} className="ax-input" name="username" autoComplete="username" autoCapitalize="none" spellCheck={false} value={username} onChange={e => setUsername(e.target.value)} aria-invalid={!!error} autoFocus required />
          </label>
          {/* the reveal button sits outside the label, so the field's accessible name stays "Password" */}
          <div className="ax-field">
            <label className="ax-field__label" htmlFor={ids.p}>
              Password
            </label>
            <span className="ax-row" style={{ flexWrap: 'nowrap' }}>
              <input id={ids.p} className="ax-input" style={{ flex: 1 }} type={show ? 'text' : 'password'} name="password" autoComplete="current-password" value={password} onChange={e => setPassword(e.target.value)} aria-invalid={!!error} required />
              <Button size="sm" variant="ghost" aria-pressed={show} aria-label={show ? 'Hide password' : 'Show password'} onClick={() => setShow(s => !s)}>
                {show ? 'Hide' : 'Show'}
              </Button>
            </span>
          </div>
          <Button type="submit" variant="primary" disabled={busy}>
            {busy ? 'Signing in' : 'Sign in'}
          </Button>
          <p className="ax-note">Forgot your password? Ask your administrator to reset it.</p>
        </form>
      </main>
    </div>
  );
}
