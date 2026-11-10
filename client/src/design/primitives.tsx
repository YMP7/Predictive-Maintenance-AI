import React from 'react';
import { Check, ChevronsUpDown, CircleSlash, Clock3, FlaskConical, Minus } from 'lucide-react';

import { formatTime, getTimeZone, zoneLabel } from './format';
import {
  PRIORITY_LABEL,
  QUALITY_HINT,
  QUALITY_LABEL,
  STATE_LABEL,
  type AlarmPriority,
  type AlarmState,
  type DataQuality,
} from './types';

/* ---------- Button ---------- */

type ButtonVariant = 'default' | 'primary' | 'danger' | 'ghost';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: 'md' | 'sm';
  icon?: React.ReactNode;
  /** Icon-only button: `label` becomes the accessible name. */
  iconOnly?: boolean;
  label?: string;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = 'default', size = 'md', icon, iconOnly, label, className, children, type = 'button', ...rest },
  ref,
) {
  const cls = [
    'ax-btn',
    variant !== 'default' && `ax-btn--${variant}`,
    size === 'sm' && 'ax-btn--sm',
    iconOnly && 'ax-btn--icon',
    className,
  ]
    .filter(Boolean)
    .join(' ');
  return (
    <button ref={ref} type={type} className={cls} aria-label={iconOnly ? label : undefined} title={iconOnly ? label : undefined} {...rest}>
      {icon}
      {!iconOnly && children}
    </button>
  );
});

/* ---------- StatusPill (square status label) ---------- */

export type Tone = AlarmPriority | 'accent' | 'sim' | 'quiet';

export function StatusPill({ tone = 'quiet', icon, children }: { tone?: Tone; icon?: React.ReactNode; children: React.ReactNode }) {
  return (
    <span className="ax-status" data-tone={tone === 'info' ? 'quiet' : tone}>
      {icon}
      {children}
    </span>
  );
}

/** Visible badge for anything synthetic or simulated (product rule: never unlabeled). */
export function SimBadge({ kind = 'SIMULATED' }: { kind?: 'SIMULATED' | 'SYNTHETIC' }) {
  return (
    <span className="ax-status" data-tone="sim" title={kind === 'SIMULATED' ? QUALITY_HINT.SIMULATED : 'Generated data, not measured'}>
      <FlaskConical aria-hidden />
      {kind}
    </span>
  );
}

/** BUILD / FUTURE-WORK evidence label. */
export function EvidenceLabel({ kind }: { kind: 'BUILD' | 'FUTURE-WORK' }) {
  return (
    <StatusPill tone={kind === 'BUILD' ? 'accent' : 'quiet'}>{kind}</StatusPill>
  );
}

/* ---------- PriorityGlyph (ISA-18.2: shape + colour, never colour alone) ---------- */

const GLYPH_PATH: Record<AlarmPriority, string> = {
  critical: 'M8 1 L15 8 L8 15 L1 8 Z', // diamond
  high: 'M8 1.5 L15 14.5 L1 14.5 Z', // triangle
  medium: 'M2 2 H14 V14 H2 Z', // square
  low: 'M8 1.5 A6.5 6.5 0 1 1 7.99 1.5 Z', // circle
  info: 'M8 1.5 A6.5 6.5 0 1 1 7.99 1.5 Z',
};

export function PriorityGlyph({
  priority,
  state = 'unack',
  title,
}: {
  priority: AlarmPriority;
  state?: AlarmState;
  title?: string;
}) {
  const muted = state === 'shelved' || state === 'suppressed' || state === 'cleared';
  const filled = state === 'unack' || state === 'rtn_unack';
  const color = muted ? 'var(--ink-3)' : `var(--p-${priority})`;
  const name = title ?? `${PRIORITY_LABEL[priority]} priority, ${STATE_LABEL[state].toLowerCase()}`;
  return (
    <svg className="ax-glyph" viewBox="0 0 16 16" role="img" aria-label={name} data-blink={state === 'unack' && priority !== 'info' ? '' : undefined}>
      <title>{name}</title>
      <path
        d={GLYPH_PATH[priority]}
        fill={filled ? color : 'none'}
        stroke={color}
        strokeWidth={1.5}
        strokeDasharray={muted && state !== 'cleared' ? '2 2' : undefined}
        strokeLinejoin="round"
      />
      {priority === 'info' && <path d="M8 7v4.5M8 4.6v.1" stroke={filled ? 'var(--surface-raised)' : color} strokeWidth={1.6} strokeLinecap="round" />}
      {state === 'cleared' && <path d="M5 8.2 7.1 10.3 11 6" fill="none" stroke={color} strokeWidth={1.5} strokeLinecap="round" />}
    </svg>
  );
}

export function PriorityLabel({ priority, state = 'unack' }: { priority: AlarmPriority; state?: AlarmState }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}>
      <PriorityGlyph priority={priority} state={state} />
      <span>{PRIORITY_LABEL[priority]}</span>
    </span>
  );
}

/* ---------- QualityBadge ---------- */

const QUALITY_ICON: Record<DataQuality, React.ReactNode> = {
  GOOD: <Check aria-hidden />,
  STALE: <Clock3 aria-hidden />,
  OUT_OF_RANGE: <ChevronsUpDown aria-hidden />,
  FLATLINE: <Minus aria-hidden />,
  MISSING: <CircleSlash aria-hidden />,
  SIMULATED: <FlaskConical aria-hidden />,
};

/** GOOD renders as a quiet check (normal is quiet); every other state shows its code. */
export function QualityBadge({ quality, compact = false }: { quality: DataQuality; compact?: boolean }) {
  const showCode = quality !== 'GOOD' && !compact;
  return (
    <span className="ax-quality" data-q={quality} title={QUALITY_HINT[quality]} aria-label={`Quality: ${QUALITY_LABEL[quality]}`} role="img">
      {QUALITY_ICON[quality]}
      {showCode && <span aria-hidden>{quality === 'OUT_OF_RANGE' ? 'RANGE' : quality === 'SIMULATED' ? 'SIM' : quality}</span>}
    </span>
  );
}

/* ---------- Timestamp ---------- */

export function Timestamp({
  value,
  style = 'datetime',
  showZone = false,
}: {
  value: string | number | Date;
  style?: 'time' | 'datetime' | 'date';
  showZone?: boolean;
}) {
  const d = value instanceof Date ? value : new Date(value);
  const tz = getTimeZone();
  const valid = !Number.isNaN(d.getTime());
  return (
    <time dateTime={valid ? d.toISOString() : undefined} title={valid ? `${d.toISOString()} (UTC)` : undefined}>
      {formatTime(d, style, tz)}
      {showZone && valid && ` ${zoneLabel(tz, d)}`}
    </time>
  );
}
