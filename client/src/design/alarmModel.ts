import { PRIORITY_ORDER, type AlarmPriority, type AlarmState } from './types';

export interface Alarm {
  id: string;
  priority: AlarmPriority;
  state: AlarmState;
  /** ISO time the alarm was raised. */
  raisedAt: string;
  assetId: string;
  assetName: string;
  message: string;
  value?: string;
}

/** States that still need an operator's attention. */
export const ACTIVE_STATES: AlarmState[] = ['unack', 'ack', 'rtn_unack'];

export const priorityRank = (p: AlarmPriority) => PRIORITY_ORDER.indexOf(p);

/** ISA-18.2 flood: more than 10 alarms in 10 minutes for one operator. */
export const FLOOD_THRESHOLD = 10;
export const FLOOD_WINDOW_MS = 10 * 60 * 1000;

export function isFlood(alarms: Alarm[], now: number): boolean {
  return alarms.filter(a => now - new Date(a.raisedAt).getTime() <= FLOOD_WINDOW_MS).length > FLOOD_THRESHOLD;
}
