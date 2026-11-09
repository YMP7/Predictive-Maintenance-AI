import { lazy, Suspense, type ComponentType, type ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router';

import { SkeletonRows } from '../design/states';

/* Legacy pages keep the old stylesheet and stay reachable until P4 replaces them (removed in P7). */
const LegacyStyles = lazy(() => import('./LegacyStyles'));
const Home = lazy(() => import('../pages/Home'));
const Dashboard = lazy(() => import('../pages/Dashboard'));

function WithLegacyStyles({ children }: { children: ReactNode }) {
  return (
    <Suspense fallback={<SkeletonRows rows={6} />}>
      <LegacyStyles>{children}</LegacyStyles>
    </Suspense>
  );
}

/* P4 product pages, each its own chunk. */
const suspended = (C: ComponentType) => (
  <Suspense fallback={<SkeletonRows rows={6} />}>
    <C />
  </Suspense>
);

const LoginImpl = lazy(() => import('../pages/ops/LoginPage'));
const FleetImpl = lazy(() => import('../pages/ops/FleetPage'));
const AlarmsImpl = lazy(() => import('../pages/ops/AlarmsPage'));
const WorkOrdersImpl = lazy(() => import('../pages/ops/WorkOrdersPage'));
const CrossDomainImpl = lazy(() => import('../pages/ops/CrossDomainPage'));
const ChatImpl = lazy(() => import('../pages/ops/ChatPage'));
const OnboardingImpl = lazy(() => import('../pages/ops/OnboardingPage'));
const UsersImpl = lazy(() => import('../pages/ops/AdminPages').then(m => ({ default: m.UsersPage })));
const DevicesImpl = lazy(() => import('../pages/ops/AdminPages').then(m => ({ default: m.DevicesPage })));
const DiagnosticsImpl = lazy(() => import('../pages/ops/AdminPages').then(m => ({ default: m.DiagnosticsPage })));

export function LoginPage() {
  return suspended(LoginImpl);
}
export function FleetPage() {
  return suspended(FleetImpl);
}
export function AlarmsPage() {
  return suspended(AlarmsImpl);
}
export function WorkOrdersPage() {
  return suspended(WorkOrdersImpl);
}
export function CrossDomainPage() {
  return suspended(CrossDomainImpl);
}
export function ChatPage() {
  return suspended(ChatImpl);
}
export function OnboardingPage() {
  return suspended(OnboardingImpl);
}
export function UsersPage() {
  return suspended(UsersImpl);
}
export function DevicesPage() {
  return suspended(DevicesImpl);
}
export function DiagnosticsPage() {
  return suspended(DiagnosticsImpl);
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

/* 3D Asset View: three.js and the five machines load only with these pages. */
const AssetIndexImpl = lazy(() => import('../pages/asset/AssetIndex'));
const AssetByKindImpl = lazy(() => import('../pages/asset/AssetIndex').then(m => ({ default: m.AssetByKind })));
const AssetPageImpl = lazy(() => import('../pages/asset/AssetPage'));
const pageFallback = <SkeletonRows rows={6} />;

export function AssetIndex() {
  return (
    <Suspense fallback={pageFallback}>
      <AssetIndexImpl />
    </Suspense>
  );
}

export function AssetByKind() {
  return (
    <Suspense fallback={pageFallback}>
      <AssetByKindImpl />
    </Suspense>
  );
}

export function AssetPage() {
  return (
    <Suspense fallback={pageFallback}>
      <AssetPageImpl />
    </Suspense>
  );
}

/* Dev-only gallery: Vite replaces import.meta.env.DEV with false in production, so the chunk is dropped. */
const GalleryImpl = import.meta.env.DEV ? lazy(() => import('../dev/ComponentGallery')) : null;

export function Gallery() {
  return GalleryImpl ? <GalleryImpl /> : null;
}

const AssetGalleryImpl = import.meta.env.DEV ? lazy(() => import('../dev/AssetGallery')) : null;

export function AssetGallery() {
  return AssetGalleryImpl ? (
    <Suspense fallback={pageFallback}>
      <AssetGalleryImpl />
    </Suspense>
  ) : null;
}
