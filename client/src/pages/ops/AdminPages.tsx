import { useState } from 'react';
import { Link } from 'react-router';

import { DataTable, type Column } from '../../design/DataTable';
import { formatPercent, formatValue } from '../../design/format';
import { ConfirmDialog, Modal } from '../../design/overlays';
import { Button, QualityBadge, StatusPill, Timestamp } from '../../design/primitives';
import { Page } from '../../design/shell';
import { EmptyState } from '../../design/states';
import type { DataQuality } from '../../design/types';
import { useSession } from '../../contexts/SessionContext';
import { apiFetch, errorMessage } from '../../lib/api';
import { usePoll } from '../../lib/usePoll';
import { Polled } from './common';
import { DOMAIN_LABEL } from './labels';

/* ---------------------------------------------------------------- Users & roles */

interface UserRow {
  username: string;
  role: 'admin' | 'operator' | 'viewer';
  created_at: string | null;
  has_email: boolean;
}

const ROLES: UserRow['role'][] = ['admin', 'operator', 'viewer'];
const ROLE_CAN: Record<UserRow['role'], string> = {
  admin: 'Everything, including administration and the cognition dashboard',
  operator: 'Read everything outside administration; acknowledge alarms; create, approve and close work orders; agent chat',
  viewer: 'Read only',
};

export function UsersPage() {
  const poll = usePoll<UserRow[]>('/api/admin/users', 0);
  const me = useSession();
  const [change, setChange] = useState<{ user: UserRow; role: UserRow['role'] } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const columns: Column<UserRow>[] = [
    { key: 'username', header: 'User', render: u => u.username, sortValue: u => u.username },
    { key: 'role', header: 'Role', width: '10rem', render: u => <StatusPill tone={u.role === 'admin' ? 'accent' : 'quiet'}>{u.role}</StatusPill>, sortValue: u => ROLES.indexOf(u.role) },
    { key: 'created', header: 'Created', width: '12rem', render: u => (u.created_at ? <Timestamp value={u.created_at} style="date" /> : '--'), sortValue: u => u.created_at },
    { key: 'email', header: 'Alert email', width: '8rem', render: u => (u.has_email ? 'Set' : '--') },
    {
      key: 'change',
      header: 'Change role',
      width: '12rem',
      render: u =>
        u.username === me.username ? (
          <span className="ax-note">Your own account</span>
        ) : (
          <select className="ax-input" aria-label={`Role for ${u.username}`} value={u.role} onChange={e => setChange({ user: u, role: e.target.value as UserRow['role'] })}>
            {ROLES.map(r => (
              <option key={r}>{r}</option>
            ))}
          </select>
        ),
    },
  ];

  const apply = async () => {
    if (!change) return;
    setBusy(true);
    setError(null);
    try {
      await apiFetch(`/api/admin/users/${encodeURIComponent(change.user.username)}`, { method: 'PATCH', body: JSON.stringify({ role: change.role }) });
      setChange(null);
      poll.reload();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Page title="Users & roles" purpose="Accounts and what each role may do. The server enforces the same rules.">
      <section className="ax-panel">
        <div className="ax-panel__body">
          <dl className="ax-dl">
            {ROLES.map(r => (
              <div key={r} style={{ display: 'contents' }}>
                <dt>{r}</dt>
                <dd>{ROLE_CAN[r]}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>
      {error && (
        <p className="ax-error" role="alert">
          {error}
        </p>
      )}
      <section className="ax-panel">
        <Polled poll={poll}>
          {users => (users.length ? <DataTable rows={users} columns={columns} rowKey={u => u.username} caption="Users" filterPlaceholder="Filter users" initialSort={{ key: 'role', dir: 'asc' }} /> : <EmptyState title="No users" />)}
        </Polled>
      </section>
      <p className="ax-note">New accounts are created with scripts/seed_dev.py or by the database administrator; passwords never pass through this page.</p>
      {change && (
        <ConfirmDialog
          open
          title={`Change role of ${change.user.username}`}
          description={
            <p>
              From <strong>{change.user.role}</strong> to <strong>{change.role}</strong>. {ROLE_CAN[change.role]}. The change takes effect on their next request.
            </p>
          }
          confirmLabel="Change role"
          busy={busy}
          onCancel={() => setChange(null)}
          onConfirm={apply}
        />
      )}
    </Page>
  );
}

/* ---------------------------------------------------------------- Devices */

export interface Device {
  device_id: string;
  machine_id: string;
  protocol: string;
  created_at: string | null;
  rotated_at: string | null;
  revoked_at: string | null;
  last_seen: string | null;
  msg_count: number;
  err_count: number;
  messages_per_min: number;
  error_rate: number;
  quality: Record<string, DataQuality>;
}

export function TokenNotice({ token, examples, onClose }: { token: string; examples?: Record<string, string>; onClose: () => void }) {
  return (
    <Modal open onClose={onClose} title="Device token" footer={<Button variant="primary" onClick={onClose}>I have copied it</Button>}>
      <p>Shown once. ATLAS stores only its SHA-256 hash, so it cannot be shown again; rotate to get a new one.</p>
      <code className="ax-code">{token}</code>
      {examples &&
        Object.entries(examples).map(([k, v]) => (
          <div key={k} className="ax-field">
            <span className="ax-field__label">{k}</span>
            <code className="ax-code">{v}</code>
          </div>
        ))}
    </Modal>
  );
}

export function DevicesPage() {
  const poll = usePoll<Device[]>('/api/admin/devices', 5000);
  const [confirm, setConfirm] = useState<{ device: Device; op: 'rotate' | 'revoke' } | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    if (!confirm) return;
    setBusy(true);
    setError(null);
    try {
      const id = encodeURIComponent(confirm.device.device_id);
      if (confirm.op === 'rotate') setToken((await apiFetch<{ token: string }>(`/api/admin/devices/${id}/rotate`, { method: 'POST' })).token);
      else await apiFetch(`/api/admin/devices/${id}`, { method: 'DELETE' });
      setConfirm(null);
      poll.reload();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  const columns: Column<Device>[] = [
    { key: 'machine', header: 'Asset', width: '10rem', render: d => d.machine_id, sortValue: d => d.machine_id },
    { key: 'protocol', header: 'Protocol', width: '7rem', render: d => d.protocol, sortValue: d => d.protocol },
    { key: 'seen', header: 'Last seen', width: '11rem', render: d => (d.last_seen ? <Timestamp value={d.last_seen} /> : <QualityBadge quality="MISSING" />), sortValue: d => d.last_seen },
    { key: 'rate', header: 'Messages', align: 'right', width: '7rem', render: d => `${d.messages_per_min}/min`, sortValue: d => d.messages_per_min },
    { key: 'err', header: 'Errors', align: 'right', width: '6rem', render: d => formatPercent(d.error_rate, 1), sortValue: d => d.error_rate },
    {
      key: 'quality',
      header: 'Channel quality',
      render: d => {
        const q = Object.entries(d.quality ?? {});
        return q.length ? (
          <span className="ax-row">
            {q.map(([ch, v]) => (
              <span key={ch} className="ax-row" title={ch}>
                <QualityBadge quality={v} compact={v === 'GOOD'} />
                <span className="ax-note">{ch}</span>
              </span>
            ))}
          </span>
        ) : (
          '--'
        );
      },
    },
    {
      key: 'ops',
      header: 'Token',
      width: '11rem',
      render: d =>
        d.revoked_at ? (
          <StatusPill tone="quiet">Revoked</StatusPill>
        ) : (
          <span className="ax-row">
            <Button size="sm" onClick={() => setConfirm({ device: d, op: 'rotate' })}>
              Rotate
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setConfirm({ device: d, op: 'revoke' })}>
              Revoke
            </Button>
          </span>
        ),
    },
  ];

  return (
    <Page title="Devices" purpose="Connection health of every device that pushes data: last seen, message rate, error rate, channel quality." actions={<Link to="/admin/onboarding">Onboard a sensor</Link>}>
      {error && (
        <p className="ax-error" role="alert">
          {error}
        </p>
      )}
      <section className="ax-panel">
        <Polled poll={poll}>
          {list =>
            list.length ? (
              <DataTable rows={list} columns={columns} rowKey={d => d.device_id} caption="Devices" filterPlaceholder="Filter devices" initialSort={{ key: 'seen', dir: 'desc' }} />
            ) : (
              <EmptyState title="No devices yet" body="Domain adapters poll by themselves and are not listed here. Devices appear once onboarded." action={<Link to="/admin/onboarding">Onboard a sensor</Link>} />
            )
          }
        </Polled>
      </section>
      {confirm && (
        <ConfirmDialog
          open
          title={confirm.op === 'rotate' ? `Rotate token for ${confirm.device.machine_id}` : `Revoke ${confirm.device.machine_id}`}
          description={confirm.op === 'rotate' ? 'A new token is issued and the old one stops working at once. Update the device before it next sends.' : 'The device can no longer send data. This cannot be undone; onboard it again to reconnect.'}
          confirmLabel={confirm.op === 'rotate' ? 'Rotate token' : 'Revoke'}
          danger={confirm.op === 'revoke'}
          busy={busy}
          onCancel={() => setConfirm(null)}
          onConfirm={run}
        />
      )}
      {token && <TokenNotice token={token} onClose={() => setToken(null)} />}
    </Page>
  );
}

/* ---------------------------------------------------------------- Diagnostics */

interface Ready {
  status: string;
  checks: { database: string; mqtt: string; models: string[] | string; audit: { pending_db_writes: number } | string };
}

interface Stat {
  mean_ms: number;
  p95_ms: number;
}

interface Benchmark {
  benchmark: {
    hardware_context: { processor: string; logical_cores: number; total_ram_gb: number; torch_backend: string; timestamp: string };
    stage_8_end_to_end_ms: Record<string, Stat>;
    [stage: string]: unknown;
  };
}

const STAGES: [string, string][] = [
  ['stage_4_machine_dna_ms', 'Machine DNA'],
  ['stage_5_explainability_ms', 'Explainability'],
  ['stage_6_simulation_ms', 'Monte Carlo simulation'],
  ['stage_7_decision_graph_ms', 'Decision Graph'],
];

interface ModelStatus {
  trained_domains: string[];
  active_engines: Record<string, { using_lstm: boolean }>;
  metrics: Record<string, { benchmark?: { rmse: number; phm_score: number; n_test_units: number } }>;
}

export function DiagnosticsPage() {
  const ready = usePoll<Ready>('/api/ready', 10_000);
  const models = usePoll<ModelStatus>('/api/atlas/models/status', 0);
  const bench = usePoll<Benchmark>('/api/atlas/system/benchmark', 0);
  const ok = (v: unknown) => v === 'ok' || v === 'connected';
  return (
    <Page title="Diagnostics" purpose="Health of the platform itself: database, broker, models and pipeline latency.">
      <div className="ax-grid">
        <section className="ax-panel" aria-labelledby="dg-ready">
          <div className="ax-panel__head">
            <h2 id="dg-ready">Readiness</h2>
            {ready.data && <StatusPill tone={ready.data.status === 'ready' ? 'quiet' : 'high'}>{ready.data.status}</StatusPill>}
          </div>
          <Polled poll={ready} rows={4}>
            {r => (
              <dl className="ax-dl ax-panel__body">
                <dt>Database</dt>
                <dd>{ok(r.checks.database) ? 'Connected' : <StatusPill tone="high">{String(r.checks.database)}</StatusPill>}</dd>
                <dt>MQTT broker</dt>
                <dd>{ok(r.checks.mqtt) ? 'Connected' : <StatusPill tone="medium">{String(r.checks.mqtt)}</StatusPill>}</dd>
                <dt>Models loaded</dt>
                <dd>{Array.isArray(r.checks.models) ? r.checks.models.map(m => DOMAIN_LABEL[m] ?? m).join(', ') : String(r.checks.models)}</dd>
                <dt>Audit writes pending</dt>
                <dd className="num">{typeof r.checks.audit === 'object' ? r.checks.audit.pending_db_writes : String(r.checks.audit)}</dd>
              </dl>
            )}
          </Polled>
        </section>
        <section className="ax-panel" aria-labelledby="dg-models">
          <div className="ax-panel__head">
            <h2 id="dg-models">RUL models</h2>
          </div>
          <Polled poll={models} rows={4}>
            {m => (
              <ul className="ax-list">
                {Object.keys(DOMAIN_LABEL).map(d => {
                  const bm = m.metrics[d]?.benchmark;
                  return (
                    <li key={d}>
                      <strong>{DOMAIN_LABEL[d]}</strong>
                      {m.trained_domains.includes(d) ? (
                        <span className="ax-note">{m.active_engines[d]?.using_lstm ? 'LSTM loaded' : 'EMA fallback'}</span>
                      ) : (
                        <StatusPill tone="quiet">No model (FUTURE-WORK)</StatusPill>
                      )}
                      {bm && (
                        <span className="num">
                          RMSE {bm.rmse.toFixed(2)} · PHM {bm.phm_score.toFixed(0)} on {bm.n_test_units} test units
                        </span>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </Polled>
        </section>
      </div>
      <section className="ax-panel" aria-labelledby="dg-latency">
        <div className="ax-panel__head">
          <h2 id="dg-latency">Pipeline latency (recorded benchmark)</h2>
        </div>
        <Polled poll={bench} rows={5} title="No benchmark recorded">
          {({ benchmark: b }) => (
            <div className="ax-panel__body ax-stack">
              <p className="ax-note">
                From scripts/benchmark_system.py on {b.hardware_context.processor}, {b.hardware_context.logical_cores} threads, {b.hardware_context.total_ram_gb} GB, {b.hardware_context.torch_backend}, recorded <Timestamp value={b.hardware_context.timestamp} style="date" />. Not live measurements.
              </p>
              <ul className="ax-list">
                {Object.entries(b.stage_8_end_to_end_ms).map(([d, s]) => (
                  <li key={d}>
                    End to end, {DOMAIN_LABEL[d] ?? d}
                    <span className="num">
                      {formatValue(s.mean_ms, 'ms', 1)} mean · {formatValue(s.p95_ms, 'ms', 1)} p95
                    </span>
                  </li>
                ))}
                {STAGES.map(([k, label]) => {
                  const s = b[k] as Stat | undefined;
                  return s ? (
                    <li key={k}>
                      {label}
                      <span className="num">
                        {formatValue(s.mean_ms, 'ms', 2)} mean · {formatValue(s.p95_ms, 'ms', 2)} p95
                      </span>
                    </li>
                  ) : null;
                })}
              </ul>
            </div>
          )}
        </Polled>
      </section>
    </Page>
  );
}
