import { useState } from 'react';

import { ConfirmDialog } from '../../design/overlays';
import { Button, SimBadge, StatusPill, Timestamp } from '../../design/primitives';
import { Page } from '../../design/shell';
import { apiFetch, errorMessage } from '../../lib/api';
import { usePoll } from '../../lib/usePoll';
import { Polled } from './common';
import { DOMAIN_LABEL } from './labels';

/* Mirrors server/cognition_admin.py model_registry(). */
interface Version {
  version: string;
  checkpoint: string;
  size: number;
  archived_at: string;
  metrics: Record<string, unknown>;
  active: boolean;
}
interface LearningEvent {
  id: number;
  triggered_at: string;
  trigger_reason: string;
  epochs_run: number;
  rmse_before: number | null;
  rmse_after: number | null;
  success: boolean;
  notes: string | null;
}
interface DomainRow {
  domain: string;
  active: { version: string; checkpoint: string } | null;
  metrics: Record<string, unknown> & { benchmark?: { rmse: number; phm_score: number; n_test_units: number } };
  versions: Version[];
  learning_history: LearningEvent[];
}

/* What each domain's model learns from (server/atlas/learning_engine.py data_source()). */
const RETRAIN_DATA: Record<string, string> = {
  cmapss: 'the NASA C-MAPSS FD001 training split',
  modbus: 'simulated pump run-to-failure data',
  laptop: 'a simulated laptop workload profile',
  mobile: 'a simulated phone workload profile',
  server: 'a simulated server workload profile',
};

const SHOWN = ['final_val_loss', 'final_train_loss', 'epochs', 'training_time_s', 'subset'];

export default function ModelsPage() {
  const poll = usePoll<{ domains: DomainRow[]; note: string }>('/api/admin/models/registry', 0);
  const [pending, setPending] = useState<{ domain: string; version: Version; current: string } | null>(null);
  const [retrain, setRetrain] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);

  const act = async (fn: () => Promise<string>) => {
    setBusy(true);
    setMessage(null);
    try {
      setMessage({ ok: true, text: await fn() });
      setPending(null);
      setRetrain(null);
      poll.reload();
    } catch (e) {
      setMessage({ ok: false, text: errorMessage(e) });
    } finally {
      setBusy(false);
    }
  };

  return (
    <Page title="Model registry" purpose="Every World Model version ATLAS has served, with its metrics. Activating an older version rolls back; every change is reversible and audited.">
      {message && (
        <p className={message.ok ? 'ax-note' : 'ax-error'} role={message.ok ? 'status' : 'alert'}>
          {message.text}
        </p>
      )}
      <Polled poll={poll} rows={8}>
        {({ domains, note }) => (
          <div className="ax-stack">
            <p className="ax-note">{note} Versions are archived by content hash when this page first sees them; weights overwritten before P5 cannot be recovered.</p>
            {domains.map(d => (
              <section key={d.domain} className="ax-panel" aria-labelledby={`m-${d.domain}`}>
                <div className="ax-panel__head">
                  <h2 id={`m-${d.domain}`}>{DOMAIN_LABEL[d.domain] ?? d.domain}</h2>
                  {d.active ? (
                    <span className="ax-note num">
                      active {d.active.checkpoint} · {d.active.version}
                    </span>
                  ) : (
                    <span className="ax-note">No checkpoint installed</span>
                  )}
                  {d.domain !== 'cmapss' && d.active && <SimBadge />}
                  {d.active && (
                    <Button size="sm" onClick={() => setRetrain(d.domain)}>
                      Retrain
                    </Button>
                  )}
                </div>
                <div className="ax-panel__body ax-stack">
                  {RETRAIN_DATA[d.domain] && d.domain !== 'cmapss' && <p className="ax-note">Trained and retrained on {RETRAIN_DATA[d.domain]}. Not validated on real hardware.</p>}
                  {d.metrics.benchmark && (
                    <p>
                      FD001 test benchmark: RMSE <strong className="num">{d.metrics.benchmark.rmse.toFixed(2)}</strong>, PHM score <strong className="num">{d.metrics.benchmark.phm_score.toFixed(1)}</strong> on{' '}
                      {d.metrics.benchmark.n_test_units} units.
                    </p>
                  )}
                  <table className="ax-table">
                    <caption className="visually-hidden">Versions of the {d.domain} model</caption>
                    <thead>
                      <tr>
                        <th scope="col">Version</th>
                        <th scope="col">Archived</th>
                        <th scope="col">Metrics at archive time</th>
                        <th scope="col">State</th>
                      </tr>
                    </thead>
                    <tbody>
                      {d.versions.map(v => (
                        <tr key={v.version}>
                          <th scope="row" className="num">
                            {v.version}
                          </th>
                          <td>
                            <Timestamp value={v.archived_at} />
                          </td>
                          <td className="ax-note">
                            {SHOWN.filter(k => v.metrics[k] !== undefined)
                              .map(k => `${k.replace(/_/g, ' ')} ${typeof v.metrics[k] === 'number' ? Number(Number(v.metrics[k]).toFixed(3)) : String(v.metrics[k])}`)
                              .join(' · ') || 'none recorded'}
                          </td>
                          <td>
                            {v.active ? (
                              <StatusPill tone="accent">Active</StatusPill>
                            ) : (
                              <Button size="sm" onClick={() => setPending({ domain: d.domain, version: v, current: d.active?.version ?? '' })}>
                                Make active
                              </Button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {d.learning_history.length > 0 && (
                    <details>
                      <summary className="ax-note">Retraining runs ({d.learning_history.length})</summary>
                      <ul className="ax-list">
                        {d.learning_history.map(h => (
                          <li key={h.id}>
                            <StatusPill tone={h.success ? 'quiet' : 'medium'}>{h.success ? 'Promoted' : 'Rejected'}</StatusPill>
                            <span className="ax-note">{h.notes}</span>
                          </li>
                        ))}
                      </ul>
                    </details>
                  )}
                </div>
              </section>
            ))}
          </div>
        )}
      </Polled>

      {pending && (
        <ConfirmDialog
          open
          title={`Activate ${pending.version.version} for ${DOMAIN_LABEL[pending.domain] ?? pending.domain}`}
          description={
            <p>
              Replaces the active weights ({pending.current}) with version {pending.version.version} and reloads the model at once. The current weights stay archived, so this can be undone from this page.
            </p>
          }
          confirmLabel="Activate version"
          requireReason
          busy={busy}
          onCancel={() => setPending(null)}
          onConfirm={reason =>
            act(async () => {
              const r = await apiFetch<{ reloaded: boolean }>(`/api/admin/models/${pending.domain}/activate`, { method: 'POST', body: JSON.stringify({ version: pending.version.version, reason }) });
              return `Version ${pending.version.version} is active${r.reloaded ? ' and loaded.' : '; the reload did not confirm, check Diagnostics.'}`;
            })
          }
        />
      )}
      {retrain && (
        <ConfirmDialog
          open
          title={`Retrain the ${DOMAIN_LABEL[retrain] ?? retrain} World Model`}
          description={
            <p>
              Runs 5 epochs on {RETRAIN_DATA[retrain] ?? 'the domain\'s training data'} (up to several minutes of CPU). The candidate is promoted only if its validation RMSE is within 3% of the best ever promoted; otherwise the active model is left as it is.
            </p>
          }
          confirmLabel="Start retraining"
          requireReason
          busy={busy}
          onCancel={() => setRetrain(null)}
          onConfirm={reason =>
            act(async () => {
              const r = await apiFetch<{ success: boolean; notes: string }>('/api/learn/retrain', { method: 'POST', body: JSON.stringify({ domain: retrain, trigger_reason: `manual: ${reason}`.slice(0, 200) }) });
              return r.notes;
            })
          }
        />
      )}
    </Page>
  );
}
