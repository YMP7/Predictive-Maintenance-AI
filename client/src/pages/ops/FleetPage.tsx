import { Link } from 'react-router';

import { ACTIVE_STATES, isFlood } from '../../design/alarmModel';
import { formatPercent, formatValue } from '../../design/format';
import { useNow } from '../../design/hooks';
import { PriorityGlyph, PriorityLabel, QualityBadge, SimBadge, StatusPill, Timestamp } from '../../design/primitives';
import { Page } from '../../design/shell';
import { EmptyState } from '../../design/states';
import { PRIORITY_ORDER } from '../../design/types';
import { useSession } from '../../contexts/SessionContext';
import { useAlarms, type OpsAlarm } from '../../lib/ops';
import { usePoll } from '../../lib/usePoll';
import type { AssetSummary } from '../asset/types';
import { Polled } from './common';
import { DOMAIN_LABEL, STATUS_TONE } from './labels';

export interface FleetAsset extends AssetSummary {
  rul: { value: number; unit: string; uncertainty: number | null; normalized: number | null } | null;
  ts: string | null;
}

interface Device {
  device_id: string;
  machine_id: string;
  protocol: string;
  last_seen: string | null;
  revoked_at: string | null;
  messages_per_min: number;
  error_rate: number;
}

const assetHref = (a: AssetSummary) => `/assets/${a.domain}/${encodeURIComponent(a.machine_id)}`;
/** Normalised RUL below this share of the model's cap counts as at risk. */
const AT_RISK = 0.3;

export default function FleetPage() {
  const assets = usePoll<{ assets: FleetAsset[] }>('/api/assets', 5000);
  const alarms = useAlarms(10_000);
  const user = useSession();
  return (
    <Page title="Fleet overview" purpose="Every asset across all machine types, ranked by what needs attention.">
      <div className="ax-grid">
        <section className="ax-panel" aria-labelledby="fleet-alarms">
          <div className="ax-panel__head">
            <h2 id="fleet-alarms">Alarms needing action</h2>
            <Link to="/alarms">All alarms</Link>
          </div>
          <Polled poll={alarms} rows={3}>
            {() => <AlarmSummary alarms={alarms.alarms ?? []} />}
          </Polled>
        </section>
        <section className="ax-panel" aria-labelledby="fleet-rul">
          <div className="ax-panel__head">
            <h2 id="fleet-rul">Remaining useful life at risk</h2>
          </div>
          <Polled poll={assets} rows={4}>
            {d => <RulAtRisk assets={d.assets} />}
          </Polled>
        </section>
      </div>

      <section className="ax-panel" aria-labelledby="fleet-health">
        <div className="ax-panel__head">
          <h2 id="fleet-health">Health of every asset</h2>
          <span className="ax-note">Worst first. Health index: 0 % is fresh, 100 % is at its limit.</span>
        </div>
        <Polled poll={assets} rows={6}>
          {d => <HealthGrid assets={d.assets} />}
        </Polled>
      </section>

      {user.role === 'admin' && <IngestionHealth />}
    </Page>
  );
}

function AlarmSummary({ alarms }: { alarms: OpsAlarm[] }) {
  const now = useNow(30_000);
  const active = alarms.filter(a => ACTIVE_STATES.includes(a.state));
  const needsAck = active.filter(a => a.state !== 'ack').sort((a, b) => PRIORITY_ORDER.indexOf(a.priority) - PRIORITY_ORDER.indexOf(b.priority) || b.raisedAt.localeCompare(a.raisedAt));
  const shelved = alarms.filter(a => a.state === 'shelved').length;
  const flood = isFlood(alarms, now.getTime());
  if (!active.length) return <EmptyState title="No active alarms" body={shelved ? `${shelved} shelved.` : 'Nothing needs acknowledging.'} />;
  return (
    <div className="ax-panel__body ax-stack">
      <div className="ax-row" aria-label="Unacknowledged alarms by priority">
        {PRIORITY_ORDER.map(p => {
          const n = needsAck.filter(a => a.priority === p).length;
          return n ? (
            <span key={p} className="ax-row">
              <PriorityGlyph priority={p} />
              <span className="num">{n}</span> {p}
            </span>
          ) : null;
        })}
        {flood && <StatusPill tone="high">Alarm flood</StatusPill>}
      </div>
      <ul className="ax-list">
        {needsAck.slice(0, 5).map(a => (
          <li key={a.id}>
            <PriorityLabel priority={a.priority} state={a.state} />
            <span>
              <strong>{a.assetName}</strong> {a.message}
            </span>
            <span className="num ax-note">
              <Timestamp value={a.raisedAt} />
            </span>
          </li>
        ))}
      </ul>
      <p className="ax-note">
        {needsAck.length}
        {alarms.length >= 500 ? '+' : ''} unacknowledged, {active.length - needsAck.length} acknowledged, {shelved} shelved{alarms.length >= 500 ? ' (newest 500 alarms counted)' : ''}.
      </p>
    </div>
  );
}

function RulAtRisk({ assets }: { assets: FleetAsset[] }) {
  const ranked = assets.filter(a => a.rul && a.rul.normalized !== null).sort((a, b) => a.rul!.normalized! - b.rul!.normalized!);
  if (!ranked.length) return <EmptyState title="No RUL predictions yet" body="Predictions appear once a machine with a trained model has 30 readings." />;
  const atRisk = ranked.filter(a => a.rul!.normalized! < AT_RISK);
  const shown = atRisk.length ? atRisk : ranked.slice(0, 5);
  return (
    <>
      <p className="ax-note" style={{ padding: 'var(--space-3) var(--space-4) 0' }}>
        {atRisk.length
          ? `${atRisk.length} of ${ranked.length} predicted assets are below ${formatPercent(AT_RISK)} of their model's RUL cap.`
          : `None of ${ranked.length} predicted assets is below ${formatPercent(AT_RISK)} of its RUL cap. Lowest five:`}
      </p>
      <ul className="ax-list">
        {shown.slice(0, 8).map(a => (
          <li key={`${a.domain}/${a.machine_id}`}>
            <Link to={assetHref(a)}>{a.machine_id}</Link>
            <span className="ax-note">{DOMAIN_LABEL[a.domain] ?? a.domain}</span>
            <span className="num">
              {formatValue(a.rul!.value, a.rul!.unit, 0)}
              {a.rul!.uncertainty !== null && ` ± ${a.rul!.uncertainty.toFixed(0)}`}
            </span>
          </li>
        ))}
      </ul>
    </>
  );
}

function HealthGrid({ assets }: { assets: FleetAsset[] }) {
  if (!assets.length) return <EmptyState title="No assets yet" body="Machines appear here once an adapter or device sends data." action={<Link to="/admin/onboarding">Onboard a sensor</Link>} />;
  const rank = (a: FleetAsset) => (STATUS_TONE[a.status ?? ''] === 'high' ? 0 : STATUS_TONE[a.status ?? ''] === 'medium' ? 1 : 2);
  const sorted = [...assets].sort((a, b) => rank(a) - rank(b) || (b.health_index ?? -1) - (a.health_index ?? -1));
  return (
    <ul className="ax-health">
      {sorted.map(a => (
        <li key={`${a.domain}/${a.machine_id}`}>
          <Link to={assetHref(a)} data-tone={STATUS_TONE[a.status ?? '']}>
            <strong>{a.machine_id}</strong>
            <span>{DOMAIN_LABEL[a.domain] ?? a.label}</span>
            <span className="ax-row">
              {a.status ?? 'No data'}
              {a.health_index !== null && <span className="num">· health {formatPercent(a.health_index)}</span>}
              {a.simulated && <SimBadge />}
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}

function IngestionHealth() {
  const devices = usePoll<Device[]>('/api/admin/devices', 10_000);
  return (
    <section className="ax-panel" aria-labelledby="fleet-ingest">
      <div className="ax-panel__head">
        <h2 id="fleet-ingest">Ingestion health</h2>
        <Link to="/admin/devices">Devices</Link>
      </div>
      <Polled poll={devices} rows={3}>
        {list =>
          list.length === 0 ? (
            <EmptyState title="No push devices" body="Domain adapters (C-MAPSS, laptop, phone, server) poll by themselves. Devices that push data appear here once onboarded." action={<Link to="/admin/onboarding">Onboard a sensor</Link>} />
          ) : (
            <ul className="ax-list">
              {list.map(d => (
                <li key={d.device_id}>
                  <strong>{d.machine_id}</strong>
                  <span className="ax-note">{d.protocol}</span>
                  {d.revoked_at ? <StatusPill tone="quiet">Revoked</StatusPill> : !d.last_seen ? <QualityBadge quality="MISSING" /> : null}
                  <span className="num">
                    {d.messages_per_min} msg/min · {formatPercent(d.error_rate, 1)} errors
                  </span>
                </li>
              ))}
            </ul>
          )
        }
      </Polled>
    </section>
  );
}
