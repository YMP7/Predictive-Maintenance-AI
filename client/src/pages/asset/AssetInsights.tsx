// Below the 3D view on the Asset page: live trends from this session, the RUL band, and the
// Decision Graph's recommended action with a link to raise a work order for it.
import { useState } from 'react';
import { Link } from 'react-router';

import { TrendChart, type TrendPoint } from '../../design/TrendChart';
import { formatPercent, formatValue } from '../../design/format';
import { Button, StatusPill } from '../../design/primitives';
import { EmptyState } from '../../design/states';
import { useSession } from '../../contexts/SessionContext';
import { apiFetch, errorMessage, statusOf } from '../../lib/api';
import { workOrderHref, type Urgency } from '../../lib/ops';
import type { FrameChannel, TwinFrame } from './types';

const MAX_POINTS = 300;

interface History {
  last: string | null;
  rul: TrendPoint[];
  channels: Record<string, TrendPoint[]>;
}

/** Engineering value when the adapter reports one, otherwise the normalised value as % of range. */
const reading = (c: FrameChannel) => (c.raw !== null && c.unit ? { v: c.raw, unit: c.unit } : { v: c.value === null ? null : c.value * 100, unit: '% of range' });

interface Decision {
  recommended_action: string;
  ranked_actions: { action: string; expected_cost: number; p_failure_before_action: number }[];
  confidence: number;
  risk: number;
  impact: number;
  urgency: number;
}

const ACTION: Record<string, { text: string; urgency: Urgency | null }> = {
  CONTINUE_OPERATION: { text: 'Continue operation', urgency: null },
  SCHEDULE_MAINTENANCE_SOON: { text: 'Schedule maintenance soon', urgency: 'Medium' },
  SCHEDULE_MAINTENANCE_NOW: { text: 'Schedule maintenance now', urgency: 'High' },
  REPLACE_IMMEDIATELY: { text: 'Replace immediately', urgency: 'Critical' },
};
const actionText = (a: string) => ACTION[a]?.text ?? a.toLowerCase().replace(/_/g, ' ');

export function AssetInsights({ frame, focus }: { frame: TwinFrame; focus: FrameChannel[] }) {
  // History accumulates from the frames this page has polled (derived during render, keyed on the frame time).
  const [hist, setHist] = useState<History>({ last: null, rul: [], channels: {} });
  if (frame.ts && frame.ts !== hist.last) {
    const t = new Date(frame.ts).getTime();
    const push = (xs: TrendPoint[], p: TrendPoint) => [...xs, p].slice(-MAX_POINTS);
    const channels = { ...hist.channels };
    for (const c of frame.channels) channels[c.feature] = push(channels[c.feature] ?? [], { t, v: reading(c).v });
    const r = frame.rul;
    setHist({
      last: frame.ts,
      rul: r ? push(hist.rul, r.lower != null && r.upper != null
        ? { t, v: r.value, lo: r.lower, hi: r.upper }
        : { t, v: r.value, lo: r.uncertainty !== null ? r.value - r.uncertainty : null, hi: r.uncertainty !== null ? r.value + r.uncertainty : null }) : hist.rul,
      channels,
    });
  }

  const shown = (focus.length ? focus : [...frame.channels].sort((a, b) => (b.load ?? -1) - (a.load ?? -1))).slice(0, 2);
  return (
    <div className="ax-grid">
      <section className="ax-panel" aria-labelledby="ai-rul">
        <div className="ax-panel__head">
          <h2 id="ai-rul">Remaining useful life</h2>
          <span className="ax-note">Since this page opened</span>
        </div>
        <div className="ax-panel__body">
          {frame.rul ? (
            hist.rul.length > 1 ? (
              <TrendChart data={hist.rul} unit={frame.rul.unit} digits={0} height={180} seriesLabel="RUL" bandLabel={frame.rul.lower != null && frame.rul.interval_level != null ? `${Math.round(frame.rul.interval_level * 100)}% conformal interval` : '± 1 sd'} summary={`RUL over ${hist.rul.length} readings, latest ${frame.rul.value.toFixed(0)} ${frame.rul.unit}`} />
            ) : (
              <p className="ax-note">Collecting readings for the trend.</p>
            )
          ) : (
            <p className="ax-row">
              {frame.rul_note ?? 'No RUL model for this machine.'}
            </p>
          )}
        </div>
      </section>
      <section className="ax-panel" aria-labelledby="ai-trend">
        <div className="ax-panel__head">
          <h2 id="ai-trend">Live trends</h2>
          <span className="ax-note">{focus.length ? 'Selected part' : 'Highest-load channels'}</span>
        </div>
        <div className="ax-panel__body ax-stack">
          {shown.length === 0 ? (
            <p className="ax-note">No channels.</p>
          ) : (
            shown.map(c => {
              const data = hist.channels[c.feature] ?? [];
              const unit = reading(c).unit;
              return data.length > 1 ? (
                <div key={c.feature}>
                  <p className="ax-note">{c.label}</p>
                  <TrendChart data={data} unit={unit} digits={unit === '% of range' ? 0 : 2} height={120} seriesLabel={c.label} summary={`${c.label} over ${data.length} readings`} />
                </div>
              ) : (
                <p key={c.feature} className="ax-note">
                  {c.label}: collecting readings.
                </p>
              );
            })
          )}
        </div>
      </section>
      <Recommendation frame={frame} />
    </div>
  );
}

function Recommendation({ frame }: { frame: TwinFrame }) {
  const user = useSession();
  const [state, setState] = useState<{ busy: boolean; decision: Decision | null; error: string | null }>({ busy: false, decision: null, error: null });
  const canAct = user.role === 'admin' || user.role === 'operator';

  const run = async () => {
    setState({ busy: true, decision: null, error: null });
    try {
      const w = await apiFetch<{ window: number[][]; cycle: number }>(`/api/atlas/domain/${frame.domain}/machine/${encodeURIComponent(frame.machine_id)}/window`);
      const decision = await apiFetch<Decision>('/api/decide', { method: 'POST', body: JSON.stringify({ domain: frame.domain, machine_id: frame.machine_id, cycle: w.cycle, window: w.window, k: 10 }) });
      setState({ busy: false, decision, error: null });
    } catch (e) {
      const s = statusOf(e);
      setState({ busy: false, decision: null, error: s === 409 ? 'The model is still collecting its first 30 readings.' : s === 404 ? (frame.rul_note ?? 'No model makes decisions for this machine yet.') : errorMessage(e) });
    }
  };

  const d = state.decision;
  const rec = d ? ACTION[d.recommended_action] : null;
  return (
    <section className="ax-panel" aria-labelledby="ai-rec">
      <div className="ax-panel__head">
        <h2 id="ai-rec">Recommended action</h2>
        <Button size="sm" disabled={state.busy || !frame.rul} onClick={run}>
          {state.busy ? 'Deciding' : d ? 'Decide again' : 'Get recommendation'}
        </Button>
      </div>
      <div className="ax-panel__body ax-stack">
        {!frame.rul && (
          <p className="ax-row">
            Decisions need a RUL prediction for this machine. {frame.rul_note}
          </p>
        )}
        {state.error && <p className="ax-error">{state.error}</p>}
        {!d && !state.error && frame.rul && <EmptyState title="No recommendation yet" body="Runs the Decision Graph on this machine's last 30 readings: Monte Carlo outcomes per action, ranked by expected cost." />}
        {d && (
          <>
            <p>
              <strong>{actionText(d.recommended_action)}</strong>
            </p>
            <dl className="ax-dl">
              <dt>Confidence</dt>
              <dd className="num">{formatPercent(d.confidence, 1)}</dd>
              <dt>Risk</dt>
              <dd className="num">{formatPercent(d.risk, 1)}</dd>
              <dt>Urgency</dt>
              <dd className="num">{formatPercent(d.urgency)}</dd>
              <dt>Impact</dt>
              <dd className="num">{formatValue(d.impact, 'cost units', 1)}</dd>
            </dl>
            <ol className="ax-list">
              {d.ranked_actions.map(a => (
                <li key={a.action}>
                  {actionText(a.action)}
                  <span className="num">
                    cost {a.expected_cost.toFixed(1)} · P(fail first) {formatPercent(a.p_failure_before_action)}
                  </span>
                </li>
              ))}
            </ol>
            {canAct &&
              (rec?.urgency ? (
                <Link to={workOrderHref(frame.machine_id, frame.domain, undefined, { action: rec.text, urgency: rec.urgency })}>Create a work order for this action</Link>
              ) : (
                <p className="ax-row">
                  <StatusPill tone="quiet">No work order needed</StatusPill>
                  <Link to={workOrderHref(frame.machine_id, frame.domain)}>Create one anyway</Link>
                </p>
              ))}
          </>
        )}
      </div>
    </section>
  );
}
