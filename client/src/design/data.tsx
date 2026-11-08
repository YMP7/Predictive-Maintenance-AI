import React, { useId } from 'react';
import { ArrowDownRight, ArrowRight, ArrowUpRight } from 'lucide-react';

import { formatAge, formatValue } from './format';
import { PriorityGlyph, QualityBadge, Timestamp } from './primitives';
import type { AlarmPriority, DataQuality } from './types';

export type Trend = 'up' | 'down' | 'flat';

const TREND_ICON: Record<Trend, React.ReactNode> = {
  up: <ArrowUpRight aria-hidden />,
  down: <ArrowDownRight aria-hidden />,
  flat: <ArrowRight aria-hidden />,
};
const TREND_WORD: Record<Trend, string> = { up: 'rising', down: 'falling', flat: 'steady' };

export interface LiveValueProps {
  label: string;
  value: number | null | undefined;
  unit?: string;
  digits?: number;
  quality: DataQuality;
  trend?: Trend | null;
  /** ISO time of the sample. */
  ts?: string | number | Date;
  /** Show "12 s ago" instead of the clock time. */
  relative?: boolean;
  size?: 'sm' | 'md' | 'lg';
  /** Hide the visible label when a surrounding heading already names the value (it stays for screen readers). */
  showLabel?: boolean;
}

/** A ledger line: value + SI unit + quality + trend + time. Never a bare number. */
export function LiveValue({ label, value, unit = '', digits = 2, quality, trend, ts, relative, size = 'md', showLabel = true }: LiveValueProps) {
  const text = quality === 'MISSING' ? '--' : formatValue(value, '', digits);
  return (
    <div className="ax-live" data-size={size} data-q={quality} data-nolabel={showLabel ? undefined : ''}>
      <span className={showLabel ? 'ax-live__label' : 'ax-live__label visually-hidden'}>{label}</span>
      <span className="ax-live__quality">
        <QualityBadge quality={quality} />
      </span>
      <span className="ax-live__value">
        <span className="num">{text}</span>
        {unit && <span className="ax-live__unit">{unit}</span>}
        {trend && (
          <span className="ax-live__trend" title={TREND_WORD[trend]}>
            {TREND_ICON[trend]}
            <span className="visually-hidden">{TREND_WORD[trend]}</span>
          </span>
        )}
      </span>
      {ts !== undefined && (
        <span className="ax-live__meta">{relative ? <span className="num">{formatAge(ts)}</span> : <Timestamp value={ts} style="time" showZone />}</span>
      )}
    </div>
  );
}

/* ---------- Sparkline ---------- */

export interface SparklineProps {
  values: number[];
  /** Optional p10/p90 band, same length as values. */
  band?: { lo: number[]; hi: number[] };
  width?: number;
  height?: number;
  tone?: 'default' | 'critical' | 'high';
  /** Spoken summary, e.g. "RUL falling from 120 to 84 cycles over 30 samples". */
  label: string;
}

export function Sparkline({ values, band, width = 120, height = 28, tone = 'default', label }: SparklineProps) {
  if (values.length < 2) return <svg className="ax-spark" width={width} height={height} role="img" aria-label={`${label}: not enough data`} />;
  const all = band ? [...values, ...band.lo, ...band.hi] : values;
  const min = Math.min(...all);
  const max = Math.max(...all);
  const span = max - min || 1;
  const pad = 2;
  const x = (i: number) => pad + (i / (values.length - 1)) * (width - pad * 2);
  const y = (v: number) => pad + (1 - (v - min) / span) * (height - pad * 2);
  const line = values.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join('');
  const area = band
    ? band.hi.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join('') +
      band.lo
        .map((v, i) => [i, v] as const)
        .reverse()
        .map(([i, v]) => `L${x(i).toFixed(1)},${y(v).toFixed(1)}`)
        .join('') +
      'Z'
    : null;
  const last = values.length - 1;
  return (
    <svg className="ax-spark" data-tone={tone} width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={label}>
      {area && <path className="ax-spark__band" d={area} />}
      <path className="ax-spark__line" d={line} />
      <circle className="ax-spark__last" cx={x(last)} cy={y(values[last])} r={2} />
    </svg>
  );
}

/* ---------- KPI tile ---------- */

export interface KpiTileProps {
  label: string;
  value: number | null | undefined;
  unit?: string;
  digits?: number;
  quality?: DataQuality;
  /** Priority when this KPI is in an abnormal state; omitted when normal. */
  priority?: AlarmPriority;
  caption?: React.ReactNode;
  history?: number[];
  ts?: string | number | Date;
  badge?: React.ReactNode;
}

export function KpiTile({ label, value, unit, digits = 0, quality = 'GOOD', priority, caption, history, ts, badge }: KpiTileProps) {
  const id = useId();
  const tone = priority === 'critical' || priority === 'high' ? priority : undefined;
  return (
    <section className="ax-kpi" data-tone={tone} aria-labelledby={id}>
      <div className="ax-kpi__head">
        <span id={id}>{label}</span>
        <span style={{ display: 'inline-flex', gap: '0.375rem', alignItems: 'center' }}>
          {badge}
          {priority && <PriorityGlyph priority={priority} />}
        </span>
      </div>
      <LiveValue label={label} value={value} unit={unit} digits={digits} quality={quality} ts={ts} relative size="lg" showLabel={false} />
      {(caption || history) && (
        <div className="ax-kpi__foot">
          <span>{caption}</span>
          {history && history.length > 1 && <Sparkline values={history} tone={tone} label={`${label} history, ${history.length} samples`} />}
        </div>
      )}
    </section>
  );
}
