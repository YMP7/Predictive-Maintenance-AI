import { createBrowserRouter, Navigate, Outlet } from 'react-router';

import { SessionContext } from '../contexts/SessionContext';
import { AppShell } from '../design/shell';
import {
  AlarmsPage,
  AssetByKind,
  AssetGallery,
  AssetIndex,
  AssetPage,
  ChatPage,
  CognitionPage,
  CrossDomainPage,
  DevicesPage,
  DiagnosticsPage,
  FleetPage,
  Gallery,
  LegacyDashboard,
  LegacyHome,
  LoginPage,
  ModelsPage,
  OnboardingPage,
  RedirectDashboard,
  UsersPage,
  WorkOrdersPage,
} from './lazyPages';
import { NotFoundPage, Pending } from './Pending';
import { RequireRole, RequireSession } from './session';

const pending = (title: string, purpose: string, phase: string, builds: string[]) => <Pending title={title} purpose={purpose} phase={phase} builds={builds} />;

const productRoutes = [
  { index: true, element: <Navigate to="/fleet" replace /> },
  { path: 'fleet', element: <FleetPage /> },
  { path: 'assets', element: <AssetIndex /> },
  { path: 'assets/kind/:kind', element: <AssetByKind /> },
  { path: 'assets/:domain/:machineId', element: <AssetPage /> },
  { path: 'cross-domain', element: <CrossDomainPage /> },
  { path: 'alarms', element: <AlarmsPage /> },
  { path: 'work-orders', element: <WorkOrdersPage /> },
  {
    path: 'chat',
    element: (
      <RequireRole roles={['admin', 'operator']}>
        <ChatPage />
      </RequireRole>
    ),
  },
  { path: 'about/evidence', element: pending('Evidence', 'Each word of the title, the feature that implements it, and the number that proves it.', 'P6', ['title justification matrix', 'live links into the product']) },
  {
    path: 'admin',
    element: (
      <RequireRole roles={['admin']}>
        <Outlet />
      </RequireRole>
    ),
    children: [
      { index: true, element: <Navigate to="/admin/users" replace /> },
      { path: 'users', element: <UsersPage /> },
      { path: 'onboarding', element: <OnboardingPage /> },
      { path: 'devices', element: <DevicesPage /> },
      { path: 'models', element: <ModelsPage /> },
      { path: 'diagnostics', element: <DiagnosticsPage /> },
      { path: 'cognition', element: <CognitionPage /> },
    ],
  },
];

const devRoutes = import.meta.env.DEV
  ? [
      {
        path: '/dev',
        // Fixed stand-in user so the shell renders without a server session. The API still enforces auth on every call.
        element: (
          <SessionContext.Provider value={{ username: 'gallery', role: 'admin' }}>
            <AppShell />
          </SessionContext.Provider>
        ),
        children: [
          { path: 'components', element: <Gallery /> },
          { path: 'assets', element: <AssetGallery /> },
          { path: 'assets/:domain/:machineId', element: <AssetGallery /> },
        ],
      },
    ]
  : [];

export const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  { path: '/legacy/home', element: <LegacyHome /> },
  {
    path: '/legacy/dashboard',
    element: (
      <RequireSession>
        <LegacyDashboard />
      </RequireSession>
    ),
  },
  { path: '/dashboard', element: <RedirectDashboard /> },
  ...devRoutes,
  {
    path: '/',
    element: (
      <RequireSession>
        <AppShell />
      </RequireSession>
    ),
    children: [...productRoutes, { path: '*', element: <NotFoundPage /> }],
  },
]);
