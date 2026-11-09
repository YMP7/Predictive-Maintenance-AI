import { useEffect, useRef, useState } from 'react';

import { API_BASE_URL } from './api';

/** A reading pushed by GET /api/stream/machines/{id} (server/ingest.py). */
export interface StreamReading {
  kind: 'reading';
  machine_id: string;
  ts: string;
  source: string;
  health_index: number | null;
  quality: Record<string, string>;
  channels: Record<string, { value: number; unit: string; quality: string }>;
}

const RETRY_MS = 3000;

/** Split an SSE byte stream into events; returns the unparsed tail. */
function parse(buffer: string, onEvent: (type: string, data: string) => void): string {
  const blocks = buffer.split(/\r?\n\r?\n/);
  const tail = blocks.pop() ?? '';
  for (const block of blocks) {
    let type = 'message';
    const data: string[] = [];
    for (const line of block.split(/\r?\n/)) {
      if (line.startsWith('event:')) type = line.slice(6).trim();
      else if (line.startsWith('data:')) data.push(line.slice(5).trimStart());
    }
    if (data.length) onEvent(type, data.join('\n'));
  }
  return tail;
}

/**
 * Subscribe to a machine's live readings over SSE, reconnecting after 3 s.
 * Read with fetch, not EventSource: the API's CSRF check needs the X-API-Request header,
 * which EventSource cannot send.
 */
export function useStream(machineId: string | null, onReading: (r: StreamReading) => void): boolean {
  const [open, setOpen] = useState(false);
  const cb = useRef(onReading);
  useEffect(() => {
    cb.current = onReading;
  });
  useEffect(() => {
    if (!machineId) return;
    const ctrl = new AbortController();
    let timer = 0;
    const connect = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/api/stream/machines/${encodeURIComponent(machineId)}`, {
          credentials: 'include',
          headers: { 'X-API-Request': 'true', Accept: 'text/event-stream' },
          signal: ctrl.signal,
        });
        if (!res.ok || !res.body) throw new Error(`stream ${res.status}`);
        setOpen(true);
        const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
        let buffer = '';
        for (;;) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer = parse(buffer + value, (type, data) => {
            if (type !== 'reading') return;
            try {
              cb.current(JSON.parse(data) as StreamReading);
            } catch {
              /* malformed event: skip it, the next one will do */
            }
          });
        }
      } catch {
        /* network error or abort: fall through to the retry */
      }
      setOpen(false);
      if (!ctrl.signal.aborted) timer = window.setTimeout(connect, RETRY_MS);
    };
    connect();
    return () => {
      ctrl.abort();
      clearTimeout(timer);
      setOpen(false);
    };
  }, [machineId]);
  return open;
}
