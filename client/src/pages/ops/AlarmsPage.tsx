import { useId, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router';

import { ACTIVE_STATES, isFlood } from '../../design/alarmModel';
import { AlarmTable } from '../../design/alarms';
import { useNow } from '../../design/hooks';
import { Drawer, Modal } from '../../design/overlays';
import { Button, StatusPill, Timestamp } from '../../design/primitives';
import { Page } from '../../design/shell';
import { EmptyState } from '../../design/states';
import { STATE_LABEL } from '../../design/types';
import { useSession } from '../../contexts/SessionContext';
import { errorMessage } from '../../lib/api';
import { alarmAction, useAlarms, workOrderHref, type AlarmAction, type OpsAlarm } from '../../lib/ops';
import { Polled } from './common';

type View = 'active' | 'shelved' | 'all';
const VIEWS: { id: View; label: string }[] = [
  { id: 'active', label: 'Active' },
  { id: 'shelved', label: 'Shelved' },
  { id: 'all', label: 'All events' },
];

const SHELVE_MINUTES = [15, 60, 240, 480, 1440];

/** Shelve and clear need a reason (and shelve a time limit); acknowledge does not. */
interface Pending {
  alarm: OpsAlarm;
  action: Exclude<AlarmAction, 'ack' | 'unshelve'>;
}

export default function AlarmsPage() {
  const poll = useAlarms(5000);
  const user = useSession();
  const canAct = user.role === 'admin' || user.role === 'operator';
  const [params, setParams] = useSearchParams();
  const view = (params.get('view') as View) || 'active';
  // The open alarm lives in the URL (?alarm=<id>), so a link can point at one alarm.
  const selectedId = params.get('alarm');
  const selected = poll.alarms?.find(a => a.id === selectedId) ?? null;
  const setSelected = (a: OpsAlarm | null) => {
    const next = new URLSearchParams(params);
    if (a) next.set('alarm', a.id);
    else next.delete('alarm');
    setParams(next);
  };
  const [pending, setPending] = useState<Pending | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const now = useNow(30_000);

  const rows = useMemo(() => {
    const all = poll.alarms ?? [];
    if (view === 'shelved') return all.filter(a => a.state === 'shelved');
    if (view === 'active') return all.filter(a => ACTIVE_STATES.includes(a.state));
    return all;
  }, [poll.alarms, view]);

  const run = async (a: OpsAlarm, action: AlarmAction, body: { reason?: string; minutes?: number } = {}) => {
    setBusy(a.id);
    setError(null);
    try {
      await alarmAction(a.id, action, body);
      setPending(null);
      poll.reload();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(null);
    }
  };

  const actions = canAct
    ? (a: OpsAlarm) => (
        <span className="ax-row">
          {(a.state === 'unack' || a.state === 'rtn_unack') && (
            <Button size="sm" disabled={busy === a.id} onClick={() => run(a, 'ack')}>
              Acknowledge
            </Button>
          )}
          {a.state === 'ack' && (
            <Button size="sm" disabled={busy === a.id} onClick={() => setPending({ alarm: a, action: 'clear' })}>
              Clear
            </Button>
          )}
          {a.state === 'shelved' ? (
            <Button size="sm" variant="ghost" disabled={busy === a.id} onClick={() => run(a, 'unshelve')}>
              Unshelve
            </Button>
          ) : (
            ACTIVE_STATES.includes(a.state) && (
              <Button size="sm" variant="ghost" disabled={busy === a.id} onClick={() => setPending({ alarm: a, action: 'shelve' })}>
                Shelve
              </Button>
            )
          )}
        </span>
      )
    : undefined;

  const flood = poll.alarms ? isFlood(poll.alarms, now.getTime()) : false;
  const count = (v: View) => (poll.alarms ?? []).filter(a => (v === 'shelved' ? a.state === 'shelved' : ACTIVE_STATES.includes(a.state))).length;

  return (
    <Page
      title="Alarms & events"
      purpose="ISA-18.2 alarm list, highest priority first. Every action is recorded with your name."
      actions={flood ? <StatusPill tone="high">Alarm flood: more than 10 alarms in 10 minutes</StatusPill> : undefined}
    >
      <div className="ax-row" role="tablist" aria-label="Alarm view">
        {VIEWS.map(v => (
          <Button key={v.id} size="sm" variant={v.id === view ? 'primary' : 'default'} role="tab" aria-selected={v.id === view} onClick={() => setParams({ view: v.id })}>
            {v.label}
            {poll.alarms && v.id !== 'all' && <span className="num">{count(v.id)}</span>}
          </Button>
        ))}
      </div>
      {error && (
        <p className="ax-error" role="alert">
          {error}
        </p>
      )}
      {!canAct && <p className="ax-note">Your role can view alarms. Acknowledging and shelving need an operator or admin.</p>}
      <section className="ax-panel">
        <Polled poll={poll} rows={8}>
          {() =>
            rows.length === 0 ? (
              <EmptyState title={view === 'shelved' ? 'Nothing is shelved' : view === 'active' ? 'No active alarms' : 'No alarms recorded'} body="Alarms are raised by the threshold and cognition pipelines." />
            ) : (
              <AlarmTable alarms={rows} actions={actions} onSelect={setSelected} selectedId={selectedId} />
            )
          }
        </Polled>
      </section>

      <Drawer open={!!selected} onClose={() => setSelected(null)} title={selected ? `Alarm ${selected.id}` : 'Alarm'}>
        {selected && (
          <>
            <AlarmDetail alarm={selected} canAct={canAct} />
            {actions && <div style={{ marginTop: 'var(--space-4)' }}>{actions(selected)}</div>}
          </>
        )}
      </Drawer>

      {pending && (
        <ReasonDialog
          key={`${pending.alarm.id}-${pending.action}`}
          pending={pending}
          busy={busy === pending.alarm.id}
          onCancel={() => setPending(null)}
          onConfirm={(reason, minutes) => run(pending.alarm, pending.action, { reason, minutes })}
        />
      )}
    </Page>
  );
}

function AlarmDetail({ alarm, canAct }: { alarm: OpsAlarm; canAct: boolean }) {
  const r = alarm.raw;
  return (
    <div className="ax-stack">
      <dl className="ax-dl">
        <dt>Asset</dt>
        <dd>{r.machine_id}</dd>
        <dt>Condition</dt>
        <dd>{r.message}</dd>
        <dt>Priority</dt>
        <dd>{alarm.priority}</dd>
        <dt>State</dt>
        <dd>{STATE_LABEL[alarm.state]}</dd>
        <dt>Raised</dt>
        <dd>
          <Timestamp value={r.raised_at} showZone />
        </dd>
        <dt>Fault type</dt>
        <dd>{r.fault_type ?? 'n/a'}</dd>
        <dt>Source</dt>
        <dd>{r.source ?? 'n/a'}</dd>
        {r.state_by && (
          <>
            <dt>Last action</dt>
            <dd>
              {r.state_by}, {r.state_at && <Timestamp value={r.state_at} />}
            </dd>
          </>
        )}
        {r.state_reason && (
          <>
            <dt>Reason</dt>
            <dd>{r.state_reason}</dd>
          </>
        )}
        {r.shelved_until && alarm.state === 'shelved' && (
          <>
            <dt>Shelved until</dt>
            <dd>
              <Timestamp value={r.shelved_until} showZone />
            </dd>
          </>
        )}
      </dl>
      {canAct && <Link to={workOrderHref(r.machine_id, null, r.id)}>Create a work order for this alarm</Link>}
    </div>
  );
}

function ReasonDialog({ pending, busy, onCancel, onConfirm }: { pending: Pending; busy: boolean; onCancel: () => void; onConfirm: (reason: string, minutes?: number) => void }) {
  const [reason, setReason] = useState('');
  const [minutes, setMinutes] = useState(60);
  const reasonId = useId();
  const minutesId = useId();
  const shelve = pending.action === 'shelve';
  const ok = reason.trim().length >= 5;
  return (
    <Modal
      open
      onClose={onCancel}
      title={shelve ? `Shelve alarm ${pending.alarm.id}` : `Clear alarm ${pending.alarm.id}`}
      footer={
        <>
          <Button onClick={onCancel}>Cancel</Button>
          <Button variant="primary" disabled={!ok || busy} onClick={() => onConfirm(reason.trim(), shelve ? minutes : undefined)}>
            {busy ? 'Working' : shelve ? 'Shelve' : 'Clear alarm'}
          </Button>
        </>
      }
    >
      <p>
        <strong>{pending.alarm.assetName}</strong>: {pending.alarm.message}
      </p>
      <p className="ax-note">
        {shelve
          ? 'A shelved alarm is hidden from the active list until the time runs out, then it returns unacknowledged.'
          : 'Clear only when the condition is resolved. ATLAS does not yet detect the return to normal by itself.'}
      </p>
      {shelve && (
        <label className="ax-field" htmlFor={minutesId}>
          <span className="ax-field__label">Shelve for</span>
          <select id={minutesId} className="ax-input" value={minutes} onChange={e => setMinutes(Number(e.target.value))}>
            {SHELVE_MINUTES.map(m => (
              <option key={m} value={m}>
                {m < 60 ? `${m} min` : `${m / 60} h`}
              </option>
            ))}
          </select>
        </label>
      )}
      <label className="ax-field" htmlFor={reasonId}>
        <span className="ax-field__label">Reason</span>
        <textarea id={reasonId} className="ax-input" autoFocus value={reason} onChange={e => setReason(e.target.value)} minLength={5} required />
        <span className="ax-field__hint">At least 5 characters. Recorded with your name in the audit trail.</span>
      </label>
    </Modal>
  );
}
