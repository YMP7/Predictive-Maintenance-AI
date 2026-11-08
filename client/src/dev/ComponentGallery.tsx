import { useState } from 'react';
import { CircleCheck, ShieldCheck } from 'lucide-react';

import type { Alarm } from '../design/alarmModel';
import { AlarmBanner, AlarmTable } from '../design/alarms';
import { DataTable, type Column } from '../design/DataTable';
import { KpiTile, LiveValue, Sparkline } from '../design/data';
import { ConfirmDialog, Drawer, Modal } from '../design/overlays';
import { Button, EvidenceLabel, PriorityGlyph, PriorityLabel, QualityBadge, SimBadge, StatusPill, Timestamp } from '../design/primitives';
import { Page } from '../design/shell';
import { EmptyState, ErrorState, OfflineNotice, Skeleton, SkeletonRows, StaleNotice } from '../design/states';
import { TrendChart, type TrendPoint } from '../design/TrendChart';
import { PRIORITY_ORDER, type AlarmState, type DataQuality } from '../design/types';

/* Dev-only gallery of every base component in every state. All values here are fixed
   sample values for review, labelled SYNTHETIC; none of them come from a machine. */

const T0 = Date.UTC(2026, 10, 8, 6, 30, 0); // fixed so screenshots are reproducible
const iso = (minAgo: number) => new Date(T0 - minAgo * 60000).toISOString();

const QUALITIES: DataQuality[] = ['GOOD', 'STALE', 'OUT_OF_RANGE', 'FLATLINE', 'MISSING', 'SIMULATED'];
const STATES: AlarmState[] = ['unack', 'ack', 'rtn_unack', 'shelved', 'suppressed', 'cleared'];

const ALARMS: Alarm[] = [
  { id: 'a1', priority: 'critical', state: 'unack', raisedAt: iso(2), assetId: 'cmapss/unit_34', assetName: 'Turbofan unit 34', message: 'RUL p10 below 15 cycles', value: '12.4 cyc' },
  { id: 'a2', priority: 'high', state: 'unack', raisedAt: iso(6), assetId: 'modbus/pump_1', assetName: 'Pump P-101', message: 'Drive-end bearing temperature above limit', value: '81.2 °C' },
  { id: 'a3', priority: 'medium', state: 'ack', raisedAt: iso(14), assetId: 'server/vm_1', assetName: 'Server VM 1', message: 'Disk usage above 90 %', value: '92.0 %' },
  { id: 'a4', priority: 'low', state: 'rtn_unack', raisedAt: iso(31), assetId: 'laptop/local', assetName: 'Laptop', message: 'CPU package temperature returned to normal', value: '64.0 °C' },
  { id: 'a5', priority: 'medium', state: 'shelved', raisedAt: iso(55), assetId: 'mobile/device_1', assetName: 'Phone 1', message: 'Battery temperature high while charging', value: '41.5 °C' },
  { id: 'a6', priority: 'info', state: 'cleared', raisedAt: iso(80), assetId: 'cmapss/unit_12', assetName: 'Turbofan unit 12', message: 'Model reloaded for C-MAPSS domain' },
];

function rulTrend(): TrendPoint[] {
  // Smooth deterministic decline with a widening band.
  return Array.from({ length: 60 }, (_, i) => {
    const v = 92 - i * 0.9 + Math.sin(i / 4) * 2;
    const w = 6 + i * 0.15;
    return { t: T0 - (59 - i) * 60000, v, lo: v - w, hi: v + w };
  });
}

interface Row {
  id: string;
  asset: string;
  domain: string;
  health: number;
  rul: number;
}
const DOMAINS = ['cmapss', 'laptop', 'mobile', 'server', 'modbus'];
const ROWS: Row[] = Array.from({ length: 1000 }, (_, i) => ({
  id: `r${i}`,
  asset: `Asset ${String(i + 1).padStart(4, '0')}`,
  domain: DOMAINS[i % 5],
  health: ((i * 37) % 100) / 100,
  rul: (i * 53) % 125,
}));
const COLUMNS: Column<Row>[] = [
  { key: 'asset', header: 'Asset', render: r => r.asset, sortValue: r => r.asset },
  { key: 'domain', header: 'Domain', render: r => r.domain, sortValue: r => r.domain },
  { key: 'health', header: 'Health index', align: 'right', render: r => r.health.toFixed(2), sortValue: r => r.health },
  { key: 'rul', header: 'RUL (cycles)', align: 'right', render: r => r.rul, sortValue: r => r.rul },
];
const trend = rulTrend();

export default function ComponentGallery() {
  const [drawer, setDrawer] = useState(false);
  const [modal, setModal] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const [lastReason, setLastReason] = useState('');

  return (
    <Page
      title="Component gallery"
      purpose="Every base component in every state. Development builds only. All values are fixed samples, not machine data."
      actions={<SimBadge kind="SYNTHETIC" />}
    >
      <div className="ax-gallery">
        <section className="ax-panel ax-panel__body">
          <h2>Alarm priority (ISA-18.2): shape, colour and word</h2>
          <div className="ax-gallery__row">
            {PRIORITY_ORDER.map(p => (
              <PriorityLabel key={p} priority={p} />
            ))}
          </div>
          <h2>Alarm states, shown for High priority</h2>
          <div className="ax-gallery__row">
            {STATES.map(s => (
              <span key={s} style={{ display: 'inline-flex', gap: '0.4rem', alignItems: 'center' }}>
                <PriorityGlyph priority="high" state={s} />
                <span style={{ fontSize: 'var(--text-sm)' }}>{s}</span>
              </span>
            ))}
          </div>
        </section>

        <section className="ax-panel ax-panel__body">
          <h2>Data quality on live values</h2>
          <div className="ax-gallery__row">
            {QUALITIES.map(q => (
              <QualityBadge key={q} quality={q} />
            ))}
          </div>
          <div className="ax-gallery__grid">
            {QUALITIES.map((q, i) => (
              <div key={q} className="ax-kpi">
                <LiveValue
                  label={`HPC outlet T30, ${q.toLowerCase().replace('_', ' ')}`}
                  value={q === 'MISSING' ? null : 1589.7 + i * 3.1}
                  unit="K"
                  digits={1}
                  quality={q}
                  trend={(['up', 'flat', 'up', 'flat', null, 'down'] as const)[i]}
                  ts={iso(i * 2)}
                />
              </div>
            ))}
          </div>
        </section>

        <section>
          <h2>KPI tiles</h2>
          <div className="ax-gallery__grid">
            <KpiTile label="Assets reporting" value={23} caption="of 25 registered" ts={iso(0)} />
            <KpiTile label="RUL at risk" value={3} priority="high" caption="p10 below 30 cycles" history={[1, 1, 2, 2, 2, 3, 3]} ts={iso(1)} />
            <KpiTile label="Unacknowledged critical" value={1} priority="critical" caption="oldest 2 min ago" ts={iso(0)} />
            <KpiTile label="Ingest rate" value={412} unit="msg/min" quality="SIMULATED" history={[380, 395, 401, 410, 407, 412]} ts={iso(0)} />
          </div>
        </section>

        <section className="ax-panel ax-panel__body">
          <h2>Sparkline and trend with uncertainty band</h2>
          <div className="ax-gallery__row">
            <Sparkline values={trend.map(p => p.v ?? 0)} band={{ lo: trend.map(p => p.lo ?? 0), hi: trend.map(p => p.hi ?? 0) }} width={180} height={36} label="RUL falling from 92 to 39 cycles" />
            <Sparkline values={[4, 4, 5, 7, 9, 12, 15]} tone="critical" width={120} label="Bearing temperature rising" />
          </div>
          <TrendChart
            data={trend}
            unit="cycles"
            seriesLabel="RUL mean"
            bandLabel="p10 to p90"
            thresholds={[{ value: 30, label: 'Plan maintenance', priority: 'medium' }, { value: 15, label: 'Critical', priority: 'critical' }]}
            summary="RUL mean falls from 92 to 39 cycles over 60 minutes; the p10 to p90 band widens from 12 to 30 cycles."
          />
        </section>

        <section>
          <h2>Alarm banner (flood indicator above 10 alarms in 10 min)</h2>
          <div className="ax-panel">
            <AlarmBanner alarms={ALARMS} onOpen={() => {}} now={T0} />
          </div>
          <div className="ax-panel">
            <AlarmBanner alarms={Array.from({ length: 12 }, (_, i) => ({ ...ALARMS[1], id: `f${i}`, raisedAt: iso(i / 2) }))} onOpen={() => {}} now={T0} />
          </div>
        </section>

        <section>
          <h2>Alarm table</h2>
          <AlarmTable alarms={ALARMS} actions={() => <Button size="sm">Acknowledge</Button>} />
        </section>

        <section>
          <h2>Data table: sort, filter, 1000 rows virtualised</h2>
          <DataTable rows={ROWS} columns={COLUMNS}rowKey={r => r.id} caption="Sample assets" filterPlaceholder="Filter assets" maxHeight="20rem" onRowActivate={() => setDrawer(true)} />
        </section>

        <section className="ax-panel ax-panel__body">
          <h2>Buttons, labels and overlays</h2>
          <div className="ax-gallery__row">
            <Button variant="primary" onClick={() => setConfirm(true)}>
              Approve work order
            </Button>
            <Button onClick={() => setDrawer(true)}>Open part detail</Button>
            <Button onClick={() => setModal(true)}>Open modal</Button>
            <Button variant="danger">Roll back model</Button>
            <Button disabled>Disabled</Button>
            <Button size="sm" variant="ghost">
              Small ghost
            </Button>
          </div>
          <div className="ax-gallery__row">
            <StatusPill tone="quiet">viewer</StatusPill>
            <StatusPill tone="accent">Selected</StatusPill>
            <StatusPill tone="critical">Critical</StatusPill>
            <StatusPill tone="high">Alarm flood</StatusPill>
            <StatusPill tone="medium">API unreachable</StatusPill>
            <StatusPill tone="low">Low</StatusPill>
            <SimBadge />
            <SimBadge kind="SYNTHETIC" />
            <EvidenceLabel kind="BUILD" />
            <EvidenceLabel kind="FUTURE-WORK" />
            <Timestamp value={T0} showZone />
          </div>
          {lastReason && (
            <p style={{ fontSize: 'var(--text-sm)', color: 'var(--ink-2)' }}>
              <CircleCheck width={14} height={14} aria-hidden /> Confirmed with reason: “{lastReason}”
            </p>
          )}
        </section>

        <section>
          <h2>States</h2>
          <div className="ax-panel">
            <StaleNotice lastUpdate={iso(4)} />
            <OfflineNotice />
          </div>
          <div className="ax-gallery__grid">
            <div className="ax-panel">
              <EmptyState title="No alarms" body="Nothing needs attention. New alarms appear here and in the banner." icon={<ShieldCheck className="ax-state__icon" aria-hidden />} />
            </div>
            <div className="ax-panel">
              <ErrorState error={new Error('API error 503: database unavailable')} onRetry={() => {}} />
            </div>
            <div className="ax-panel ax-panel__body" style={{ display: 'grid', gap: '0.5rem' }}>
              <Skeleton width="40%" />
              <Skeleton height="2rem" />
              <SkeletonRows rows={3} />
            </div>
          </div>
        </section>
      </div>

      <Drawer open={drawer} onClose={() => setDrawer(false)} title="High-pressure turbine">
        <LiveValue label="Part health" value={0.42} digits={2} quality="GOOD" ts={iso(0)} size="lg" />
        <LiveValue label="HPT coolant bleed W31" value={38.9} unit="lbm/s" digits={1} quality="GOOD" trend="down" ts={iso(0)} />
        <LiveValue label="Physical core speed Nc" value={9065} unit="rpm" digits={0} quality="STALE" ts={iso(5)} />
        <p>Contributing sensors and AMKB citations appear here in P3.</p>
      </Drawer>
      <Modal open={modal} onClose={() => setModal(false)} title="Plain modal" footer={<Button onClick={() => setModal(false)}>Close</Button>}>
        <p>Modals are for tasks that need protected focus. Esc and the backdrop close it.</p>
      </Modal>
      <ConfirmDialog
        open={confirm}
        title="Approve work order WO-0042?"
        description="Schedules maintenance on Turbofan unit 34. Your name and reason are recorded in the audit trail. You can still reject it later."
        confirmLabel="Approve"
        requireReason
        onCancel={() => setConfirm(false)}
        onConfirm={reason => {
          setLastReason(reason);
          setConfirm(false);
        }}
      />
    </Page>
  );
}
