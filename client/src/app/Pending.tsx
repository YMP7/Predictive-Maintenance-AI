import { Link } from 'react-router';
import { MapPinOff } from 'lucide-react';

import { Page } from '../design/shell';
import { EmptyState } from '../design/states';

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
