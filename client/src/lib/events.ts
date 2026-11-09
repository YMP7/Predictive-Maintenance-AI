// Interaction events for the audit trail (D4): page views and every button pressed, batched to
// POST /api/audit/client-events. Recorded server-side, never shown. Field values are never sent:
// only a control's visible name.
import { API_BASE_URL } from './api';

interface ClientEvent {
  type: string;
  ts: string;
  path: string;
  name?: string;
  detail?: Record<string, string | number | boolean | null>;
}

const queue: ClientEvent[] = [];
const FLUSH_MS = 10_000;
const MAX_BATCH = 200;
let started = false;

export function track(type: string, name?: string, detail?: ClientEvent['detail']) {
  queue.push({ type, ts: new Date().toISOString(), path: location.pathname.slice(0, 256), name: name?.slice(0, 120), detail });
  if (queue.length >= MAX_BATCH) flush();
}

function flush() {
  if (!queue.length) return;
  const events = queue.splice(0, MAX_BATCH);
  // keepalive fetch instead of sendBeacon: the API's CSRF check needs the X-API-Request header,
  // which sendBeacon cannot set. Both survive the page closing.
  fetch(`${API_BASE_URL}/api/audit/client-events`, {
    method: 'POST',
    keepalive: true,
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', 'X-API-Request': 'true' },
    body: JSON.stringify({ events }),
  }).catch(() => {
    /* audit of UI clicks is best effort; never disturb the operator */
  });
}

function controlName(el: Element) {
  return (el.getAttribute('aria-label') || el.textContent || '').replace(/\s+/g, ' ').trim();
}

/** Start once, after sign-in. Records every button and link pressed anywhere in the app. */
export function startClientEvents() {
  if (started) return;
  started = true;
  document.addEventListener(
    'click',
    e => {
      const el = (e.target as Element | null)?.closest('button, a[href], [role="button"], [role="menuitem"], [role="option"]');
      if (!el) return;
      const pressed = el.getAttribute('aria-pressed');
      track(el.tagName === 'A' ? 'link' : 'command', controlName(el), pressed === null ? undefined : { pressed: pressed === 'false' });
    },
    true,
  );
  window.setInterval(flush, FLUSH_MS);
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') flush();
  });
}
