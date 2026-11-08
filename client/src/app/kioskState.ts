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

/** Pages the tour visits: the five machine types in 3D (each page tours its parts on its own), then the overviews. */
export const TOUR: { path: string; caption: string }[] = [
  { path: '/assets/kind/turbofan', caption: 'Turbofan engine, NASA C-MAPSS: the benchmark the RUL model is scored on' },
  { path: '/assets/kind/laptop', caption: 'A laptop: this computer, read live from its operating system' },
  { path: '/assets/kind/phone', caption: 'An Android phone: battery, processor and motion sensors' },
  { path: '/assets/kind/server', caption: 'A rack server: processors, memory, disks and network' },
  { path: '/assets/kind/motor_pump', caption: 'A motor-driven pump over Modbus TCP' },
  { path: '/fleet', caption: 'Fleet overview: every asset across five machine types, one pipeline' },
  { path: '/about/evidence', caption: 'Evidence: each title term linked to the feature and metric that proves it' },
];
export const TOUR_HOLD_MS = 20000;
export const TOUR_IDLE_RESUME_MS = 25000;
