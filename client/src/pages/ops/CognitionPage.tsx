import { useEffect, useId, useState, type ReactNode } from 'react';
import { Link, useSearchParams } from 'react-router';
import { Play, RotateCcw } from 'lucide-react';

import { BarList, Bars, HeatStrip, Histogram, Scatter } from '../../design/charts';
import { formatPercent, formatValue } from '../../design/format';
import { Button, QualityBadge, SimBadge, StatusPill, Timestamp } from '../../design/primitives';
import { Page } from '../../design/shell';
import { EmptyState, ErrorState, SkeletonRows } from '../../design/states';
import { TrendChart } from '../../design/TrendChart';
import type { DataQuality } from '../../design/types';
import { apiFetch, errorMessage, statusOf } from '../../lib/api';
import { usePoll } from '../../lib/usePoll';
import type { FleetAsset } from './FleetPage';
import { Polled } from './common';
import { DOMAIN_LABEL } from './labels';

/* ---------- payloads (server/cognition_trace.py, server/cognition_admin.py) ---------- */

type Out = Record<string, unknown>;
interface Stage {
  stage: string;
  latency_ms: number;
  output: Out;
}
interface Trace {
  domain: string;
  machine_id: string;
  ts: string;
  replayed: boolean;
  total_latency_ms: number;
  stages: Stage[];
}
interface HistoryPoint {
  ts: string;
  rul_mean: number | null;
  rul_p10: number | null;
  rul_p90: number | null;
  ground_truth: number | null;
  total_latency_ms: number | null;
  recommended_action: string | null;
}
interface History {
  points: HistoryPoint[];
  projection: { points: number[][]; explained: number[] };
  stage_latency_ms: Record<string, number | null>;
  drift: {
    data: { feature: string; early_mean: number; late_mean: number; shift_sd: number }[];
    model: { n: number; mae_early: number | null; mae_recent: number | null };
    dna: { l2: number; cosine: number; baseline_ts: string; current_ts: string } | null;
  };
}
interface Health {
  domains: { domain: string; model_loaded: boolean; using_lstm: boolean; model: string | null; version: string | null; traces: number; machines: number; mean_latency_ms: number | null; last_trace: string | null }[];
}

const STAGE_TITLE: Record<string, string> = {
  adapter: 'Adapter',
  world_model: 'World Model',
  amkb: 'Memory (AMKB)',
  machine_dna: 'Machine DNA',
  adaptive_context: 'Adaptive Context',
  rul: 'RUL prediction',
  simulation: 'Simulation',
  decision: 'Decision Graph',
  explainability: 'Explainability',
  learning: 'Learning Engine',
};
const ACTION = (a: string) => a.charAt(0) + a.slice(1).toLowerCase().replace(/_/g, ' ');
const num = (v: unknown) => (typeof v === 'number' ? v : null);
const arr = <T,>(v: unknown) => (Array.isArray(v) ? (v as T[]) : []);
const obj = (v: unknown) => (v && typeof v === 'object' ? (v as Out) : {});

/* ---------- page ---------- */

export default function CognitionPage() {
  const [params, setParams] = useSearchParams();
  const domain = params.get('domain') ?? 'cmapss';
  const machine = params.get('machine') ?? '';
  const ts = params.get('ts');
  const assets = usePoll<{ assets: FleetAsset[] }>('/api/assets', 0);
  const machines = (assets.data?.assets ?? []).filter(a => a.domain === domain).map(a => a.machine_id);
  const active = machine || machines[0] || '';
  const [trace, setTrace] = useState<{ busy: boolean; data: Trace | null; error: unknown }>({ busy: false, data: null, error: null });
  const [run, setRun] = useState(0);
  const history = usePoll<History>(active ? `/api/admin/cognition/${encodeURIComponent(active)}/history?domain=${domain}&limit=200` : null, 0);
  const ids = { d: useId(), m: useId() };

  const set = (patch: Record<string, string | null>) => {
    const next = new URLSearchParams(params);
    for (const [k, v] of Object.entries(patch)) {
      if (v === null) next.delete(k);
      else next.set(k, v);
    }
    setParams(next);
  };

  // A live trace runs on load and when asked; a replay loads the stored trace at ?ts=.
  useEffect(() => {
    if (!active) return;
    let alive = true;
    const url = `/api/admin/cognition/${encodeURIComponent(active)}/trace?domain=${domain}${ts ? `&ts=${encodeURIComponent(ts)}` : ''}`;
    apiFetch<Trace>(url)
      .then(data => alive && setTrace({ busy: false, data, error: null }))
      .catch(error => alive && setTrace({ busy: false, data: null, error }));
    return () => {
      alive = false;
    };
  }, [active, domain, ts, run]);

  const reloadHistory = history.reload;
  const liveTs = trace.data && !trace.data.replayed ? trace.data.ts : null;
  useEffect(() => {
    if (liveTs) reloadHistory();
  }, [liveTs, reloadHistory]);

  const points = history.data?.points ?? [];
  const at = ts ? points.findIndex(p => p.ts === ts) : points.length - 1;
  const busy = trace.busy || (!!active && !trace.data && !trace.error);

  return (
    <Page
      title="Cognition"
      purpose="The pipeline thinking, stage by stage, for one machine: what it perceived, remembered, predicted, simulated, decided and why."
      actions={trace.data?.replayed ? <StatusPill tone="accent">Replay</StatusPill> : trace.data ? <StatusPill tone="quiet">Live trace</StatusPill> : undefined}
    >
      <section className="ax-panel ax-panel__body ax-stack" aria-label="Machine and time">
        <div className="ax-form__row">
          <label className="ax-field" htmlFor={ids.d}>
            <span className="ax-field__label">Domain</span>
            <select id={ids.d} className="ax-input" value={domain} onChange={e => setParams({ domain: e.target.value })}>
              {Object.entries(DOMAIN_LABEL).map(([d, l]) => (
                <option key={d} value={d}>
                  {l}
                </option>
              ))}
            </select>
          </label>
          <label className="ax-field" htmlFor={ids.m}>
            <span className="ax-field__label">Machine</span>
            <select id={ids.m} className="ax-input" value={active} onChange={e => set({ machine: e.target.value, ts: null })}>
              {machines.length === 0 && <option value="">No machines</option>}
              {machines.map(m => (
                <option key={m}>{m}</option>
              ))}
            </select>
          </label>
        </div>
        <div className="ax-scrub">
          <Button
            icon={<Play aria-hidden />}
            variant="primary"
            disabled={!active || busy}
            onClick={() => {
              setTrace(t => ({ ...t, busy: true, error: null }));
              if (ts) set({ ts: null });
              else setRun(r => r + 1);
            }}
          >
            {busy ? 'Tracing' : 'Run live trace'}
          </Button>
          {points.length > 1 ? (
            <input
              type="range"
              min={0}
              max={points.length - 1}
              value={at < 0 ? points.length - 1 : at}
              aria-label="Replay a stored trace"
              aria-valuetext={points[at < 0 ? points.length - 1 : at]?.ts}
              onChange={e => set({ ts: points[Number(e.target.value)].ts })}
            />
          ) : (
            <span className="ax-note">Every live trace is stored; with two or more you can scrub back through them.</span>
          )}
          <span className="ax-note num">{points.length} stored</span>
        </div>
        {trace.data && (
          <p className="ax-note ax-row">
            {trace.data.replayed ? 'Replaying the trace stored at' : 'Traced at'} <Timestamp value={trace.data.ts} showZone /> · total {formatValue(trace.data.total_latency_ms, 'ms', 1)}
            {trace.data.replayed && (
              <Button size="sm" variant="ghost" icon={<RotateCcw aria-hidden />} onClick={() => set({ ts: null })}>
                Back to live
              </Button>
            )}
          </p>
        )}
      </section>

      {trace.error ? <TraceError error={trace.error} /> : !trace.data ? <SkeletonRows rows={8} /> : <Stages trace={trace.data} history={history.data} />}

      <DriftAndHealth history={history.data} />
      <Research />
    </Page>
  );
}

function TraceError({ error }: { error: unknown }) {
  const s = statusOf(error);
  if (s === 409 || s === 404)
    return (
      <section className="ax-panel">
        <EmptyState title="No trace for this machine yet" body={errorMessage(error).replace(/^API error \d+: /, '')} />
      </section>
    );
  return <ErrorState error={error} />;
}

/* ---------- the ten stages ---------- */

function Panel({ n, stage, latency, children }: { n: number; stage: string; latency?: number; children: ReactNode }) {
  return (
    <section className="ax-panel ax-stage-panel" aria-labelledby={`st-${stage}`}>
      <div className="ax-panel__head">
        <h2 id={`st-${stage}`}>
          {n}. {STAGE_TITLE[stage] ?? stage}
          {latency !== undefined && <span className="num">{formatValue(latency, 'ms', latency < 10 ? 2 : 1)}</span>}
        </h2>
      </div>
      <div className="ax-panel__body ax-stack">{children}</div>
    </section>
  );
}

function Stages({ trace, history }: { trace: Trace; history: History | null }) {
  const by = Object.fromEntries(trace.stages.map(s => [s.stage, s]));
  const o = (s: string) => by[s]?.output ?? {};
  const lat = (s: string) => by[s]?.latency_ms;
  const adapter = o('adapter');
  const raw = obj(adapter.raw);
  const norm = obj(adapter.normalized);
  const quality = obj(adapter.quality);
  const wm = o('world_model');
  const sv = arr<number>(wm.state_vector);
  const dnaOut = o('machine_dna');
  const dna = arr<number>(dnaOut.dna);
  const ctx = o('adaptive_context');
  const rul = o('rul');
  const sim = o('simulation');
  const hist = obj(sim.histogram);
  const dec = o('decision');
  const ex = o('explainability');
  const attrs = arr<{ sensor_name: string; magnitude: number; signed_delta: number }>(ex.sensor_attributions);
  const learn = o('learning');
  const proj = history?.projection;
  const hp = history?.points ?? [];
  const truth = hp.filter(p => p.ground_truth !== null && p.rul_mean !== null);
  const rmse = truth.length ? Math.sqrt(truth.reduce((s, p) => s + (p.rul_mean! - p.ground_truth!) ** 2, 0) / truth.length) : null;

  return (
    <>
      <section className="ax-panel ax-panel__body" aria-label="Latency per stage">
        <BarList label="Latency per stage, this trace" unit="ms" rows={trace.stages.map(s => ({ label: STAGE_TITLE[s.stage] ?? s.stage, value: s.latency_ms }))} />
      </section>
      <div className="ax-stages">
        <Panel n={1} stage="adapter" latency={lat('adapter')}>
          <p className="ax-note ax-row">
            {String(adapter.adapter ?? 'Adapter')} {String(adapter.adapter_version ?? '')} · status {String(adapter.adapter_status ?? 'n/a')} · window {String(adapter.window_hash ?? '')}
            {adapter.adapter_status === 'simulation' && <SimBadge />}
          </p>
          <div className="ax-table-scroll" style={{ maxHeight: '16rem' }}>
            <table className="ax-table">
              <caption className="visually-hidden">Raw and normalised value per channel</caption>
              <thead>
                <tr>
                  <th scope="col">Channel</th>
                  <th scope="col">Raw</th>
                  <th scope="col">Normalised</th>
                  <th scope="col">Quality</th>
                </tr>
              </thead>
              <tbody>
                {Object.keys(norm).map(k => (
                  <tr key={k}>
                    <th scope="row">{k}</th>
                    <td className="num">{num(raw[k]) === null ? '--' : String(raw[k])}</td>
                    <td className="num">{num(norm[k])?.toFixed(3) ?? '--'}</td>
                    <td>{quality[k] ? <QualityBadge quality={quality[k] as DataQuality} /> : '--'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>

        <Panel n={2} stage="world_model" latency={lat('world_model')}>
          <p className="ax-note">
            {String(wm.model ?? 'model')} version {String(wm.version ?? 'n/a')} · raw RUL head {num(wm.rul_raw)?.toFixed(2) ?? 'n/a'}
          </p>
          {sv.length > 0 && <HeatStrip values={sv} label={`State vector, ${sv.length} dimensions`} />}
          {proj && proj.points.length > 1 ? (
            <Scatter
              points={proj.points}
              labels={hp.map(p => p.ts)}
              xLabel={`PC1 (${formatPercent(proj.explained[0])})`}
              yLabel={`PC2 (${formatPercent(proj.explained[1])})`}
              label={`Stored states projected to 2-D (PCA), ${proj.points.length} traces`}
            />
          ) : (
            <p className="ax-note">The 2-D trajectory appears once two traces are stored for this machine.</p>
          )}
        </Panel>

        <Panel n={3} stage="amkb" latency={lat('amkb')}>
          <p className="ax-note">Nearest past experiences to this state (k = {String(o('amkb').k ?? '')}). Distance is in the 32-dim state space; 0 is identical.</p>
          <table className="ax-table">
            <thead>
              <tr>
                <th scope="col">Machine</th>
                <th scope="col">Cycle</th>
                <th scope="col">Distance</th>
                <th scope="col">True RUL</th>
                <th scope="col">Outcome</th>
              </tr>
            </thead>
            <tbody>
              {arr<Out>(o('amkb').neighbors).map((n, i) => (
                <tr key={i}>
                  <th scope="row">{String(n.machine_id)}</th>
                  <td className="num">{String(n.cycle)}</td>
                  <td className="num">{num(n.distance)?.toExponential(2)}</td>
                  <td className="num">{num(n.true_rul)?.toFixed(0) ?? '--'}</td>
                  <td>{String(n.event_type ?? '')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>

        <Panel n={4} stage="machine_dna" latency={lat('machine_dna')}>
          {dna.length ? (
            <>
              <Bars values={dna} labels={dna.map((_, i) => `dim ${i}`)} label="Machine DNA, 16-dim fingerprint" />
              <p className="ax-note">
                Drift against this machine's first stored trace:{' '}
                {history?.drift.dna ? `L2 ${history.drift.dna.l2.toFixed(3)}, cosine distance ${history.drift.dna.cosine.toFixed(4)}` : 'needs two stored traces'}.
              </p>
              <p className="ax-note">Nearest siblings: {arr<Out>(dnaOut.siblings).map(s => `${s.machine_id} (${num(s.distance)?.toFixed(3)})`).join(', ') || 'none'}</p>
            </>
          ) : (
            <p className="ax-note">{String(dnaOut.reason ?? 'No stored Machine DNA for this unit.')}</p>
          )}
        </Panel>

        <Panel n={5} stage="adaptive_context" latency={lat('adaptive_context')}>
          <dl className="ax-dl">
            <dt>Predicted RUL</dt>
            <dd className="num">{num(ctx.predicted_rul)?.toFixed(1)}</dd>
            <dt>Neighbour average RUL</dt>
            <dd className="num">{num(ctx.average_neighbor_rul)?.toFixed(1)}</dd>
            <dt>Neighbours used</dt>
            <dd className="num">{String(ctx.neighbor_count)}</dd>
            {Object.entries(obj(ctx.operational_context)).map(([k, v]) => (
              <div key={k} style={{ display: 'contents' }}>
                <dt>{k}</dt>
                <dd className="num">
                  {String(v)} {arr<string>(ctx.synthetic_fields).includes(k) && <SimBadge kind="SYNTHETIC" />}
                </dd>
              </div>
            ))}
          </dl>
          {arr<string>(ctx.synthetic_fields).length > 0 && <p className="ax-note">Fields marked SYNTHETIC are generated, not measured.</p>}
        </Panel>

        <Panel n={6} stage="rul" latency={lat('rul')}>
          <p>
            <strong className="num">{num(rul.mean)?.toFixed(1)}</strong>{' '}
            <span className="ax-note">
              mean, p10 {num(rul.p10)?.toFixed(1)} to p90 {num(rul.p90)?.toFixed(1)}
            </span>
            {num(rul.ground_truth) !== null && (
              <span className="ax-note">
                {' '}
                · ground truth {num(rul.ground_truth_capped ?? rul.ground_truth)?.toFixed(0)}
                {num(rul.truth_cap) !== null && num(rul.ground_truth)! > num(rul.truth_cap)! && ` (label ${num(rul.ground_truth)?.toFixed(0)}, capped at ${num(rul.truth_cap)} like the training target)`}
                , error {num(rul.error)?.toFixed(1)}
              </span>
            )}
          </p>
          {hp.length > 1 ? (
            <TrendChart
              data={hp.filter(p => p.rul_mean !== null).map(p => ({ t: new Date(p.ts).getTime(), v: p.rul_mean, lo: p.rul_p10, hi: p.rul_p90 }))}
              digits={1}
              height={180}
              seriesLabel="RUL mean"
              bandLabel="p10 to p90"
              summary={`RUL mean with p10 to p90 band over ${hp.length} stored traces`}
            />
          ) : (
            <p className="ax-note">The band over time appears once two traces are stored.</p>
          )}
          {rmse !== null && (
            <p className="ax-note">
              RMSE against ground truth (capped) over {truth.length} stored traces: {rmse.toFixed(2)}. These are training-set replays, not a benchmark; the FD001 test benchmark is on the Model registry page.
            </p>
          )}
        </Panel>

        <Panel n={7} stage="simulation" latency={lat('simulation')}>
          <p className="ax-note">
            Monte Carlo: N = {String(sim.n)}, seed {String(sim.seed)}, P(failure now) {formatPercent(num(sim.p_failure_now) ?? 0, 1)}
          </p>
          {arr<number>(hist.edges).length > 1 && <Histogram edges={arr<number>(hist.edges)} counts={arr<number>(hist.counts)} label="Simulated failure time (RUL draws)" unit="cycles" markAt={0} markLabel="failure" />}
          <table className="ax-table">
            <thead>
              <tr>
                <th scope="col">Action</th>
                <th scope="col">Expected cost</th>
                <th scope="col">Cost sd</th>
                <th scope="col">P(fail first)</th>
              </tr>
            </thead>
            <tbody>
              {arr<Out>(sim.results).map(r => (
                <tr key={String(r.action)}>
                  <th scope="row">{ACTION(String(r.action))}</th>
                  <td className="num">{num(r.expected_cost)?.toFixed(1)}</td>
                  <td className="num">{num(r.cost_std)?.toFixed(1)}</td>
                  <td className="num">{formatPercent(num(r.p_failure_before_action) ?? 0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>

        <Panel n={8} stage="decision" latency={lat('decision')}>
          <p>
            Recommended: <strong>{ACTION(String(dec.recommended_action ?? ''))}</strong>
          </p>
          <dl className="ax-dl">
            <dt>Confidence</dt>
            <dd className="num">{formatPercent(num(dec.confidence) ?? 0, 1)}</dd>
            <dt>Risk</dt>
            <dd className="num">{formatPercent(num(dec.risk) ?? 0, 1)}</dd>
            <dt>Impact</dt>
            <dd className="num">{num(dec.impact)?.toFixed(1)} cost units</dd>
            <dt>Urgency</dt>
            <dd className="num">{formatPercent(num(dec.urgency) ?? 0)}</dd>
          </dl>
          <ol className="ax-list">
            {arr<Out>(dec.ranked_actions).map(a => (
              <li key={String(a.action)}>
                {ACTION(String(a.action))}
                <span className="num">cost {num(a.expected_cost)?.toFixed(1)}</span>
              </li>
            ))}
          </ol>
        </Panel>

        <Panel n={9} stage="explainability" latency={lat('explainability')}>
          <p>{String(ex.primary_justification ?? '')}</p>
          <p className="ax-note">
            Confidence {String(ex.confidence_level ?? '')} ({formatPercent(num(ex.confidence_score) ?? 0, 1)})
          </p>
          {attrs.length > 0 ? (
            <Bars values={attrs.map(a => a.signed_delta)} labels={attrs.map(a => a.sensor_name)} label="Occlusion attribution: RUL change when each sensor is masked" unit="cycles" />
          ) : (
            <p className="ax-note">{String(ex.attribution_unavailable_reason ?? 'No per-sensor attribution for this domain.')}</p>
          )}
          <details>
            <summary className="ax-note">AMKB citations ({arr<string>(ex.citations).length})</summary>
            <ul className="ax-list">
              {arr<string>(ex.citations).map((c, i) => (
                <li key={i}>{c}</li>
              ))}
            </ul>
          </details>
        </Panel>

        <Panel n={10} stage="learning" latency={lat('learning')}>
          <p className="ax-note">{String(learn.note ?? '')}</p>
          {arr<Out>(learn.history).length === 0 ? (
            <p className="ax-note">No retraining runs recorded for this domain.</p>
          ) : (
            <ul className="ax-list">
              {arr<Out>(learn.history).map(h => (
                <li key={String(h.id)}>
                  <StatusPill tone={h.success ? 'quiet' : 'medium'}>{h.success ? 'Promoted' : 'Rejected'}</StatusPill>
                  <span className="num">
                    RMSE {num(h.rmse_before)?.toFixed(2)} to {num(h.rmse_after)?.toFixed(2)}
                  </span>
                  <span className="ax-note">{String(h.triggered_at).slice(0, 16)}</span>
                </li>
              ))}
            </ul>
          )}
          <Link to="/admin/models">Model registry: versions, promote and roll back</Link>
        </Panel>
      </div>
    </>
  );
}

/* ---------- drift, fleet health ---------- */

function DriftAndHealth({ history }: { history: History | null }) {
  const health = usePoll<Health>('/api/admin/cognition/health', 30_000);
  const d = history?.drift;
  return (
    <div className="ax-grid">
      <section className="ax-panel" aria-labelledby="cg-drift">
        <div className="ax-panel__head">
          <h2 id="cg-drift">Drift monitor</h2>
          <span className="ax-note">Over this machine's stored traces</span>
        </div>
        <div className="ax-panel__body ax-stack">
          {!d || (history?.points.length ?? 0) < 2 ? (
            <p className="ax-note">Drift needs stored traces for this machine; run a few live traces first.</p>
          ) : (
            <>
              <p className="ax-note">Data drift: mean shift per feature, first third of traces against the last third, in pooled standard deviations (floored at 1 % of range).</p>
              {d.data.length ? (
                <BarList label="Data drift by feature" unit="sd" rows={d.data.slice(0, 6).map(x => ({ label: x.feature, value: Math.abs(x.shift_sd) }))} />
              ) : (
                <p className="ax-note">Needs at least 9 stored traces (3 in each third); {history?.points.length} so far.</p>
              )}
              <p className="ax-note">
                Model drift:{' '}
                {d.model.n === 0
                  ? 'no ground truth for this machine, so prediction error cannot be measured.'
                  : `mean absolute RUL error ${d.model.mae_early?.toFixed(2)} in the earlier half, ${d.model.mae_recent?.toFixed(2)} in the recent half (${d.model.n} traces with ground truth).`}
              </p>
            </>
          )}
        </div>
      </section>
      <section className="ax-panel" aria-labelledby="cg-health">
        <div className="ax-panel__head">
          <h2 id="cg-health">Fleet cognition health</h2>
        </div>
        <Polled poll={health} rows={4}>
          {h => (
            <div className="ax-table-scroll ax-panel__body">
            <table className="ax-table">
              <thead>
                <tr>
                  <th scope="col">Domain</th>
                  <th scope="col">Model</th>
                  <th scope="col">Traces / machines</th>
                  <th scope="col">Mean latency</th>
                  <th scope="col">Last trace</th>
                </tr>
              </thead>
              <tbody>
                {h.domains.map(r => (
                  <tr key={r.domain}>
                    <th scope="row">{DOMAIN_LABEL[r.domain] ?? r.domain}</th>
                    <td>{r.model_loaded ? `${r.using_lstm ? 'LSTM' : 'EMA fallback'} ${r.version ?? ''}` : <StatusPill tone="medium">Not loaded</StatusPill>}</td>
                    <td className="num">
                      {r.traces} / {r.machines}
                    </td>
                    <td className="num">{r.mean_latency_ms === null ? '--' : formatValue(r.mean_latency_ms, 'ms', 0)}</td>
                    <td>{r.last_trace ? <Timestamp value={r.last_trace} style="time" /> : '--'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          )}
        </Polled>
      </section>
    </div>
  );
}

/* ---------- ablations and transfer study (recorded results) ---------- */

interface Ablations {
  ablation_1?: { total_cost_pipeline_a: number; total_cost_pipeline_b: number; cost_reduction_percent: number };
  ablation_2?: { grounded_confidence_mean: number; ungrounded_confidence_mean: number; grounded_spearman_rho: number | null };
  ablation_3?: { policy_agreement_rate: number; near_failure_urgent_rate_naive: number; near_failure_urgent_rate_atlas: number };
}
interface Transfer {
  retrieval_transfer_diagnostics?: Record<string, { within_rmse: number; cross_rmse: number; error_inflation_ratio: number }>;
}

function Research() {
  const ab = usePoll<Ablations>('/api/atlas/research/ablations', 0);
  const tr = usePoll<Transfer>('/api/atlas/research/transfer-study', 0);
  return (
    <div className="ax-grid">
      <section className="ax-panel" aria-labelledby="cg-ab">
        <div className="ax-panel__head">
          <h2 id="cg-ab">Ablations (recorded run)</h2>
        </div>
        <Polled poll={ab} rows={3} title="No ablation results recorded">
          {a => (
            <dl className="ax-dl ax-panel__body">
              {a.ablation_1 && (
                <>
                  <dt>Decision Graph vs threshold policy</dt>
                  <dd>
                    total cost {a.ablation_1.total_cost_pipeline_a} to {a.ablation_1.total_cost_pipeline_b} ({a.ablation_1.cost_reduction_percent}% lower)
                  </dd>
                </>
              )}
              {a.ablation_2 && (
                <>
                  <dt>AMKB grounding</dt>
                  <dd>
                    confidence mean {a.ablation_2.grounded_confidence_mean} grounded vs {a.ablation_2.ungrounded_confidence_mean} ungrounded; Spearman rho {a.ablation_2.grounded_spearman_rho ?? 'n/a'}
                  </dd>
                </>
              )}
              {a.ablation_3 && (
                <>
                  <dt>Monte Carlo vs naive policy</dt>
                  <dd>
                    agreement {a.ablation_3.policy_agreement_rate}%; urgent near failure {a.ablation_3.near_failure_urgent_rate_atlas}% vs {a.ablation_3.near_failure_urgent_rate_naive}%
                  </dd>
                </>
              )}
            </dl>
          )}
        </Polled>
      </section>
      <section className="ax-panel" aria-labelledby="cg-tr">
        <div className="ax-panel__head">
          <h2 id="cg-tr">Transfer study (recorded run)</h2>
        </div>
        <Polled poll={tr} rows={3} title="No transfer study recorded">
          {t => (
            <div className="ax-table-scroll ax-panel__body">
            <table className="ax-table">
              <thead>
                <tr>
                  <th scope="col">Domain</th>
                  <th scope="col">Within-domain RMSE</th>
                  <th scope="col">C-MAPSS memory RMSE</th>
                  <th scope="col">Error ratio</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(t.retrieval_transfer_diagnostics ?? {}).map(([d, r]) => (
                  <tr key={d}>
                    <th scope="row">{DOMAIN_LABEL[d] ?? d}</th>
                    <td className="num">{r.within_rmse}</td>
                    <td className="num">{r.cross_rmse}</td>
                    <td className="num">{r.error_inflation_ratio}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          )}
        </Polled>
      </section>
    </div>
  );
}
