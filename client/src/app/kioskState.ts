import { useSyncExternalStore } from 'react';

/* Kiosk mode (?kiosk=1): full screen, no chrome, auto-touring, for the 1080p showcase screen.
   The flag lives in sessionStorage so in-app navigation keeps it; Esc leaves kiosk mode. */

const KEY = 'atlas-kiosk';
const listeners = new Set<() => void>();
const emit = () => listeners.forEach(l => l());

function read(): boolean {
  try {
    return sessionStorage.getItem(KEY) === '1';
  } catch {
    return false;
  }
}

export function setKiosk(on: boolean) {
  try {
    if (on) sessionStorage.setItem(KEY, '1');
    else sessionStorage.removeItem(KEY);
  } catch {
    // private mode: kiosk lasts for this page view only
  }
  document.documentElement.toggleAttribute('data-kiosk', on);
  emit();
}

/** Call once at startup: honours ?kiosk=1 / ?kiosk=0 from the URL. */
export function initKioskFromUrl() {
  const p = new URLSearchParams(window.location.search).get('kiosk');
  if (p === '1') setKiosk(true);
  else if (p === '0') setKiosk(false);
  else document.documentElement.toggleAttribute('data-kiosk', read());
}

export function useKiosk() {
  const active = useSyncExternalStore(
    cb => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    read,
    () => false,
  );
  return { active, exit: () => setKiosk(false) };
}

/** Pages the tour visits until P3 adds the five machines. */
export const TOUR: { path: string; caption: string }[] = [
  { path: '/fleet', caption: 'Fleet overview: every asset across five machine types, one pipeline' },
  { path: '/cross-domain', caption: 'Cross-domain view: normalised health and RUL across unlike machines' },
  { path: '/about/evidence', caption: 'Evidence: each title term linked to the feature and metric that proves it' },
];
export const TOUR_HOLD_MS = 20000;
export const TOUR_IDLE_RESUME_MS = 25000;
