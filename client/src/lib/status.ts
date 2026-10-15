// health_index from the adapters is a degradation score: 0 is healthy, 1 is failing
// (e.g. a C-MAPSS unit at 0.95 reports "Critical"). Colour it from the server's status
// label rather than re-deriving thresholds in the UI.
export function statusColor(status?: string): string {
  const s = (status ?? '').toLowerCase();
  if (s === 'critical') return 'var(--status-critical)';
  if (s === 'degrading' || s === 'warning') return 'var(--status-warning)';
  if (s === 'stable' || s === 'normal') return 'var(--status-normal)';
  return 'var(--text-muted)';
}

export function stressPercent(healthIndex?: number): string {
  return typeof healthIndex === 'number' ? `${Math.round(healthIndex * 100)}%` : '--';
}
