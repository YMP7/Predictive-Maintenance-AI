import { createContext, useContext } from 'react';

export interface SessionUser {
  username: string;
  role: 'admin' | 'operator' | 'viewer' | string;
}

// Filled from GET /api/auth/me by the protected route, so the UI never trusts a
// client-side cookie for who is signed in or what they may do.
export const SessionContext = createContext<SessionUser | null>(null);

export function useSession(): SessionUser {
  const user = useContext(SessionContext);
  if (!user) throw new Error('useSession must be used inside a signed-in route');
  return user;
}
