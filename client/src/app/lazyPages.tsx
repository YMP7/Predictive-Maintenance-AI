import { lazy, Suspense, type ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router';

import { SkeletonRows } from '../design/states';

/* Legacy pages keep the old stylesheet and stay reachable until P4 replaces them (removed in P7). */
const LegacyStyles = lazy(() => import('./LegacyStyles'));
const Login = lazy(() => import('../pages/Login'));
const Home = lazy(() => import('../pages/Home'));
const Dashboard = lazy(() => import('../pages/Dashboard'));

function WithLegacyStyles({ children }: { children: ReactNode }) {
  return (
    <Suspense fallback={<SkeletonRows rows={6} />}>
      <LegacyStyles>{children}</LegacyStyles>
    </Suspense>
  );
}

export function LegacyLogin() {
  return (
    <WithLegacyStyles>
      <Login />
    </WithLegacyStyles>
  );
}

export function LegacyHome() {
  return (
    <WithLegacyStyles>
      <Home />
    </WithLegacyStyles>
  );
}

export function LegacyDashboard() {
  return (
    <WithLegacyStyles>
      <Dashboard />
    </WithLegacyStyles>
  );
}

/** Old links (/dashboard?view=...) keep working. */
export function RedirectDashboard() {
  const { search } = useLocation();
  return <Navigate to={`/legacy/dashboard${search}`} replace />;
}

/* Dev-only gallery: Vite replaces import.meta.env.DEV with false in production, so the chunk is dropped. */
const GalleryImpl = import.meta.env.DEV ? lazy(() => import('../dev/ComponentGallery')) : null;

export function Gallery() {
  return GalleryImpl ? <GalleryImpl /> : null;
}
