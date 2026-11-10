import { useCallback, useEffect, useState } from 'react';

import { apiFetch } from './api';

export interface Poll<T> {
  data: T | null;
  error: unknown;
  /** When the last successful reply arrived (ms). */
  updatedAt: number | null;
  /** The last reply is older than three polling intervals: show it, marked stale. */
  stale: boolean;
  reload: () => void;
}

/** GET `path` now and every `intervalMs` (0 = once). Keeps the last good reply when a poll fails. */
export function usePoll<T>(path: string | null, intervalMs = 5000): Poll<T> {
  const [state, setState] = useState<{ data: T | null; error: unknown; updatedAt: number | null }>({ data: null, error: null, updatedAt: null });
  const [tick, setTick] = useState(0);
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (!path) return;
    let alive = true;
    let timer = 0;
    const ctrl = new AbortController();
    const load = async () => {
      try {
        const data = await apiFetch<T>(path, { signal: ctrl.signal });
        if (alive) setState({ data, error: null, updatedAt: Date.now() });
      } catch (e) {
        if (alive && !ctrl.signal.aborted) setState(s => ({ ...s, error: e }));
      }
      if (alive) {
        setNow(Date.now());
        if (intervalMs > 0) timer = window.setTimeout(load, intervalMs);
      }
    };
    load();
    return () => {
      alive = false;
      ctrl.abort();
      clearTimeout(timer);
    };
  }, [path, intervalMs, tick]);

  const reload = useCallback(() => setTick(t => t + 1), []);
  const stale = intervalMs > 0 && state.updatedAt !== null && now - state.updatedAt > 3 * intervalMs;
  return { ...state, stale, reload };
}
