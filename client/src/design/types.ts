// Shared vocabulary for the design system. Values match the backend payloads (P2).

/** ISA-18.2 alarm priority. */
export type AlarmPriority = 'critical' | 'high' | 'medium' | 'low' | 'info';

/** ISA-18.2 alarm state. `rtn_unack` = returned to normal but not yet acknowledged. */
export type AlarmState = 'unack' | 'ack' | 'rtn_unack' | 'shelved' | 'suppressed' | 'cleared';

/** Quality flag carried by every live value. */
export type DataQuality = 'GOOD' | 'STALE' | 'OUT_OF_RANGE' | 'FLATLINE' | 'MISSING' | 'SIMULATED';

export type Role = 'admin' | 'operator' | 'viewer';

export const PRIORITY_ORDER: AlarmPriority[] = ['critical', 'high', 'medium', 'low', 'info'];

export const PRIORITY_LABEL: Record<AlarmPriority, string> = {
  critical: 'Critical',
  high: 'High',
  medium: 'Medium',
  low: 'Low',
  info: 'Info',
};

export const STATE_LABEL: Record<AlarmState, string> = {
  unack: 'Unacknowledged',
  ack: 'Acknowledged',
  rtn_unack: 'Cleared, unacknowledged',
  shelved: 'Shelved',
  suppressed: 'Suppressed',
  cleared: 'Cleared',
};

export const QUALITY_LABEL: Record<DataQuality, string> = {
  GOOD: 'Good',
  STALE: 'Stale',
  OUT_OF_RANGE: 'Out of range',
  FLATLINE: 'Flatline',
  MISSING: 'Missing',
  SIMULATED: 'Simulated',
};

/** Spoken description used for aria-labels and tooltips. */
export const QUALITY_HINT: Record<DataQuality, string> = {
  GOOD: 'Value is current and within its valid range',
  STALE: 'No update for more than 3 sampling intervals',
  OUT_OF_RANGE: 'Value is outside the channel’s valid range',
  FLATLINE: 'Value has not changed for an unusually long time',
  MISSING: 'No value received for this channel',
  SIMULATED: 'Value comes from a simulator, not a physical sensor',
};
