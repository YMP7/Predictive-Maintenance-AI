// Formatting for live values: time zone aware timestamps and SI numbers.

const TZ_KEY = 'atlas-tz';
export const DEFAULT_TZ = 'Asia/Kolkata';

export function getTimeZone(): string {
  try {
    return localStorage.getItem(TZ_KEY) || DEFAULT_TZ;
  } catch {
    return DEFAULT_TZ;
  }
}

export function setTimeZone(tz: string): void {
  try {
    localStorage.setItem(TZ_KEY, tz);
  } catch {
    // storage blocked: the default zone still applies
  }
}

/** Short zone label, e.g. "IST" or "GMT+5:30". */
export function zoneLabel(tz = getTimeZone(), at = new Date()): string {
  const part = new Intl.DateTimeFormat('en-GB', { timeZone: tz, timeZoneName: 'short' })
    .formatToParts(at)
    .find(p => p.type === 'timeZoneName');
  return part?.value ?? tz;
}

type TimeStyle = 'time' | 'datetime' | 'date';

export function formatTime(value: string | number | Date, style: TimeStyle = 'datetime', tz = getTimeZone()): string {
  const d = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(d.getTime())) return '--';
  const opts: Intl.DateTimeFormatOptions =
    style === 'time'
      ? { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }
      : style === 'date'
        ? { year: 'numeric', month: 'short', day: '2-digit' }
        : { year: 'numeric', month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false };
  return new Intl.DateTimeFormat('en-GB', { ...opts, timeZone: tz }).format(d);
}

/** "12 s ago", "4 min ago": for last-seen columns. */
export function formatAge(value: string | number | Date, now = Date.now()): string {
  const t = value instanceof Date ? value.getTime() : new Date(value).getTime();
  if (Number.isNaN(t)) return '--';
  const s = Math.max(0, Math.round((now - t) / 1000));
  if (s < 60) return `${s} s ago`;
  const m = Math.round(s / 60);
  if (m < 60) return `${m} min ago`;
  const h = Math.round(m / 60);
  if (h < 48) return `${h} h ago`;
  return `${Math.round(h / 24)} d ago`;
}

/** Thin space between a number and its SI unit (SI brochure style). */
const THIN = String.fromCharCode(0x2009);

/** Fixed-precision number with a thin space before the SI unit. `--` for missing values. */
export function formatValue(value: number | null | undefined, unit = '', digits = 2): string {
  if (value == null || !Number.isFinite(value)) return '--';
  const n = value.toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits });
  return unit ? `${n}${THIN}${unit}` : n;
}

export function formatPercent(fraction: number | null | undefined, digits = 0): string {
  if (fraction == null || !Number.isFinite(fraction)) return '--';
  return `${(fraction * 100).toFixed(digits)}${THIN}%`;
}
