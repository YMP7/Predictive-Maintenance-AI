import { createBrowserRouter, Navigate, Outlet } from 'react-router';

import { SessionContext } from '../contexts/SessionContext';
import { AppShell } from '../design/shell';
import { AssetByKind, AssetGallery, AssetIndex, AssetPage, Gallery, LegacyDashboard, LegacyHome, LegacyLogin, RedirectDashboard } from './lazyPages';
import { NotFoundPage, Pending } from './Pending';
import { RequireRole, RequireSession } from './session';

const pending = (title: string, purpose: string, phase: string, builds: string[]) => <Pending title={title} purpose={purpose} phase={phase} builds={builds} />;

const productRoutes = [
  { index: true, element: <Navigate to="/fleet" replace /> },
  {
    path: 'fleet',
    element: pending('Fleet overview', 'Every asset across all machine types, ranked by what needs attention.', 'P4', [
      'health grid of all assets',
      'alarm summary',
      'RUL-at-risk list',
      'ingestion health per device',
    ]),
  },
  { path: 'assets', element: <AssetIndex /> },
  { path: 'assets/kind/:kind', element: <AssetByKind /> },
  // shortcut: live trends, RUL band, work orders and the AMKB panel join this page in P4
  { path: 'assets/:domain/:machineId', element: <AssetPage /> },
  {
    path: 'cross-domain',
    element: pending('Cross-domain view', 'The same pipeline across a turbofan, a laptop, a phone, a server and a pump.', 'P4', [
      'normalised health and RUL per domain',
      'per-domain metrics',
    ]),
  },
  { path: 'alarms', element: pending('Alarms & events', 'ISA-18.2 alarm list.', 'P4', ['acknowledge and shelve with reason', 'alarm-flood indicator', 'event history']) },
  { path: 'work-orders', element: pending('Work orders', 'Recommended maintenance actions from creation to closure.', 'P4', ['lifecycle', 'assignment', 'approve and reject with confirmation']) },
  {
    path: 'chat',
    element: (
      <RequireRole roles={['admin', 'operator']}>
        {pending('Agent chat', 'Ask about a machine. Answers cite AMKB memory.', 'P4', ['restyled chat', 'AMKB citations inline'])}
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
      { path: 'users', element: pending('Users & roles', 'Accounts and what each role may do.', 'P4', ['user list', 'role assignment']) },
      { path: 'onboarding', element: pending('Sensor onboarding', 'Connect a new asset in seven steps.', 'P4', ['register asset', 'protocol and credentials', 'channel mapping', 'live validation preview', '3D part binding', 'activate']) },
      { path: 'devices', element: pending('Devices', 'Connection health of every device.', 'P4', ['last seen', 'message rate', 'error rate', 'data quality']) },
      { path: 'models', element: pending('Model registry', 'Model versions and their metrics.', 'P5', ['versions', 'metrics', 'promote and roll back with confirmation']) },
      { path: 'diagnostics', element: pending('Diagnostics', 'Health of the platform itself.', 'P4', ['database, broker and model status', 'latency']) },
      { path: 'cognition', element: pending('Cognition', 'The pipeline stage by stage for any machine and time.', 'P5', ['10 stage panels', 'per-stage latency', 'drift monitor', 'replay']) },
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
  { path: '/login', element: <LegacyLogin /> },
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
