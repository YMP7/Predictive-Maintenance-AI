import { lazy, Suspense } from 'react';

import type { TrendChartProps } from './TrendChartImpl';

// recharts is ~100 KB gzipped: load it only on screens that draw a trend.
const Impl = lazy(() => import('./TrendChartImpl'));

export type { TrendPoint, TrendChartProps } from './TrendChartImpl';

export function TrendChart(props: TrendChartProps) {
  const height = props.height ?? 240;
  return (
    <div className="ax-chart" style={{ height }}>
      <Suspense fallback={<span className="ax-skeleton" style={{ height }} aria-label="Loading chart" role="status" />}>
        <Impl {...props} />
      </Suspense>
    </div>
  );
}
