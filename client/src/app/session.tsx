import { useEffect, useState, type ReactNode } from 'react';
import { ShieldAlert } from 'lucide-react';

import { SessionContext, useSession, type SessionUser } from '../contexts/SessionContext';
import { ErrorState, EmptyState, SkeletonRows } from '../design/states';
import type { Role } from '../design/types';
import { apiFetch } from '../lib/api';

/** The server decides who is signed in: children render only after /api/auth/me accepts the cookie.
    A 401 redirects to /login (handled in apiFetch). */
export function RequireSession({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<SessionUser | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let alive = true;
    apiFetch<SessionUser>('/api/auth/me')
      .then(u => alive && setUser(u))
      .catch(e => alive && setError(e));
    return () => {
      alive = false;
    };
  }, [attempt]);

  if (user) return <SessionContext.Provider value={user}>{children}</SessionContext.Provider>;
  if (error)
    return (
      <ErrorState
        title="Could not confirm your session"
        error={error}
        onRetry={() => {
          setError(null);
          setAttempt(a => a + 1);
        }}
      />
    );
  return <SkeletonRows rows={6} />;
}

/** UI-side role gate. Hides the page for other roles; the API returns 403 regardless. */
export function RequireRole({ roles, children }: { roles: Role[]; children: ReactNode }) {
  const user = useSession();
  if (roles.includes(user.role as Role)) return <>{children}</>;
  return (
    <EmptyState
      icon={<ShieldAlert className="ax-state__icon" aria-hidden />}
      title="Not available for your role"
      body={`This page needs the ${roles.join(' or ')} role. You are signed in as ${user.role}.`}
    />
  );
}
