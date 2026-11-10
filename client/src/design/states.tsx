import type { ReactNode } from 'react';
import { CircleAlert, Clock3, Inbox, RefreshCw, WifiOff } from 'lucide-react';

import { formatAge } from './format';
import { Button } from './primitives';

export function EmptyState({ title, body, action, icon }: { title: string; body?: ReactNode; action?: ReactNode; icon?: ReactNode }) {
  return (
    <div className="ax-state">
      {icon ?? <Inbox className="ax-state__icon" aria-hidden />}
      <h3>{title}</h3>
      {body && <p>{body}</p>}
      {action}
    </div>
  );
}

/** Names the problem and the recovery. Shows the raw error for operators who report it. */
export function ErrorState({ title = 'This view could not load', error, onRetry }: { title?: string; error: unknown; onRetry?: () => void }) {
  const detail = error instanceof Error ? error.message : String(error);
  return (
    <div className="ax-state" data-tone="error" role="alert">
      <CircleAlert className="ax-state__icon" aria-hidden />
      <h3>{title}</h3>
      <p>Check that the ATLAS server is running, then try again.</p>
      <code>{detail}</code>
      {onRetry && (
        <Button icon={<RefreshCw aria-hidden />} onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}

export function Skeleton({ width = '100%', height = '1rem', label = 'Loading' }: { width?: string; height?: string; label?: string }) {
  return <span className="ax-skeleton" style={{ width, height }} role="status" aria-label={label} />;
}

export function SkeletonRows({ rows = 5 }: { rows?: number }) {
  return (
    <div style={{ display: 'grid', gap: '0.5rem', padding: '1rem' }} role="status" aria-label="Loading">
      {Array.from({ length: rows }, (_, i) => (
        <span key={i} className="ax-skeleton" style={{ height: '1.75rem', width: `${100 - (i % 3) * 8}%` }} aria-hidden />
      ))}
    </div>
  );
}

/** Data older than its expected refresh: values stay visible but greyed, with this notice on top. */
export function StaleNotice({ lastUpdate }: { lastUpdate: string | number | Date }) {
  return (
    <div className="ax-notice" data-tone="stale" role="status">
      <Clock3 aria-hidden />
      <span>
        Data is stale. Last update <span className="num">{formatAge(lastUpdate)}</span>. Values below may not reflect the machine now.
      </span>
    </div>
  );
}

export function OfflineNotice() {
  return (
    <div className="ax-notice" data-tone="offline" role="alert">
      <WifiOff aria-hidden />
      <span>Connection lost. Showing the last values received; nothing updates until the connection returns.</span>
    </div>
  );
}
