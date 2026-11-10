import { useMemo, type ReactNode } from 'react';
import { BellRing, Waves } from 'lucide-react';

import { ACTIVE_STATES, isFlood, priorityRank as rank, type Alarm } from './alarmModel';
import { DataTable, type Column } from './DataTable';
import { Button, PriorityGlyph, PriorityLabel, StatusPill, Timestamp } from './primitives';
import { PRIORITY_ORDER, STATE_LABEL } from './types';

/** Shown under the header only while an alarm needs attention. Quiet (absent) otherwise.
    `now` comes from the caller's clock (useNow) so the flood window stays current. */
export function AlarmBanner({ alarms, onOpen, now }: { alarms: Alarm[]; onOpen?: () => void; now: number }) {
  const active = alarms.filter(a => ACTIVE_STATES.includes(a.state));
  const needsAck = active.filter(a => a.state !== 'ack');
  if (!needsAck.length) return null;
  const top = [...needsAck].sort((a, b) => rank(a.priority) - rank(b.priority) || b.raisedAt.localeCompare(a.raisedAt))[0];
  const counts = PRIORITY_ORDER.map(p => [p, needsAck.filter(a => a.priority === p).length] as const).filter(([, n]) => n > 0);
  const flood = isFlood(alarms, now);
  return (
    <div className="ax-alarm-banner" data-priority={top.priority} data-flood={flood ? '' : undefined} role="status" aria-live="polite">
      <PriorityGlyph priority={top.priority} state={top.state} />
      <p className="ax-alarm-banner__text">
        <strong>{top.assetName}</strong>: {top.message}{' '}
        <span className="num" style={{ color: 'var(--ink-3)' }}>
          <Timestamp value={top.raisedAt} style="time" />
        </span>
      </p>
      <span className="ax-alarm-banner__flood">
        <StatusPill tone="high" icon={<Waves aria-hidden />}>
          Alarm flood
        </StatusPill>
      </span>
      <span className="ax-alarm-banner__counts" aria-label={`${needsAck.length} alarms need acknowledgement`}>
        {counts.map(([p, n]) => (
          <span key={p}>
            <PriorityGlyph priority={p} />
            {n}
          </span>
        ))}
      </span>
      {onOpen && (
        <Button size="sm" icon={<BellRing aria-hidden />} onClick={onOpen}>
          Open alarms
        </Button>
      )}
    </div>
  );
}

export function AlarmTable<T extends Alarm>({
  alarms,
  actions,
  onSelect,
  selectedId,
}: {
  alarms: T[];
  /** Per-row controls (acknowledge, shelve). */
  actions?: (a: T) => ReactNode;
  onSelect?: (a: T) => void;
  selectedId?: string | null;
}) {
  const columns = useMemo<Column<T>[]>(() => {
    const cols: Column<T>[] = [
      { key: 'priority', header: 'Priority', width: '8rem', render: a => <PriorityLabel priority={a.priority} state={a.state} />, sortValue: a => rank(a.priority) },
      { key: 'state', header: 'State', width: '12rem', render: a => STATE_LABEL[a.state], sortValue: a => STATE_LABEL[a.state] },
      { key: 'raisedAt', header: 'Raised', width: '11rem', render: a => <Timestamp value={a.raisedAt} />, sortValue: a => a.raisedAt },
      { key: 'asset', header: 'Asset', width: '12rem', render: a => a.assetName, sortValue: a => a.assetName },
      { key: 'message', header: 'Condition', render: a => a.message, sortValue: a => a.message },
      { key: 'value', header: 'Value', align: 'right', width: '8rem', render: a => a.value ?? '--' },
    ];
    if (actions) cols.push({ key: 'actions', header: 'Actions', width: '12rem', render: actions });
    return cols;
  }, [actions]);

  return (
    <DataTable
      rows={alarms}
      columns={columns}
      rowKey={a => a.id}
      caption="Alarms, highest priority first"
      filterPlaceholder="Filter alarms"
      initialSort={{ key: 'priority', dir: 'asc' }}
      onRowActivate={onSelect}
      selectedKey={selectedId}
      rowTone={a => (a.state === 'unack' && a.priority !== 'low' && a.priority !== 'info' ? a.priority : undefined) as 'critical' | 'high' | 'medium' | undefined}
    />
  );
}
