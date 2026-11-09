// Payloads of the operations API (server/operations_api.py, backend_api work orders) and their mapping
// onto the design system's alarm model.
import type { Alarm } from '../design/alarmModel';
import type { AlarmPriority, AlarmState } from '../design/types';
import { apiFetch } from './api';
import { usePoll } from './usePoll';

export interface ApiAlarm {
  id: number;
  raised_at: string;
  machine_id: string;
  type: string | null;
  priority: string;
  message: string;
  fault_type: string | null;
  source: string | null;
  state: AlarmState;
  state_by: string | null;
  state_at: string | null;
  state_reason: string | null;
  shelved_until: string | null;
}

const PRIORITIES: AlarmPriority[] = ['critical', 'high', 'medium', 'low', 'info'];

export interface OpsAlarm extends Alarm {
  raw: ApiAlarm;
}

export function toAlarm(a: ApiAlarm): OpsAlarm {
  return {
    id: String(a.id),
    priority: PRIORITIES.includes(a.priority as AlarmPriority) ? (a.priority as AlarmPriority) : 'medium',
    state: a.state,
    raisedAt: a.raised_at,
    assetId: a.machine_id,
    assetName: a.machine_id,
    message: a.message,
    value: a.fault_type && a.fault_type !== 'Normal' ? a.fault_type : undefined,
    raw: a,
  };
}

/** Alarm list shared by the banner, Fleet and the Alarms page. */
export function useAlarms(intervalMs = 10_000, machineId?: string) {
  const q = machineId ? `&machine_id=${encodeURIComponent(machineId)}` : '';
  const poll = usePoll<{ alarms: ApiAlarm[] }>(`/api/alarms?limit=500${q}`, intervalMs);
  return { ...poll, alarms: poll.data?.alarms.map(toAlarm) ?? null };
}

export type AlarmAction = 'ack' | 'shelve' | 'unshelve' | 'clear';

export const alarmAction = (id: string, action: AlarmAction, body: { reason?: string; minutes?: number } = {}) =>
  apiFetch<ApiAlarm>(`/api/alarms/${id}/${action}`, { method: 'POST', body: JSON.stringify(body) });

export type WorkOrderStatus = 'Pending Approval' | 'Open' | 'In Progress' | 'Resolved' | 'Rejected';
export type Urgency = 'Low' | 'Medium' | 'High' | 'Critical';

export interface WorkOrder {
  order_id: string;
  machine_id: string;
  domain: string | null;
  action: string;
  urgency: Urgency;
  status: WorkOrderStatus;
  created_at: string;
  resolved_at: string | null;
  updated_at: string | null;
  notes: string | null;
  created_by: string | null;
  assignee: string | null;
  alarm_id: number | null;
}

export const URGENCY_TONE: Record<Urgency, AlarmPriority> = { Critical: 'critical', High: 'high', Medium: 'medium', Low: 'low' };

export interface NewWorkOrder {
  machine_id: string;
  domain?: string | null;
  action: string;
  urgency: Urgency;
  notes?: string;
  alarm_id?: number;
}

export const createWorkOrder = (body: NewWorkOrder) =>
  apiFetch<WorkOrder>('/api/work-orders', { method: 'POST', body: JSON.stringify(body) });

/** Link that opens the Work Orders page with the create form filled in for this machine (and alarm). */
export function workOrderHref(machineId: string, domain?: string | null, alarmId?: number, prefill?: { action: string; urgency: Urgency }) {
  const p = new URLSearchParams({ new: '1', machine: machineId });
  if (domain) p.set('domain', domain);
  if (alarmId !== undefined) p.set('alarm', String(alarmId));
  if (prefill) {
    p.set('action', prefill.action);
    p.set('urgency', prefill.urgency);
  }
  return `/work-orders?${p}`;
}
