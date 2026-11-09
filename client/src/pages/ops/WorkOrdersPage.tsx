import { useId, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router';
import { Plus } from 'lucide-react';

import { DataTable, type Column } from '../../design/DataTable';
import { ConfirmDialog, Drawer, Modal } from '../../design/overlays';
import { Button, PriorityLabel, StatusPill, Timestamp } from '../../design/primitives';
import { Page } from '../../design/shell';
import { EmptyState } from '../../design/states';
import { useSession } from '../../contexts/SessionContext';
import { apiFetch, errorMessage } from '../../lib/api';
import { createWorkOrder, URGENCY_TONE, type Urgency, type WorkOrder, type WorkOrderStatus } from '../../lib/ops';
import { usePoll } from '../../lib/usePoll';
import { Polled } from './common';

const STATUSES: WorkOrderStatus[] = ['Pending Approval', 'Open', 'In Progress', 'Resolved', 'Rejected'];
const URGENCIES: Urgency[] = ['Critical', 'High', 'Medium', 'Low'];
const OPEN: WorkOrderStatus[] = ['Pending Approval', 'Open', 'In Progress'];

const post = (path: string, body?: unknown) => apiFetch(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) });

type Step = 'approve' | 'reject' | 'start' | 'resolve';
const STEP: Record<Step, { label: string; from: WorkOrderStatus[]; call: (id: string, reason: string) => Promise<unknown>; reason?: boolean; danger?: boolean; text: string }> = {
  approve: { label: 'Approve', from: ['Pending Approval'], call: id => post(`/api/work-orders/${id}/approve`), text: 'The order becomes Open and can be assigned and started.' },
  reject: { label: 'Reject', from: ['Pending Approval'], call: (id, reason) => post(`/api/work-orders/${id}/reject`, { reason }), reason: true, danger: true, text: 'The order is closed without work. This cannot be undone.' },
  start: { label: 'Start', from: ['Open'], call: id => post(`/api/work-orders/${id}/start`), text: 'Marks the work as in progress.' },
  resolve: { label: 'Resolve', from: ['Open', 'In Progress'], call: id => apiFetch(`/api/work-orders/${id}/resolve`, { method: 'PATCH' }), text: 'Closes the order as done. This cannot be undone.' },
};

export default function WorkOrdersPage() {
  const [params, setParams] = useSearchParams();
  const filter = params.get('status') ?? 'open';
  const poll = usePoll<{ work_orders: WorkOrder[] }>('/api/work-orders?limit=200', 5000);
  const user = useSession();
  const canAct = user.role === 'admin' || user.role === 'operator';
  const assignable = usePoll<{ username: string; role: string }[]>(canAct ? '/api/users/assignable' : null, 0);
  const [selected, setSelected] = useState<string | null>(null);
  const [confirm, setConfirm] = useState<{ order: WorkOrder; step: Step } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const creating = params.get('new') === '1';

  const orders = useMemo(() => {
    const all = poll.data?.work_orders ?? [];
    return filter === 'open' ? all.filter(o => OPEN.includes(o.status)) : filter === 'all' ? all : all.filter(o => o.status === filter);
  }, [poll.data, filter]);
  const sel = poll.data?.work_orders.find(o => o.order_id === selected) ?? null;

  const act = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await fn();
      setConfirm(null);
      poll.reload();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  const closeCreate = () => {
    const next = new URLSearchParams(params);
    ['new', 'machine', 'domain', 'alarm', 'action', 'urgency'].forEach(k => next.delete(k));
    setParams(next);
  };

  const columns: Column<WorkOrder>[] = [
    { key: 'urgency', header: 'Urgency', width: '8rem', render: o => <PriorityLabel priority={URGENCY_TONE[o.urgency] ?? 'medium'} state="ack" />, sortValue: o => URGENCIES.indexOf(o.urgency) },
    { key: 'status', header: 'Status', width: '9rem', render: o => <StatusPill tone={o.status === 'Pending Approval' ? 'accent' : 'quiet'}>{o.status}</StatusPill>, sortValue: o => STATUSES.indexOf(o.status) },
    { key: 'machine', header: 'Asset', width: '9rem', render: o => o.machine_id, sortValue: o => o.machine_id },
    { key: 'action', header: 'Action', render: o => o.action, sortValue: o => o.action },
    { key: 'assignee', header: 'Assignee', width: '8rem', render: o => o.assignee ?? '--', sortValue: o => o.assignee },
    { key: 'created', header: 'Created', width: '11rem', render: o => <Timestamp value={o.created_at} />, sortValue: o => o.created_at },
  ];
  if (canAct)
    columns.push({
      key: 'next',
      header: 'Next step',
      width: '11rem',
      render: o => (
        <span className="ax-row">
          {(Object.keys(STEP) as Step[])
            .filter(s => STEP[s].from.includes(o.status))
            .map(s => (
              <Button key={s} size="sm" variant={s === 'reject' ? 'ghost' : 'default'} onClick={() => setConfirm({ order: o, step: s })}>
                {STEP[s].label}
              </Button>
            ))}
        </span>
      ),
    });

  return (
    <Page
      title="Work orders"
      purpose="Maintenance actions from request through approval to closure."
      actions={
        canAct && (
          <Button variant="primary" icon={<Plus aria-hidden />} onClick={() => setParams({ ...Object.fromEntries(params), new: '1' })}>
            New work order
          </Button>
        )
      }
    >
      <div className="ax-row" role="tablist" aria-label="Status filter">
        {[['open', 'Open'], ...STATUSES.map(s => [s, s]), ['all', 'All']].map(([id, label]) => (
          <Button key={id} size="sm" role="tab" aria-selected={filter === id} variant={filter === id ? 'primary' : 'default'} onClick={() => setParams({ status: id })}>
            {label}
          </Button>
        ))}
      </div>
      {error && (
        <p className="ax-error" role="alert">
          {error}
        </p>
      )}
      <section className="ax-panel">
        <Polled poll={poll} rows={6}>
          {() =>
            orders.length === 0 ? (
              <EmptyState title="No work orders here" body="Orders are created from an asset, an alarm or this page, and by the maintenance agent." />
            ) : (
              <DataTable rows={orders} columns={columns} rowKey={o => o.order_id} caption="Work orders" filterPlaceholder="Filter work orders" initialSort={{ key: 'urgency', dir: 'asc' }} onRowActivate={o => setSelected(o.order_id)} selectedKey={selected} />
            )
          }
        </Polled>
      </section>

      <Drawer open={!!sel} onClose={() => setSelected(null)} title={sel ? `Work order for ${sel.machine_id}` : 'Work order'}>
        {sel && (
          <div className="ax-stack">
            <dl className="ax-dl">
              <dt>Action</dt>
              <dd>{sel.action}</dd>
              <dt>Status</dt>
              <dd>{sel.status}</dd>
              <dt>Urgency</dt>
              <dd>{sel.urgency}</dd>
              <dt>Asset</dt>
              <dd>{sel.domain ? <Link to={`/assets/${sel.domain}/${encodeURIComponent(sel.machine_id)}`}>{sel.machine_id}</Link> : sel.machine_id}</dd>
              {sel.alarm_id !== null && (
                <>
                  <dt>From alarm</dt>
                  <dd>{sel.alarm_id}</dd>
                </>
              )}
              <dt>Created</dt>
              <dd>
                <Timestamp value={sel.created_at} showZone /> by {sel.created_by ?? 'unknown'}
              </dd>
              {sel.resolved_at && (
                <>
                  <dt>Resolved</dt>
                  <dd>
                    <Timestamp value={sel.resolved_at} showZone />
                  </dd>
                </>
              )}
              {sel.notes && (
                <>
                  <dt>Notes</dt>
                  <dd style={{ whiteSpace: 'pre-wrap' }}>{sel.notes}</dd>
                </>
              )}
            </dl>
            {canAct && OPEN.includes(sel.status) && (
              <AssignField
                key={sel.order_id}
                order={sel}
                users={assignable.data ?? []}
                busy={busy}
                onAssign={who => act(() => apiFetch(`/api/work-orders/${sel.order_id}/assign`, { method: 'PATCH', body: JSON.stringify({ assignee: who || null }) }))}
              />
            )}
          </div>
        )}
      </Drawer>

      {confirm && (
        <ConfirmDialog
          open
          title={`${STEP[confirm.step].label} work order`}
          description={
            <>
              <p>
                <strong>{confirm.order.machine_id}</strong>: {confirm.order.action}
              </p>
              <p>{STEP[confirm.step].text}</p>
            </>
          }
          confirmLabel={STEP[confirm.step].label}
          danger={STEP[confirm.step].danger}
          requireReason={STEP[confirm.step].reason}
          busy={busy}
          onCancel={() => setConfirm(null)}
          onConfirm={reason => act(() => STEP[confirm.step].call(confirm.order.order_id, reason))}
        />
      )}

      {creating && canAct && (
        <CreateDialog
          machine={params.get('machine') ?? ''}
          domain={params.get('domain')}
          alarm={params.get('alarm')}
          action={params.get('action') ?? ''}
          urgency={(URGENCIES as string[]).includes(params.get('urgency') ?? '') ? (params.get('urgency') as Urgency) : 'Medium'}
          onClose={closeCreate}
          onCreated={() => {
            setParams({ status: 'Pending Approval' });
            poll.reload();
          }}
        />
      )}
    </Page>
  );
}

function AssignField({ order, users, busy, onAssign }: { order: WorkOrder; users: { username: string; role: string }[]; busy: boolean; onAssign: (who: string) => void }) {
  const [who, setWho] = useState(order.assignee ?? '');
  const id = useId();
  return (
    <div className="ax-row">
      <label className="ax-field" htmlFor={id} style={{ flex: 1 }}>
        <span className="ax-field__label">Assignee</span>
        <select id={id} className="ax-input" value={who} onChange={e => setWho(e.target.value)}>
          <option value="">Unassigned</option>
          {users.map(u => (
            <option key={u.username} value={u.username}>
              {u.username} ({u.role})
            </option>
          ))}
        </select>
      </label>
      <Button disabled={busy || who === (order.assignee ?? '')} onClick={() => onAssign(who)} style={{ alignSelf: 'end' }}>
        Assign
      </Button>
    </div>
  );
}

function CreateDialog(props: { machine: string; domain: string | null; alarm: string | null; action: string; urgency: Urgency; onClose: () => void; onCreated: () => void }) {
  const { machine, domain, alarm, onClose, onCreated } = props;
  const [form, setForm] = useState({ machine_id: machine, action: props.action, urgency: props.urgency, notes: '' });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const ids = { m: useId(), a: useId(), u: useId(), n: useId() };
  const ok = /^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$/.test(form.machine_id) && form.action.trim().length >= 3;
  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      await createWorkOrder({ ...form, action: form.action.trim(), notes: form.notes.trim() || undefined, domain, alarm_id: alarm ? Number(alarm) : undefined });
      onCreated();
    } catch (e) {
      setError(errorMessage(e));
      setBusy(false);
    }
  };
  return (
    <Modal
      open
      onClose={onClose}
      title="New work order"
      footer={
        <>
          <Button onClick={onClose}>Cancel</Button>
          <Button variant="primary" disabled={!ok || busy} onClick={submit}>
            {busy ? 'Creating' : 'Create, pending approval'}
          </Button>
        </>
      }
    >
      <div className="ax-form">
        {alarm && <p className="ax-note">Linked to alarm {alarm}.</p>}
        <label className="ax-field" htmlFor={ids.m}>
          <span className="ax-field__label">Asset</span>
          <input id={ids.m} className="ax-input" value={form.machine_id} onChange={e => setForm({ ...form, machine_id: e.target.value })} required />
        </label>
        <label className="ax-field" htmlFor={ids.a}>
          <span className="ax-field__label">Action</span>
          <input id={ids.a} className="ax-input" value={form.action} autoFocus onChange={e => setForm({ ...form, action: e.target.value })} placeholder="e.g. Borescope the HPT stage" required />
        </label>
        <label className="ax-field" htmlFor={ids.u}>
          <span className="ax-field__label">Urgency</span>
          <select id={ids.u} className="ax-input" value={form.urgency} onChange={e => setForm({ ...form, urgency: e.target.value as Urgency })}>
            {URGENCIES.map(u => (
              <option key={u}>{u}</option>
            ))}
          </select>
        </label>
        <label className="ax-field" htmlFor={ids.n}>
          <span className="ax-field__label">Notes</span>
          <textarea id={ids.n} className="ax-input" value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} />
        </label>
        {error && (
          <p className="ax-error" role="alert">
            {error}
          </p>
        )}
      </div>
    </Modal>
  );
}
