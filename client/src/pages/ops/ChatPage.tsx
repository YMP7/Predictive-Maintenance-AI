import { useEffect, useId, useRef, useState } from 'react';
import { useSearchParams } from 'react-router';
import { Send } from 'lucide-react';

import { Button, EvidenceLabel, Timestamp } from '../../design/primitives';
import { Page } from '../../design/shell';
import { EmptyState } from '../../design/states';
import { apiFetch, errorMessage, statusOf } from '../../lib/api';
import { usePoll } from '../../lib/usePoll';
import type { FleetAsset } from './FleetPage';
import { DOMAIN_LABEL } from './labels';

interface AgentReply {
  response: string;
  tools_called: (string | { name?: string; tool?: string })[];
  work_orders_created: unknown[];
  llm_enabled: boolean;
}

interface Grounding {
  justification: string;
  citations: string[];
}

interface Message {
  from: 'user' | 'agent';
  text: string;
  at: string;
  tools?: string[];
  orders?: number;
  grounding?: Grounding | null;
  groundingNote?: string;
}

/** AMKB evidence for a machine: the explanation engine's nearest past experiences for its current window. */
async function amkbGrounding(a: FleetAsset): Promise<Grounding> {
  const w = await apiFetch<{ window: number[][]; cycle: number }>(`/api/atlas/domain/${a.domain}/machine/${encodeURIComponent(a.machine_id)}/window`);
  const r = await apiFetch<{ primary_justification: string; citations: string[] }>('/api/explain', {
    method: 'POST',
    body: JSON.stringify({ domain: a.domain, machine_id: a.machine_id, cycle: w.cycle, window: w.window, k: 5 }),
  });
  return { justification: r.primary_justification, citations: r.citations ?? [] };
}

export default function ChatPage() {
  const [params, setParams] = useSearchParams();
  const assets = usePoll<{ assets: FleetAsset[] }>('/api/assets', 0);
  const machineKey = params.get('machine') ?? '';
  const asset = assets.data?.assets.find(a => `${a.domain}/${a.machine_id}` === machineKey) ?? null;
  const [messages, setMessages] = useState<Message[]>([]);
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const log = useRef<HTMLDivElement>(null);
  const ids = { m: useId(), q: useId() };

  useEffect(() => {
    log.current?.scrollTo({ top: log.current.scrollHeight });
  }, [messages]);

  const ask = async () => {
    const q = text.trim();
    if (!q) return;
    setText('');
    setBusy(true);
    setError(null);
    setMessages(m => [...m, { from: 'user', text: q, at: new Date().toISOString() }]);
    try {
      const [reply, grounding] = await Promise.all([
        apiFetch<AgentReply>('/api/agent/chat', { method: 'POST', body: JSON.stringify({ message: q, machine_id: asset?.machine_id ?? null }) }),
        asset
          ? amkbGrounding(asset).then(
              g => ({ g, note: '' }),
              e => ({ g: null, note: statusOf(e) === 409 ? 'The model is still collecting its first 30 readings.' : 'No AMKB evidence for this machine.' }),
            )
          : Promise.resolve(null),
      ]);
      setMessages(m => [
        ...m,
        {
          from: 'agent',
          text: reply.response,
          at: new Date().toISOString(),
          tools: reply.tools_called.map(t => (typeof t === 'string' ? t : (t.name ?? t.tool ?? 'tool'))),
          orders: reply.work_orders_created.length,
          grounding: grounding?.g ?? null,
          groundingNote: grounding?.note,
        },
      ]);
    } catch (e) {
      setError(statusOf(e) === 429 ? 'The agent accepts 10 questions a minute. Wait a moment and ask again.' : errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Page title="Agent chat" purpose="Ask the maintenance agent about a machine. AMKB evidence for the selected machine is shown with each answer.">
      <div className="ax-row">
        <label className="ax-field" htmlFor={ids.m}>
          <span className="ax-field__label">Machine</span>
          <select id={ids.m} className="ax-input" value={machineKey} onChange={e => setParams(e.target.value ? { machine: e.target.value } : {})}>
            <option value="">No specific machine</option>
            {(assets.data?.assets ?? []).map(a => (
              <option key={`${a.domain}/${a.machine_id}`} value={`${a.domain}/${a.machine_id}`}>
                {a.machine_id} ({DOMAIN_LABEL[a.domain] ?? a.domain})
              </option>
            ))}
          </select>
        </label>
      </div>
      <section className="ax-panel" aria-label="Conversation">
        <div className="ax-chat" ref={log} aria-live="polite">
          {messages.length === 0 ? (
            <EmptyState title="No questions yet" body="For example: why is this machine degrading, and what should we inspect first?" />
          ) : (
            messages.map((m, i) => (
              <div key={i} className="ax-chat__msg" data-from={m.from}>
                {m.text}
                <div className="ax-chat__meta">
                  <Timestamp value={m.at} style="time" />
                  {m.tools && m.tools.length > 0 && ` · tools used: ${m.tools.join(', ')}`}
                  {m.orders ? ` · ${m.orders} work order(s) created, pending approval` : ''}
                </div>
                {m.from === 'agent' && (m.grounding || m.groundingNote) && (
                  <div className="ax-chat__meta">
                    {m.grounding ? (
                      <>
                        <strong>AMKB evidence:</strong> {m.grounding.justification}{' '}
                        {m.grounding.citations.length > 0 && `Similar past cases: ${m.grounding.citations.slice(0, 5).join('; ')}.`}
                      </>
                    ) : (
                      m.groundingNote
                    )}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
        <form
          className="ax-panel__body ax-row"
          onSubmit={e => {
            e.preventDefault();
            ask();
          }}
        >
          <label htmlFor={ids.q} className="visually-hidden">
            Question
          </label>
          <input id={ids.q} className="ax-input" style={{ flex: 1 }} value={text} onChange={e => setText(e.target.value)} placeholder="Ask about a machine" maxLength={2000} />
          <Button type="submit" variant="primary" icon={<Send aria-hidden />} disabled={busy || !text.trim()}>
            {busy ? 'Thinking' : 'Ask'}
          </Button>
        </form>
      </section>
      {error && (
        <p className="ax-error" role="alert">
          {error}
        </p>
      )}
      <p className="ax-note ax-row">
        <EvidenceLabel kind="FUTURE-WORK" /> The agent's own answer does not yet quote AMKB cases; the evidence line comes from the explanation engine for the same machine.
      </p>
    </Page>
  );
}
