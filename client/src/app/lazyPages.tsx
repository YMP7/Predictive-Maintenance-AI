import { lazy, Suspense, type ComponentType } from 'react';
import { Navigate } from 'react-router';

import { SkeletonRows } from '../design/states';

/** Old bookmarks (/dashboard?view=...) land on the fleet overview. */
export function RedirectDashboard() {
  return <Navigate to="/fleet" replace />;
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
const CognitionImpl = lazy(() => import('../pages/ops/CognitionPage'));
const ModelsImpl = lazy(() => import('../pages/ops/ModelsPage'));
const EvidenceImpl = lazy(() => import('../pages/ops/EvidencePage'));
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
export function CognitionPage() {
  return suspended(CognitionImpl);
}
export function ModelsPage() {
  return suspended(ModelsImpl);
}
export function EvidencePage() {
  return suspended(EvidenceImpl);
}
export function DiagnosticsPage() {
  return suspended(DiagnosticsImpl);
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
