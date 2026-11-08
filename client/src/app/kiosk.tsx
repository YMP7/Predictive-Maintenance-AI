import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router';

import { formatTime, getTimeZone, zoneLabel } from '../design/format';
import { useNow, useReducedMotion } from '../design/hooks';
import { TOUR, TOUR_HOLD_MS, TOUR_IDLE_RESUME_MS, useKiosk } from './kioskState';

/** Bottom caption bar in kiosk mode: title, current stop, clock. Drives the auto tour. */
export function KioskBar() {
  const navigate = useNavigate();
  const location = useLocation();
  const { exit } = useKiosk();
  const now = useNow(1000);
  const reduced = useReducedMotion();
  const [stopStart, setStopStart] = useState(() => Date.now());
  const [pausedUntil, setPausedUntil] = useState(0);
  const tz = getTimeZone();

  const stop = Math.max(0, TOUR.findIndex(t => location.pathname.startsWith(t.path)));
  const paused = now.getTime() < pausedUntil;
  const progress = paused ? 0 : Math.min(1, Math.max(0, (now.getTime() - stopStart) / TOUR_HOLD_MS));

  // Advance from a timer callback; the next stop is computed from the route at that moment.
  useEffect(() => {
    const id = window.setInterval(() => {
      const t = Date.now();
      if (t < pausedUntil || t - stopStart < TOUR_HOLD_MS) return;
      const idx = Math.max(0, TOUR.findIndex(s => window.location.pathname.startsWith(s.path)));
      setStopStart(t);
      navigate(TOUR[(idx + 1) % TOUR.length].path);
    }, 500);
    return () => window.clearInterval(id);
  }, [pausedUntil, stopStart, navigate]);

  // Any input hands control to the visitor; 25 s of quiet hands it back. First input requests full screen.
  useEffect(() => {
    const onInput = (e: Event) => {
      if (e instanceof KeyboardEvent && e.key === 'Escape') {
        if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
        exit();
        return;
      }
      if (!document.fullscreenElement) document.documentElement.requestFullscreen?.().catch(() => {});
      const resume = Date.now() + TOUR_IDLE_RESUME_MS;
      setPausedUntil(resume);
      setStopStart(resume);
    };
    const events = ['pointerdown', 'keydown', 'wheel'] as const;
    events.forEach(ev => window.addEventListener(ev, onInput, { passive: true }));
    return () => events.forEach(ev => window.removeEventListener(ev, onInput));
  }, [exit]);

  return (
    <div className="ax-kiosk-bar" role="contentinfo">
      <strong>ATLAS</strong>
      <span className="ax-kiosk-bar__caption" aria-live="polite">
        {paused ? 'Visitor in control. The tour resumes after 25 s without input.' : TOUR[stop].caption}
      </span>
      {!reduced && (
        <span className="ax-kiosk-bar__progress" aria-hidden>
          <i style={{ transform: `scaleX(${progress})` }} />
        </span>
      )}
      <time className="num" dateTime={now.toISOString()}>
        {formatTime(now, 'time', tz)} {zoneLabel(tz, now)}
      </time>
    </div>
  );
}
