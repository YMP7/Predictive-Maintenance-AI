import { Link } from 'react-router';

import { formatPercent } from '../../design/format';
import { SimBadge } from '../../design/primitives';
import { Page } from '../../design/shell';
import { EmptyState } from '../../design/states';
import { usePoll } from '../../lib/usePoll';
import { Polled } from './common';
import { DOMAIN_LABEL, STATUS_TONE } from './labels';
import type { FleetAsset } from './FleetPage';

const mean = (xs: number[]) => (xs.length ? xs.reduce((s, x) => s + x, 0) / xs.length : null);

function Bar({ value, tone, label }: { value: number | null; tone?: string; label: string }) {
  if (value === null) return <span className="ax-note">no value</span>;
  return (
    <span className="ax-row" style={{ flexWrap: 'nowrap' }}>
      <span className="ax-bar" data-tone={tone} role="img" aria-label={`${label} ${formatPercent(value)}`}>
        <span style={{ width: `${Math.max(0, Math.min(1, value)) * 100}%` }} />
      </span>
      <span className="num">{formatPercent(value)}</span>
    </span>
  );
}

/** One pipeline across unlike machines: every domain on the same 0..1 scales. */
export default function CrossDomainPage() {
  const poll = usePoll<{ assets: FleetAsset[] }>('/api/assets', 5000);
  return (
    <Page title="Cross-domain view" purpose="The same adapter layer and cognition pipeline across a turbofan, a laptop, a phone, a server and a pump, on one normalised scale.">
      <Polled poll={poll} rows={6}>
        {({ assets }) => {
          const domains = [...new Set([...Object.keys(DOMAIN_LABEL), ...assets.map(a => a.domain)])];
          return (
            <div className="ax-stack">
              <section className="ax-panel" aria-labelledby="xd-metrics">
                <div className="ax-panel__head">
                  <h2 id="xd-metrics">Per-domain summary</h2>
                  <span className="ax-note">Health index: 0 % fresh, 100 % at limit. RUL: share of the model's cap, 100 % is a new machine.</span>
                </div>
                <div tabIndex={0} role="region" aria-label="Per-domain summary table" className="ax-table-scroll">
                  <table className="ax-table">
                    <caption className="visually-hidden">Assets, mean health and mean normalised RUL per domain</caption>
                    <thead>
                      <tr>
                        <th scope="col">Domain</th>
                        <th scope="col">Assets</th>
                        <th scope="col">Mean health index</th>
                        <th scope="col">Mean RUL (normalised)</th>
                        <th scope="col">Lowest RUL</th>
                        <th scope="col">Data</th>
                      </tr>
                    </thead>
                    <tbody>
                      {domains.map(d => {
                        const rows = assets.filter(a => a.domain === d);
                        const rul = rows.map(a => a.rul?.normalized).filter((x): x is number => x != null);
                        const health = rows.map(a => a.health_index).filter((x): x is number => x !== null);
                        const sim = rows.some(a => a.simulated);
                        return (
                          <tr key={d}>
                            <th scope="row">{DOMAIN_LABEL[d] ?? d}</th>
                            <td className="num">{rows.length}</td>
                            <td>{rows.length ? <Bar value={mean(health)} label="Mean health index" /> : <span className="ax-note">no assets</span>}</td>
                            <td>{rul.length ? <Bar value={mean(rul)} label="Mean RUL" /> : rows.length ? <span className="ax-note">waiting for 30 readings</span> : null}</td>
                            <td className="num">{rul.length ? formatPercent(Math.min(...rul)) : ''}</td>
                            <td>{sim ? <SimBadge /> : rows.length ? 'Measured or dataset' : ''}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
                <p className="ax-note" style={{ padding: 'var(--space-3) var(--space-4)' }}>
                  No RUL means the machine has not sent 30 readings yet, or its sensor profile does not match the trained model. C-MAPSS values replay the NASA FD001 training set; laptop, phone and server read live or simulated telemetry as badged; the pump's RUL model is trained on simulated run-to-failure data.
                </p>
              </section>

              <section className="ax-panel" aria-labelledby="xd-assets">
                <div className="ax-panel__head">
                  <h2 id="xd-assets">Every asset on the same scale</h2>
                </div>
                {assets.length === 0 ? (
                  <EmptyState title="No assets yet" body="Machines appear once an adapter or device sends data." />
                ) : (
                  <div tabIndex={0} role="region" aria-label="Every asset table" className="ax-table-scroll">
                    <table className="ax-table">
                      <caption className="visually-hidden">Normalised health and RUL for every asset</caption>
                      <thead>
                        <tr>
                          <th scope="col">Asset</th>
                          <th scope="col">Domain</th>
                          <th scope="col">Status</th>
                          <th scope="col">Health index</th>
                          <th scope="col">RUL (normalised)</th>
                        </tr>
                      </thead>
                      <tbody>
                        {assets.map(a => (
                          <tr key={`${a.domain}/${a.machine_id}`}>
                            <th scope="row">
                              <Link to={`/assets/${a.domain}/${encodeURIComponent(a.machine_id)}`}>{a.machine_id}</Link>
                            </th>
                            <td>{DOMAIN_LABEL[a.domain] ?? a.domain}</td>
                            <td>{a.status ?? 'No data'}</td>
                            <td>
                              <Bar value={a.health_index} tone={STATUS_TONE[a.status ?? '']} label="Health index" />
                            </td>
                            <td>{a.rul?.normalized != null ? <Bar value={a.rul.normalized} label="RUL" /> : <span className="ax-note">no model</span>}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </section>
            </div>
          );
        }}
      </Polled>
    </Page>
  );
}
