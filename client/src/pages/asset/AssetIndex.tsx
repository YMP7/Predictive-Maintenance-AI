import { useEffect, useState } from 'react';
import { Link, Navigate, useParams } from 'react-router';

import { formatPercent } from '../../design/format';
import { SimBadge, StatusPill } from '../../design/primitives';
import { Page } from '../../design/shell';
import { EmptyState, ErrorState, SkeletonRows } from '../../design/states';
import { apiFetch } from '../../lib/api';
import type { AssetSummary } from './types';

function useAssets() {
  const [assets, setAssets] = useState<AssetSummary[] | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [tick, setTick] = useState(0);
  useEffect(() => {
    const ctrl = new AbortController();
    apiFetch<{ assets: AssetSummary[] }>('/api/assets', { signal: ctrl.signal })
      .then(r => setAssets(r.assets))
      .catch(e => {
        if (!ctrl.signal.aborted) setError(e);
      });
    return () => ctrl.abort();
  }, [tick]);
  return { assets, error, retry: () => setTick(t => t + 1) };
}

const href = (a: AssetSummary) => `/assets/${a.domain}/${encodeURIComponent(a.machine_id)}`;
const tone = (status: string) => (status === 'Critical' ? 'high' : status === 'Degrading' ? 'medium' : 'quiet');

/** Every machine the 3D Asset View can show, grouped by machine type. */
export default function AssetIndex() {
  const { assets, error, retry } = useAssets();
  const kinds = [...new Set(assets?.map(a => a.label) ?? [])];
  return (
    <Page title="Assets" purpose="Pick a machine to open its 3D Asset View.">
      {error ? (
        <ErrorState error={error} onRetry={retry} />
      ) : !assets ? (
        <SkeletonRows rows={6} />
      ) : assets.length === 0 ? (
        <EmptyState title="No assets yet" body="Machines appear here once an adapter or device sends data." />
      ) : (
        kinds.map(kind => (
          <section key={kind} className="ax-panel">
            <div className="ax-panel__head">
              <h2>{kind}</h2>
            </div>
            <ul className="ax-asset__index">
              {assets
                .filter(a => a.label === kind)
                .map(a => (
                  <li key={`${a.domain}/${a.machine_id}`}>
                    <Link to={href(a)}>{a.machine_id}</Link>
                    <span className="num">{a.health_index === null ? '' : `health ${formatPercent(a.health_index)}`}</span>
                    <span className="ax-asset__badges">
                      {a.status && <StatusPill tone={tone(a.status)}>{a.status}</StatusPill>}
                      {a.simulated && <SimBadge />}
                    </span>
                  </li>
                ))}
            </ul>
          </section>
        ))
      )}
    </Page>
  );
}

/** /assets/kind/:kind opens the first asset of that machine type, so the kiosk tour can list types, not ids. */
export function AssetByKind() {
  const { kind } = useParams();
  const { assets, error, retry } = useAssets();
  if (error) {
    return (
      <Page title="Assets">
        <ErrorState error={error} onRetry={retry} />
      </Page>
    );
  }
  if (!assets) {
    return (
      <Page title="Assets">
        <SkeletonRows rows={3} />
      </Page>
    );
  }
  const first = assets.find(a => a.kind === kind);
  return <Navigate to={first ? href(first) : '/assets'} replace />;
}
