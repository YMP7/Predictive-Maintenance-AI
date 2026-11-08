import {
  Activity,
  BellRing,
  Boxes,
  BrainCircuit,
  ClipboardList,
  Factory,
  FileCheck2,
  GitCompareArrows,
  MessagesSquare,
  PlugZap,
  Router,
  Users,
  type LucideIcon,
} from 'lucide-react';

import type { Role } from './types';

export interface NavItem {
  path: string;
  label: string;
  icon: LucideIcon;
  group: 'Operate' | 'Understand' | 'Administer';
  /** Roles that see this item. Omitted means every signed-in role. The server enforces the same rule. */
  roles?: Role[];
  /** One line for the command palette. */
  summary: string;
}

export const NAV: NavItem[] = [
  { path: '/fleet', label: 'Fleet overview', icon: Factory, group: 'Operate', summary: 'Health, RUL at risk and ingestion for every asset' },
  { path: '/alarms', label: 'Alarms & events', icon: BellRing, group: 'Operate', summary: 'ISA-18.2 alarm list: acknowledge, shelve, review' },
  { path: '/work-orders', label: 'Work orders', icon: ClipboardList, group: 'Operate', summary: 'Recommended actions through approval and closure' },
  { path: '/cross-domain', label: 'Cross-domain view', icon: GitCompareArrows, group: 'Understand', summary: 'Normalised health and RUL across unlike machines' },
  { path: '/chat', label: 'Agent chat', icon: MessagesSquare, group: 'Understand', roles: ['admin', 'operator'], summary: 'Ask about a machine; answers cite AMKB memory' },
  { path: '/about/evidence', label: 'Evidence', icon: FileCheck2, group: 'Understand', summary: 'Every title term mapped to working features and metrics' },
  { path: '/admin/cognition', label: 'Cognition', icon: BrainCircuit, group: 'Administer', roles: ['admin'], summary: 'The pipeline stage by stage for any machine and time' },
  { path: '/admin/onboarding', label: 'Sensor onboarding', icon: PlugZap, group: 'Administer', roles: ['admin'], summary: 'Register an asset, map channels, activate' },
  { path: '/admin/devices', label: 'Devices', icon: Router, group: 'Administer', roles: ['admin'], summary: 'Connection health per device' },
  { path: '/admin/models', label: 'Model registry', icon: Boxes, group: 'Administer', roles: ['admin'], summary: 'Versions, metrics, promote and roll back' },
  { path: '/admin/users', label: 'Users & roles', icon: Users, group: 'Administer', roles: ['admin'], summary: 'Accounts and their roles' },
  { path: '/admin/diagnostics', label: 'Diagnostics', icon: Activity, group: 'Administer', roles: ['admin'], summary: 'Platform health: database, broker, models, latency' },
];

export function navFor(role: string): NavItem[] {
  return NAV.filter(n => !n.roles || n.roles.includes(role as Role));
}
