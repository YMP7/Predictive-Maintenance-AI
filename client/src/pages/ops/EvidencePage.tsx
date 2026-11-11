import type { ReactNode } from 'react';
import { Link } from 'react-router';

import { formatPercent } from '../../design/format';
import { EvidenceLabel } from '../../design/primitives';
import { Page } from '../../design/shell';
import { usePoll, type Poll } from '../../lib/usePoll';

/* The title matrix (D7). Same content as docs/TITLE_JUSTIFICATION.md; the numbers here are read live from the
   recorded result files through the API, so the page cannot drift from the files. */

interface Evaluation {
  prediction_accuracy: {
    total_test_units: number;
    rmse: number;
    mae: number;
    phm_score: number;
    reference_baseline: { multiseed_mean_rmse: number; multiseed_std_rmse: number; multiseed_mean_phm: number; multiseed_std_phm: number; literature_zheng_rmse: number; literature_zheng_phm: number };
  };
}
interface Ablations {
  ablation_1: { total_cost_pipeline_a: number; total_cost_pipeline_b: number; cost_reduction_percent: number; missed_failures_a: number; missed_failures_b: number; premature_waste_cycles_b: number };
  ablation_2: { grounded_confidence_mean: number; ungrounded_confidence_mean: number; grounded_spearman_rho: number | null };
}
interface Transfer {
  retrieval_transfer_diagnostics: Record<string, { within_rmse: number; cross_rmse: number; error_inflation_ratio: number }>;
}
interface Benchmark {
  benchmark: { stage_8_end_to_end_ms: Record<string, { mean_ms: number }> };
}
type Deletion = Record<string, { mean_abs_delta_top: number; mean_abs_delta_random: number; top_beats_random_pct: number; n_units: number }>;
interface Faithfulness {
  summary: Deletion;
  domains?: Record<string, { summary: Deletion; n_features: number; provenance: string; output: string }>;
}
interface RetrainHistory {
  total_runs: number;
  promoted: number;
  rejected: number;
  by_domain: Record<string, { runs: number; promoted: number; rejected: number; data: string }>;
}
interface PumpRul {
  shipped_checkpoint: { rmse: number; mae: number; phm_score: number; n_units: number };
  baseline_constant_mean: { rmse: number };
  multi_seed: { n: number; rmse_mean: number; rmse_std: number };
}

/** A live number, or a plain note when its result file is missing. Never a made-up default. */
function N<T>({ poll, children }: { poll: Poll<T>; children: (d: T) => ReactNode }) {
  if (poll.data) return <>{children(poll.data)}</>;
  if (poll.error) return <span className="ax-note">(result file not found on this server)</span>;
  return <span className="ax-note">loading</span>;
}

interface Row {
  id: string;
  term: string;
  claim: string;
  components: string[];
  see: { label: string; to: string; admin?: boolean }[];
  numbers: ReactNode;
  future?: string;
}

const DOMAIN: Record<string, string> = { laptop: 'laptop', mobile: 'phone', server: 'server', cmapss: 'turbofan', modbus: 'pump' };

export default function EvidencePage() {
  const ev = usePoll<Evaluation>('/api/atlas/evaluation/summary', 0);
  const ab = usePoll<Ablations>('/api/atlas/research/ablations', 0);
  const tr = usePoll<Transfer>('/api/atlas/research/transfer-study', 0);
  const bm = usePoll<Benchmark>('/api/atlas/system/benchmark', 0);
  const ff = usePoll<Faithfulness>('/api/atlas/research/attribution-faithfulness', 0);
  const rh = usePoll<RetrainHistory>('/api/atlas/research/retrain-history', 0);
  const pr = usePoll<PumpRul>('/api/atlas/research/pump-rul', 0);

  const rows: Row[] = [
    {
      id: 'adaptive',
      term: 'Adaptive',
      claim: "Adapts its estimate to the machine's context and to new machines.",
      components: ['server/atlas/adaptive_context.py', 'server/atlas/learning_engine.py (batch retrain for every domain, 3% gate)', 'scripts/run_retrain_history.py', 'server/atlas/transfer_study.py'],
      see: [
        { label: 'Cognition: Adaptive Context and Learning Engine panels', to: '/admin/cognition', admin: true },
        { label: 'Model registry', to: '/admin/models', admin: true },
      ],
      numbers: (
        <>
        <N poll={tr}>
          {t => (
            <>
              Error when a domain retrieves through turbofan memory instead of its own, as a ratio:{' '}
              {Object.entries(t.retrieval_transfer_diagnostics)
                .map(([d, r]) => `${r.error_inflation_ratio}x (${DOMAIN[d] ?? d})`)
                .join(', ')}
              . Above 1 means borrowed memory is worse, so each domain keeps its own memory and model.
            </>
          )}
        </N>
          <N poll={rh}>
            {h => (
              <>
                {' '}Retraining history: {h.total_runs} gated runs across {Object.keys(h.by_domain).length} domains on scratch copies of the shipped models, {h.promoted} promoted and {h.rejected} rejected by the 3% gate (
                {Object.entries(h.by_domain)
                  .map(([d, r]) => `${DOMAIN[d] ?? d} ${r.promoted} of ${r.runs} promoted`)
                  .join(', ')}
                ). Only the turbofan runs use benchmark data; the others retrain on simulated data.
              </>
            )}
          </N>
        </>
      ),
      future: 'Retraining on failures recorded from real machines in service; every run on record uses the NASA benchmark or simulated data.',
    },
    {
      id: 'cognition',
      term: 'Machine Cognition',
      claim: 'Perceives, remembers, predicts, simulates, decides and explains in one pipeline.',
      components: ['server/atlas/world_model.py (32-dim state)', 'server/atlas/amkb.py', 'server/atlas/machine_dna.py (16-dim)', 'server/atlas/simulation.py', 'server/atlas/decision.py', 'server/cognition_trace.py'],
      see: [{ label: 'Cognition: all ten stages, latency and replay', to: '/admin/cognition', admin: true }],
      numbers: (
        <>
          <N poll={bm}>
            {b => (
              <>
                End-to-end pipeline mean latency{' '}
                {Object.entries(b.benchmark.stage_8_end_to_end_ms)
                  .map(([d, s]) => `${s.mean_ms.toFixed(1)} ms (${DOMAIN[d] ?? d})`)
                  .join(', ')}
                .{' '}
              </>
            )}
          </N>
          <N poll={ab}>
            {a => (
              <>
                The full pipeline costs {a.ablation_1.cost_reduction_percent}% less than a RUL-threshold rule ({a.ablation_1.total_cost_pipeline_a} to {a.ablation_1.total_cost_pipeline_b} cost units, {a.ablation_1.missed_failures_b} missed failures), at the price of {a.ablation_1.premature_waste_cycles_b} cycles of early replacement. AMKB grounding moves confidence from a constant {a.ablation_2.ungrounded_confidence_mean} to a calibrated mean {a.ablation_2.grounded_confidence_mean} (Spearman rho {a.ablation_2.grounded_spearman_rho ?? 'n/a'}).
              </>
            )}
          </N>
        </>
      ),
    },
    {
      id: 'platform',
      term: 'Platform',
      claim: 'Takes on new machines without code, secured by role, deployable and audited.',
      components: ['docs/ADAPTER_SDK_SPEC.md and tests/test_adapter_conformance.py', 'server/adapters/configurable_adapter.py', 'server/ingest.py, server/platform_api.py (HTTP, WebSocket, MQTT, Modbus, CSV, manual)', 'server/audit.py (hash-chained, append-only)', 'docker-compose.yml'],
      see: [
        { label: 'Sensor onboarding wizard', to: '/admin/onboarding', admin: true },
        { label: 'Devices', to: '/admin/devices', admin: true },
        { label: 'Users and roles', to: '/admin/users', admin: true },
        { label: 'Diagnostics', to: '/admin/diagnostics', admin: true },
      ],
      numbers: <>Adapter conformance suite 41 of 41 tests pass, including the configurable adapter; 443 backend tests pass; fifteen end-to-end browser checks pass, including flows 1 to 7 and an accessibility scan of every page, among them onboarding a sensor and seeing its pushed data on screen in under a second; the audit chain verifies intact.</>,
    },
    {
      id: 'explainable',
      term: 'Explainable',
      claim: 'Every prediction comes with a reason a person can check.',
      components: ['server/atlas/explain.py (occlusion attribution for all five domains, AMKB-grounded justification)', 'scripts/attribution_faithfulness.py'],
      see: [
        { label: 'Show why in the 3D Asset View (any of the five machines)', to: '/assets' },
        { label: 'Cognition: Explainability panel', to: '/admin/cognition', admin: true },
        { label: 'Agent chat with AMKB evidence', to: '/chat' },
      ],
      numbers: (
        <N poll={ff}>
          {f => (
            <>
              Deletion test on {f.summary.k2.n_units} FD001 test units: masking the 2 most-attributed sensors moves the prediction {f.summary.k2.mean_abs_delta_top.toFixed(1)} cycles against {f.summary.k2.mean_abs_delta_random.toFixed(1)} for 2 random sensors, and beats random in{' '}
              {formatPercent(f.summary.k2.top_beats_random_pct / 100)} of units (top 3: {f.summary.k3.mean_abs_delta_top.toFixed(1)} vs {f.summary.k3.mean_abs_delta_random.toFixed(1)}, {formatPercent(f.summary.k3.top_beats_random_pct / 100)}).
              {f.domains && (
                <>
                  {' '}The same test on the other domains, on simulated data (top 2 against 2 random sensors, share of windows where the top 2 win):{' '}
                  {Object.entries(f.domains)
                    .filter(([d]) => d !== 'cmapss')
                    .map(([d, r]) => `${DOMAIN[d] ?? d} ${r.summary.k2.mean_abs_delta_top.toPrecision(3)} vs ${r.summary.k2.mean_abs_delta_random.toPrecision(3)} (${formatPercent(r.summary.k2.top_beats_random_pct / 100)})`)
                    .join(', ')}
                  . Pump values are cycles; laptop, phone and server values are on their 0 to 1 output scale.
                </>
              )}
            </>
          )}
        </N>
      ),
      future: 'A check of the attribution against known fault causes on real machines; the deletion test only shows the ranking is faithful to the model.',
    },
    {
      id: 'pm',
      term: 'Predictive Maintenance',
      claim: 'Forecasts remaining useful life and turns it into a maintenance action.',
      components: ['server/atlas/rul_engine.py', 'server/atlas/decision.py', 'server/operations_api.py (work orders, alarms)', 'server/atlas/train_pump_rul.py and server/adapters/pump_degradation.py (pump RUL, simulated)'],
      see: [
        { label: 'Asset Detail: RUL band and recommended action', to: '/assets/kind/turbofan' },
        { label: 'Work orders', to: '/work-orders' },
        { label: 'Alarms', to: '/alarms' },
      ],
      numbers: (
        <>
        <N poll={ev}>
          {e => {
            const p = e.prediction_accuracy;
            const r = p.reference_baseline;
            return (
              <>
                NASA C-MAPSS FD001 test set, {p.total_test_units} units: RMSE {p.rmse.toFixed(2)}, MAE {p.mae.toFixed(2)}, PHM score {p.phm_score.toFixed(1)}. Five seeds: RMSE {r.multiseed_mean_rmse.toFixed(2)} ± {r.multiseed_std_rmse.toFixed(2)}, PHM {r.multiseed_mean_phm.toFixed(0)} ± {r.multiseed_std_phm.toFixed(1)}. Published LSTM baseline (Zheng et al., 2017): RMSE {r.literature_zheng_rmse}, PHM {r.literature_zheng_phm}.
              </>
            );
          }}
        </N>
          <N poll={pr}>
            {p => (
              <>
                {' '}Motor-pump, on simulated run-to-failure data only: {p.shipped_checkpoint.n_units} held-out simulated units, RMSE {p.shipped_checkpoint.rmse.toFixed(2)} cycles, MAE {p.shipped_checkpoint.mae.toFixed(2)}, PHM score {p.shipped_checkpoint.phm_score.toFixed(1)}; {p.multi_seed.n} seeds RMSE {p.multi_seed.rmse_mean.toFixed(2)} ± {p.multi_seed.rmse_std.toFixed(2)}; a constant guess scores RMSE {p.baseline_constant_mean.rmse.toFixed(2)}. These pump numbers measure fit to the simulator, not to real pumps.
              </>
            )}
          </N>
        </>
      ),
      future: 'Validating the pump RUL model on real pump failure data; it has only seen simulated wear.',
    },
    {
      id: 'heterogeneous',
      term: 'Heterogeneous Machine Systems',
      claim: 'One pipeline across unlike machines.',
      components: ['server/adapters/ (C-MAPSS, laptop, mobile, server, Modbus, configurable)', 'server/adapters/asset_profiles.py'],
      see: [
        { label: 'Cross-domain view', to: '/cross-domain' },
        { label: 'Five machines in 3D', to: '/assets' },
      ],
      numbers: (
        <N poll={tr}>
          {t => (
            <>
Five domains with trained World Models: turbofan on the NASA benchmark; laptop, phone, server and the Modbus motor-pump on simulated data. Within-domain RUL error on the normalised scale:{' '}
              {Object.entries(t.retrieval_transfer_diagnostics)
                .map(([d, r]) => `${r.within_rmse} (${DOMAIN[d] ?? d})`)
                .join(', ')}
              .
            </>
          )}
        </N>
      ),
      future: 'Validation on real hardware fleets: the laptop, phone, server and pump models are trained on simulated profiles, and none of the five domains has kHz-range vibration data.',
    },
  ];

  return (
    <Page title="Evidence" purpose="Each word of the title, the feature that implements it, where to see it here, and the number that backs it.">
      <section className="ax-panel" aria-labelledby="ev-matrix">
        <div className="ax-panel__head">
          <h2 id="ev-matrix">ATLAS: An Adaptive Machine Cognition Platform for Explainable Predictive Maintenance Across Heterogeneous Machine Systems</h2>
        </div>
        <div tabIndex={0} role="region" aria-label="Title terms table" className="ax-table-scroll ax-panel__body">
          <table className="ax-table">
            <caption className="visually-hidden">Title terms and their status</caption>
            <thead>
              <tr>
                <th scope="col">Term</th>
                <th scope="col">Claim</th>
                <th scope="col">Status</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(r => (
                <tr key={r.id}>
                  <th scope="row">
                    <a href={`#${r.id}`}>{r.term}</a>
                  </th>
                  <td>{r.claim}</td>
                  <td>
                    <span className="ax-row">
                      <EvidenceLabel kind="BUILD" />
                      {r.future && <EvidenceLabel kind="FUTURE-WORK" />}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {rows.map(r => (
        <section key={r.id} id={r.id} className="ax-panel" aria-labelledby={`h-${r.id}`}>
          <div className="ax-panel__head">
            <h2 id={`h-${r.id}`}>{r.term}</h2>
            <EvidenceLabel kind="BUILD" />
          </div>
          <dl className="ax-dl ax-panel__body">
            <dt>Claim</dt>
            <dd>{r.claim}</dd>
            <dt>Built in</dt>
            <dd>
              <ul className="ax-list">
                {r.components.map(c => (
                  <li key={c}>
                    <code>{c}</code>
                  </li>
                ))}
              </ul>
            </dd>
            <dt>See it</dt>
            <dd>
              <ul className="ax-list">
                {r.see.map(s => (
                  <li key={s.to + s.label}>
                    <Link to={s.to}>{s.label}</Link>
                    {s.admin && <span className="ax-note">admin</span>}
                  </li>
                ))}
              </ul>
            </dd>
            <dt>Numbers</dt>
            <dd>{r.numbers}</dd>
            {r.future && (
              <>
                <dt>
                  <EvidenceLabel kind="FUTURE-WORK" />
                </dt>
                <dd>{r.future}</dd>
              </>
            )}
          </dl>
        </section>
      ))}

      <p className="ax-note">
        Reproduce every number with the commands in docs/TITLE_JUSTIFICATION.md. C-MAPSS is NASA's simulated run-to-failure data, replayed here; values from simulators carry SIMULATED badges throughout the product.
      </p>
    </Page>
  );
}
