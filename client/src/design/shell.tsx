import { Suspense, useCallback, useEffect, useState, type ReactNode } from 'react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router';
import { LogOut, Moon, PanelLeftClose, PanelLeftOpen, Search, Sun } from 'lucide-react';

import { useSession } from '../contexts/SessionContext';
import { useTheme } from '../hooks/useTheme';
import { API_BASE_URL, apiFetch } from '../lib/api';
import { startClientEvents, track } from '../lib/events';
import { useAlarms } from '../lib/ops';
import { AlarmBanner } from './alarms';
import { KioskBar } from '../app/kiosk';
import { useKiosk } from '../app/kioskState';
import { CommandPalette } from './CommandPalette';
import { getTimeZone, formatTime, zoneLabel } from './format';
import { useNow, useOnline } from './hooks';
import { navFor, type NavItem } from './nav';
import { Button, StatusPill } from './primitives';
import { OfflineNotice, SkeletonRows } from './states';

/* ---------- Brand mark: authored SVG (a meridian ring, for ATLAS) ---------- */

function BrandMark() {
  return (
    <svg viewBox="0 0 20 20" aria-hidden>
      <circle cx="10" cy="10" r="8" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <ellipse cx="10" cy="10" rx="3.6" ry="8" fill="none" stroke="currentColor" strokeWidth="1.2" />
      <path d="M2 10h16" stroke="currentColor" strokeWidth="1.2" />
    </svg>
  );
}

/* ---------- Connection status: polls the public health probe ---------- */

type Link = 'connected' | 'degraded' | 'offline';

function useApiLink(intervalMs = 15000): Link {
  const online = useOnline();
  const [link, setLink] = useState<Link>('connected');
  useEffect(() => {
    let alive = true;
    const probe = async () => {
      try {
        // /api/ready is public and reports database, broker and model state (503 when degraded).
        // Plain fetch: a probe must never send the user to the login page.
        const r = await fetch(`${API_BASE_URL}/api/ready`, { credentials: 'include' });
        if (alive) setLink(r.ok ? 'connected' : 'degraded');
      } catch {
        if (alive) setLink('degraded');
      }
    };
    probe();
    const id = window.setInterval(probe, intervalMs);
    return () => {
      alive = false;
      window.clearInterval(id);
    };
  }, [intervalMs]);
  return online ? link : 'offline';
}

function LinkStatus({ link }: { link: Link }) {
  if (link === 'connected') return <StatusPill tone="quiet">Connected</StatusPill>;
  if (link === 'degraded') return <StatusPill tone="medium">API unreachable</StatusPill>;
  return <StatusPill tone="critical">Offline</StatusPill>;
}

/* ---------- Header ---------- */

const SITE = import.meta.env.VITE_ATLAS_SITE ?? 'Local deployment';

export function Header({ onSearch }: { onSearch: () => void }) {
  const user = useSession();
  const { theme, toggleTheme } = useTheme();
  const now = useNow(1000);
  const link = useApiLink();
  const tz = getTimeZone();
  const logout = async () => {
    try {
      await apiFetch('/api/auth/logout', { method: 'POST' });
    } finally {
      window.location.href = '/login';
    }
  };
  return (
    <header className="ax-header">
      <div className="ax-header__site">
        <strong>ATLAS</strong>
        <span>{SITE}</span>
      </div>
      <button type="button" className="ax-btn ax-header__search" onClick={onSearch} aria-keyshortcuts="Control+K">
        <Search aria-hidden />
        <span>Go to</span>
        <kbd>Ctrl K</kbd>
      </button>
      <span className="ax-header__spacer" />
      <LinkStatus link={link} />
      <div className="ax-header__clock">
        <time className="num" dateTime={now.toISOString()}>
          {formatTime(now, 'time', tz)}
        </time>
        <span>{zoneLabel(tz, now)}</span>
      </div>
      <Button variant="ghost" iconOnly label={theme === 'dark' ? 'Light theme' : 'Dark theme'} icon={theme === 'dark' ? <Sun aria-hidden /> : <Moon aria-hidden />} onClick={toggleTheme} />
      <div className="ax-header__user">
        <span>{user.username}</span>
        <StatusPill tone="quiet">{user.role}</StatusPill>
      </div>
      <Button variant="ghost" iconOnly label="Sign out" icon={<LogOut aria-hidden />} onClick={logout} />
    </header>
  );
}

/* ---------- Side navigation ---------- */

export function SideNav({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  const user = useSession();
  const items = navFor(user.role);
  const groups = [...new Set(items.map(i => i.group))];
  return (
    <aside className="ax-rail" aria-label="Main">
      <NavLink to="/fleet" className="ax-rail__brand">
        <BrandMark />
        <span>ATLAS</span>
      </NavLink>
      <nav>
        {groups.map(g => (
          <div key={g} role="group" aria-label={g}>
            <div className="ax-rail__group">{g}</div>
            {items
              .filter((i: NavItem) => i.group === g)
              .map(i => (
                <NavLink key={i.path} to={i.path} className="ax-rail__link" title={collapsed ? i.label : undefined}>
                  <i.icon aria-hidden />
                  <span className="ax-rail__label">{i.label}</span>
                </NavLink>
              ))}
          </div>
        ))}
      </nav>
      <div className="ax-rail__foot">
        <Button
          variant="ghost"
          size="sm"
          icon={collapsed ? <PanelLeftOpen aria-hidden /> : <PanelLeftClose aria-hidden />}
          onClick={onToggle}
          aria-expanded={!collapsed}
          aria-label={collapsed ? 'Expand navigation' : 'Collapse navigation'}
        >
          <span className="ax-rail__label">Collapse</span>
        </Button>
      </div>
    </aside>
  );
}

/* ---------- AppShell ---------- */

function readCollapsed(): boolean {
  try {
    return localStorage.getItem('atlas-rail') === 'collapsed';
  } catch {
    return false;
  }
}

/** Alarms that need acknowledging, shown on every page; quiet when there are none. */
function LiveAlarmBanner() {
  const { alarms } = useAlarms(15_000);
  const navigate = useNavigate();
  const now = useNow(30_000);
  return alarms ? <AlarmBanner alarms={alarms} now={now.getTime()} onOpen={() => navigate('/alarms')} /> : null;
}

/** Rail + header + banner slot + routed page. In kiosk mode only the page and a caption bar remain. */
export function AppShell({ banner }: { banner?: ReactNode }) {
  const user = useSession();
  const kiosk = useKiosk();
  const online = useOnline();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(readCollapsed);
  const [palette, setPalette] = useState(false);

  const toggle = useCallback(() => {
    setCollapsed(c => {
      try {
        localStorage.setItem('atlas-rail', c ? 'open' : 'collapsed');
      } catch {
        // preference only
      }
      return !c;
    });
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setPalette(true);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  // Move focus to the page heading on navigation so screen readers announce the new page.
  useEffect(() => {
    document.querySelector<HTMLElement>('#main h1')?.focus({ preventScroll: true });
  }, [location.pathname]);

  // Interaction audit (D4): page views here, every button and link press in startClientEvents.
  useEffect(() => {
    if (user.username === 'gallery') return; // dev gallery has no server session
    startClientEvents();
    track('page_view', location.pathname);
  }, [location.pathname, user.username]);

  return (
    <div className="ax-shell" data-collapsed={collapsed ? '' : undefined} data-kiosk={kiosk.active ? '' : undefined}>
      {!kiosk.active && (
        <>
          <a className="skip-link" href="#main">
            Skip to content
          </a>
          <SideNav collapsed={collapsed} onToggle={toggle} />
          <Header onSearch={() => setPalette(true)} />
        </>
      )}
      {kiosk.active ? (
        <KioskBar />
      ) : (
        <div className="ax-banner-slot">
          {!online && <OfflineNotice />}
          {banner ?? (user.username === 'gallery' ? null : <LiveAlarmBanner />)}
        </div>
      )}
      <main id="main" className="ax-main">
        <Suspense fallback={<SkeletonRows rows={8} />}>
          <Outlet />
        </Suspense>
      </main>
      {!kiosk.active && <CommandPalette role={user.role} open={palette} onClose={() => setPalette(false)} />}
    </div>
  );
}

/** Page frame: heading (focus target on navigation), one-line purpose, actions. */
export function Page({ title, purpose, actions, children }: { title: string; purpose?: string; actions?: ReactNode; children: ReactNode }) {
  return (
    <div className="ax-page">
      <div className="ax-page__head">
        <div>
          <h1 tabIndex={-1}>{title}</h1>
          {purpose && <p>{purpose}</p>}
        </div>
        {actions && <div style={{ display: 'flex', gap: 'var(--space-2)' }}>{actions}</div>}
      </div>
      {children}
    </div>
  );
}
