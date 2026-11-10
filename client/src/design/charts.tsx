// Small SVG charts for the Cognition Dashboard (P5). Each one shows the hovered value in a readout line and
// carries a table view, so no value depends on hovering. Colours come from the --viz-* tokens (validated pair).
import { useState, type ReactNode } from 'react';

const fmt = (v: number, digits = 3) => (Math.abs(v) >= 1000 ? v.toFixed(0) : v.toFixed(digits));

function Figure({ label, readout, table, children }: { label: string; readout: string | null; table: [string, string][]; children: ReactNode }) {
  return (
    <figure className="ax-viz" aria-label={label}>
      {children}
      <figcaption className="ax-viz__readout num" aria-live="polite">
        {readout ?? ' '}
      </figcaption>
      <details className="ax-viz__table">
        <summary>Values</summary>
        <table className="ax-table">
          <tbody>
            {table.map(([k, v], i) => (
              <tr key={i}>
                <th scope="row">{k}</th>
                <td className="num">{v}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </figure>
  );
}

/** Diverging colour for v in [-1, 1]: brown above zero, blue below, grey at zero. */
function diverging(v: number) {
  const t = Math.min(1, Math.abs(v));
  const pole = v >= 0 ? 'var(--viz-pos)' : 'var(--viz-neg)';
  return `color-mix(in oklab, ${pole} ${Math.round(t * 100)}%, var(--viz-mid))`;
}

/** One cell per dimension, coloured by value on a symmetric diverging scale. */
export function HeatStrip({ values, label }: { values: number[]; label: string }) {
  const [hover, setHover] = useState<number | null>(null);
  const max = Math.max(1e-9, ...values.map(Math.abs));
  const w = 640;
  const cw = w / Math.max(1, values.length);
  return (
    <Figure label={label} readout={hover === null ? null : `dim ${hover}: ${fmt(values[hover])}`} table={values.map((v, i) => [`dim ${i}`, fmt(v)])}>
      <svg viewBox={`0 0 ${w} 40`} className="ax-viz__svg" role="img" aria-label={`${label}, ${values.length} values, colour scale symmetric around zero, maximum magnitude ${fmt(max)}`} onPointerLeave={() => setHover(null)}>
        {values.map((v, i) => (
          <rect key={i} x={i * cw + 1} y={2} width={cw - 2} height={28} rx={2} fill={diverging(v / max)} stroke={hover === i ? 'var(--ink)' : 'none'} onPointerEnter={() => setHover(i)} />
        ))}
        <text x={0} y={39} className="ax-viz__tick">0</text>
        <text x={w} y={39} textAnchor="end" className="ax-viz__tick">{values.length - 1}</text>
      </svg>
      <div className="ax-viz__legend" aria-hidden>
        <span><i style={{ background: 'var(--viz-neg)' }} /> negative</span>
        <span><i style={{ background: 'var(--viz-mid)' }} /> 0</span>
        <span><i style={{ background: 'var(--viz-pos)' }} /> positive (±{fmt(max, 2)})</span>
      </div>
    </Figure>
  );
}

/** Points in order joined by a trajectory line, equal scale on both axes; the newest point is ringed. */
export function Scatter({ points, labels, xLabel, yLabel, label }: { points: number[][]; labels: string[]; xLabel: string; yLabel: string; label: string }) {
  const [hover, setHover] = useState<number | null>(null);
  const W = 560;
  const H = 260;
  const P = 32;
  const xs = points.map(p => p[0]);
  const ys = points.map(p => p[1]);
  const [x0, x1] = [Math.min(...xs), Math.max(...xs)];
  const [y0, y1] = [Math.min(...ys), Math.max(...ys)];
  // One scale for both axes: a projection drawn with stretched axes overstates the minor component.
  const k = Math.min((W - 2 * P) / (x1 - x0 || 1), (H - 2 * P) / (y1 - y0 || 1));
  const cx = (x0 + x1) / 2;
  const cy = (y0 + y1) / 2;
  const sx = (x: number) => W / 2 + (x - cx) * k;
  const sy = (y: number) => H / 2 - (y - cy) * k;
  const last = points.length - 1;
  return (
    <Figure label={label} readout={hover === null ? null : `${labels[hover]}: (${fmt(points[hover][0], 2)}, ${fmt(points[hover][1], 2)})`} table={points.map((p, i) => [labels[i], `${fmt(p[0], 2)}, ${fmt(p[1], 2)}`])}>
      <svg viewBox={`0 0 ${W} ${H}`} className="ax-viz__svg" role="img" aria-label={`${label}: ${points.length} states, newest ringed`} onPointerLeave={() => setHover(null)}>
        <line x1={P} y1={H - P} x2={W - P} y2={H - P} className="ax-viz__axis" />
        <line x1={P} y1={P} x2={P} y2={H - P} className="ax-viz__axis" />
        <text x={W / 2} y={H - 6} textAnchor="middle" className="ax-viz__tick">{xLabel}</text>
        <text x={10} y={H / 2} textAnchor="middle" className="ax-viz__tick" transform={`rotate(-90 10 ${H / 2})`}>{yLabel}</text>
        <polyline points={points.map(p => `${sx(p[0])},${sy(p[1])}`).join(' ')} fill="none" stroke="var(--viz-quiet)" strokeWidth={2} />
        {points.map((p, i) => (
          <circle key={i} cx={sx(p[0])} cy={sy(p[1])} r={i === last ? 6 : 4} fill={i === last ? 'var(--viz-mark)' : 'var(--surface-raised)'} stroke="var(--viz-mark)" strokeWidth={2} onPointerEnter={() => setHover(i)} />
        ))}
        {points.length > 0 && <circle cx={sx(points[last][0])} cy={sy(points[last][1])} r={10} fill="none" stroke="var(--viz-mark)" strokeWidth={1} />}
      </svg>
    </Figure>
  );
}

/** Vertical bars from a zero line (signed values go below it). */
export function Bars({ values, labels, label, unit = '' }: { values: number[]; labels: string[]; label: string; unit?: string }) {
  const [hover, setHover] = useState<number | null>(null);
  const W = 640;
  const H = 140;
  const max = Math.max(1e-9, ...values.map(Math.abs));
  const signed = values.some(v => v < 0);
  const zero = signed ? H / 2 : H - 16;
  const span = signed ? H / 2 - 12 : H - 28;
  const bw = W / Math.max(1, values.length);
  return (
    <Figure label={label} readout={hover === null ? null : `${labels[hover]}: ${fmt(values[hover])} ${unit}`} table={values.map((v, i) => [labels[i], `${fmt(v)} ${unit}`])}>
      <svg viewBox={`0 0 ${W} ${H}`} className="ax-viz__svg" role="img" aria-label={`${label}, ${values.length} bars`} onPointerLeave={() => setHover(null)}>
        <line x1={0} x2={W} y1={zero} y2={zero} className="ax-viz__axis" />
        {values.map((v, i) => {
          const h = (Math.abs(v) / max) * span;
          return (
            <g key={i} onPointerEnter={() => setHover(i)}>
              <rect x={i * bw} y={0} width={bw} height={H} fill="transparent" />
              <rect x={i * bw + 2} y={v >= 0 ? zero - h : zero} width={bw - 4} height={Math.max(1, h)} rx={2} fill={signed ? (v >= 0 ? 'var(--viz-pos)' : 'var(--viz-neg)') : 'var(--viz-mark)'} opacity={hover === null || hover === i ? 1 : 0.55} />
            </g>
          );
        })}
      </svg>
    </Figure>
  );
}

/** Histogram with an optional marker line (e.g. RUL = 0, failure). */
export function Histogram({ edges, counts, label, unit, markAt, markLabel }: { edges: number[]; counts: number[]; label: string; unit: string; markAt?: number; markLabel?: string }) {
  const [hover, setHover] = useState<number | null>(null);
  const W = 560;
  const H = 180;
  const B = 18;
  const max = Math.max(1, ...counts);
  const [lo, hi] = [edges[0], edges[edges.length - 1]];
  const sx = (x: number) => ((x - lo) / (hi - lo || 1)) * W;
  const rows = counts.map((c, i): [string, string] => [`${fmt(edges[i], 1)} to ${fmt(edges[i + 1], 1)} ${unit}`, String(c)]);
  return (
    <Figure label={label} readout={hover === null ? null : `${rows[hover][0]}: ${counts[hover]} samples`} table={rows}>
      <svg viewBox={`0 0 ${W} ${H}`} className="ax-viz__svg" role="img" aria-label={`${label}, ${counts.length} bins from ${fmt(lo, 1)} to ${fmt(hi, 1)} ${unit}`} onPointerLeave={() => setHover(null)}>
        <line x1={0} x2={W} y1={H - B} y2={H - B} className="ax-viz__axis" />
        {counts.map((c, i) => {
          const h = (c / max) * (H - B - 8);
          return <rect key={i} x={sx(edges[i]) + 1} y={H - B - h} width={Math.max(1, sx(edges[i + 1]) - sx(edges[i]) - 2)} height={h} rx={2} fill="var(--viz-mark)" opacity={hover === null || hover === i ? 1 : 0.55} onPointerEnter={() => setHover(i)} />;
        })}
        {markAt !== undefined && markAt >= lo && markAt <= hi && (
          <>
            <line x1={sx(markAt)} x2={sx(markAt)} y1={4} y2={H - B} stroke="var(--ink-2)" strokeDasharray="3 3" />
            <text x={sx(markAt) + 4} y={12} className="ax-viz__tick">{markLabel}</text>
          </>
        )}
        <text x={0} y={H - 4} className="ax-viz__tick">{fmt(lo, 0)}</text>
        <text x={W} y={H - 4} textAnchor="end" className="ax-viz__tick">{fmt(hi, 0)} {unit}</text>
      </svg>
    </Figure>
  );
}

/** Horizontal bars with the value written beside each bar (stage latency). */
export function BarList({ rows, unit, label }: { rows: { label: string; value: number | null }[]; unit: string; label: string }) {
  const max = Math.max(1e-9, ...rows.map(r => r.value ?? 0));
  return (
    <ul className="ax-barlist" aria-label={label}>
      {rows.map(r => (
        <li key={r.label}>
          <span>{r.label}</span>
          <span className="ax-bar">
            <span style={{ width: `${((r.value ?? 0) / max) * 100}%`, background: 'var(--viz-mark)' }} />
          </span>
          <span className="num">{r.value === null ? 'n/a' : `${fmt(r.value, r.value < 10 ? 2 : 1)} ${unit}`}</span>
        </li>
      ))}
    </ul>
  );
}
