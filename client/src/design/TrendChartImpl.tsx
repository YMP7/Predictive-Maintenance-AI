import { Area, CartesianGrid, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import { formatTime, formatValue } from './format';

export interface TrendPoint {
  /** Epoch ms. */
  t: number;
  /** Central estimate (e.g. RUL mean or sensor value). */
  v: number | null;
  /** Optional uncertainty band, e.g. p10 / p90. */
  lo?: number | null;
  hi?: number | null;
}

export interface TrendChartProps {
  data: TrendPoint[];
  unit?: string;
  digits?: number;
  height?: number;
  /** Label for the central series, e.g. "RUL mean". */
  seriesLabel: string;
  /** Label for the band, e.g. "p10 to p90". */
  bandLabel?: string;
  /** Horizontal limits, e.g. an alarm threshold. */
  thresholds?: { value: number; label: string; priority?: 'critical' | 'high' | 'medium' | 'low' }[];
  /** Spoken summary for screen readers. */
  summary: string;
}

interface TipProps {
  // Injected by recharts:
  active?: boolean;
  label?: number;
  payload?: { payload: TrendPoint }[];
  // Ours:
  seriesLabel: string;
  bandLabel?: string;
  unit: string;
  digits: number;
}

function Tip({ active, label, payload, seriesLabel, bandLabel, unit, digits }: TipProps) {
  if (!active || !payload?.length || label == null) return null;
  const p = payload[0].payload;
  return (
    <div className="ax-tooltip">
      <strong className="num">{formatTime(label)}</strong>
      <dl>
        <dt>{seriesLabel}</dt>
        <dd className="num">{formatValue(p.v, unit, digits)}</dd>
        {p.lo != null && p.hi != null && (
          <>
            <dt>{bandLabel ?? 'Range'}</dt>
            <dd className="num">
              {formatValue(p.lo, '', digits)} to {formatValue(p.hi, unit, digits)}
            </dd>
          </>
        )}
      </dl>
    </div>
  );
}

export default function TrendChartImpl({ data, unit = '', digits = 1, height = 240, seriesLabel, bandLabel, thresholds = [], summary }: TrendChartProps) {
  const rows = data.map(p => ({ ...p, band: p.lo != null && p.hi != null ? [p.lo, p.hi] : null }));
  const hasBand = rows.some(r => r.band);

  return (
    <figure style={{ margin: 0, height }} aria-label={summary}>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={rows} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
          <CartesianGrid vertical={false} />
          <XAxis
            dataKey="t"
            type="number"
            scale="time"
            domain={['dataMin', 'dataMax']}
            tickFormatter={t => formatTime(t, 'time').slice(0, 5)}
            tickLine={false}
            axisLine={{ stroke: 'var(--line-strong)' }}
            minTickGap={40}
          />
          <YAxis width={48} tickLine={false} axisLine={false} tickFormatter={v => formatValue(v, '', 0)} />
          <Tooltip content={<Tip seriesLabel={seriesLabel} bandLabel={bandLabel} unit={unit} digits={digits} />} cursor={{ stroke: 'var(--line-strong)' }} isAnimationActive={false} />
          {hasBand && <Area dataKey="band" stroke="none" fill="var(--ink-2)" fillOpacity={0.12} isAnimationActive={false} />}
          {thresholds.map(th => (
            <ReferenceLine
              key={th.label}
              y={th.value}
              stroke={th.priority ? `var(--p-${th.priority})` : 'var(--line-strong)'}
              strokeDasharray="4 3"
              label={{ value: th.label, position: 'insideTopRight', fill: 'var(--ink-3)', fontSize: 11 }}
            />
          ))}
          <Line dataKey="v" stroke="var(--ink)" strokeWidth={1.5} dot={false} isAnimationActive={false} connectNulls={false} />
        </ComposedChart>
      </ResponsiveContainer>
      <figcaption className="visually-hidden">{summary}</figcaption>
    </figure>
  );
}
