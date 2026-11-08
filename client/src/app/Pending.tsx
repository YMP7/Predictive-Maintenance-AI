import { Link } from 'react-router';
import { Construction, MapPinOff } from 'lucide-react';

import { Page } from '../design/shell';
import { EmptyState } from '../design/states';

/** Route skeleton for pages built in later phases. States plainly what will be here and when. */
export function Pending({ title, purpose, phase, builds }: { title: string; purpose: string; phase: string; builds: string[] }) {
  return (
    <Page title={title} purpose={purpose}>
      <div className="ax-panel">
        <EmptyState
          icon={<Construction className="ax-state__icon" aria-hidden />}
          title={`Built in phase ${phase}`}
          body={
            <>
              This route exists so links and role checks work now. It will show: {builds.join('; ')}. The previous dashboard is still available at{' '}
              <Link to="/legacy/dashboard">/legacy/dashboard</Link> until then.
            </>
          }
        />
      </div>
    </Page>
  );
}

export function NotFoundPage() {
  return (
    <Page title="Page not found">
      <div className="ax-panel">
        <EmptyState
          icon={<MapPinOff className="ax-state__icon" aria-hidden />}
          title="No page at this address"
          body="The link may be out of date. Use the navigation or press Ctrl K to find the page."
          action={<Link to="/fleet">Go to fleet overview</Link>}
        />
      </div>
    </Page>
  );
}
