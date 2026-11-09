import type { ReactNode } from 'react';

import { ErrorState, SkeletonRows, StaleNotice } from '../../design/states';
import type { Poll } from '../../lib/usePoll';

/** Loading, error and stale states for one polled source. Offline is shown by the shell for every page. */
export function Polled<T>({ poll, rows = 5, title, children }: { poll: Poll<T>; rows?: number; title?: string; children: (data: T) => ReactNode }) {
  if (poll.error && poll.data === null) return <ErrorState title={title} error={poll.error} onRetry={poll.reload} />;
  if (poll.data === null) return <SkeletonRows rows={rows} />;
  return (
    <>
      {(poll.stale || poll.error) && poll.updatedAt !== null ? <StaleNotice lastUpdate={poll.updatedAt} /> : null}
      {children(poll.data)}
    </>
  );
}
