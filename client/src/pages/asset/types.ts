import type { DataQuality } from '../../design/types';
import type { PartState } from '../../teardown/view';

/** Mirrors server/asset_view.py build_frame(). */
export interface FrameChannel {
  feature: string;
  label: string;
  part: string;
  dir: number;
  value: number | null;
  raw: number | null;
  unit: string | null;
  quality: DataQuality;
  load: number | null;
}

export interface FramePart {
  id: string;
  name: string;
  detail: string;
  channels: string[];
  load: number | null;
  state: PartState;
}

export interface TwinFrame {
  domain: string;
  machine_id: string;
  kind: string;
  label: string;
  ts: string | null;
  status: string | null;
  adapter_status: string | null;
  simulated: boolean;
  health_index: number | null;
  rul: { value: number; unit: string; uncertainty: number | null; normalized: number | null; confidence: number | null; using_lstm: boolean | null; provenance?: string | null } | null;
  rul_note: string | null;
  /** A model exists and is waiting for its first full window. */
  rul_pending?: boolean;
  attribution: boolean;
  spin: number | null;
  spin_label: string | null;
  parts: FramePart[];
  channels: FrameChannel[];
}

export interface AssetSummary {
  domain: string;
  machine_id: string;
  kind: string;
  label: string;
  status: string | null;
  health_index: number | null;
  simulated: boolean;
}

export interface WhyResult {
  shares: Record<string, number> | null;
  justification: string;
  citations: string[];
  reason: string | null;
  top: { label: string; part: string; magnitude: number }[];
}

export const STATE_LABEL: Record<PartState, string> = {
  high: 'High load',
  elevated: 'Elevated',
  normal: 'Normal',
  nodata: 'No data',
  unmonitored: 'Not monitored',
};
