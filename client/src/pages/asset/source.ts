import { createContext } from 'react';

import { apiFetch } from '../../lib/api';
import type { TwinFrame, WhyResult } from './types';

/** Where the Asset View gets its data: the API in the product, fixtures in the dev gallery. */
export interface AssetSource {
  frame(domain: string, machineId: string, signal: AbortSignal): Promise<TwinFrame>;
  why(frame: TwinFrame): Promise<WhyResult>;
}

interface Explanation {
  primary_justification: string;
  citations: string[];
  sensor_attributions: { sensor_name: string; magnitude: number }[];
  attribution_unavailable_reason: string | null;
}

/** Sum per-sensor attribution into per-part shares through the frame's channel bindings. */
export function sharesFromExplanation(frame: TwinFrame, r: Explanation): WhyResult {
  const byFeature = new Map(frame.channels.map(c => [c.feature, c]));
  const sums: Record<string, number> = {};
  const top: WhyResult['top'] = [];
  for (const a of r.sensor_attributions ?? []) {
    // sensor_name reads "s2 (T24 ...)": the code before the space is the channel
    const ch = byFeature.get(a.sensor_name.split(' ')[0]);
    if (!ch) continue;
    sums[ch.part] = (sums[ch.part] ?? 0) + a.magnitude;
    top.push({ label: ch.label, part: ch.part, magnitude: a.magnitude });
  }
  const total = Object.values(sums).reduce((s, v) => s + v, 0);
  return {
    shares: total > 0 ? Object.fromEntries(Object.entries(sums).map(([k, v]) => [k, v / total])) : null,
    justification: r.primary_justification,
    citations: r.citations ?? [],
    reason: r.attribution_unavailable_reason,
    top: top.sort((a, b) => b.magnitude - a.magnitude).slice(0, 3),
  };
}

export const apiSource: AssetSource = {
  frame: (domain, machineId, signal) =>
    apiFetch<TwinFrame>(`/api/assets/${encodeURIComponent(machineId)}/frame?domain=${encodeURIComponent(domain)}`, { signal }),
  async why(frame) {
    const w = await apiFetch<{ window: number[][]; cycle: number }>(`/api/atlas/domain/${frame.domain}/machine/${encodeURIComponent(frame.machine_id)}/window`);
    const r = await apiFetch<Explanation>('/api/explain', {
      method: 'POST',
      body: JSON.stringify({ domain: frame.domain, machine_id: frame.machine_id, cycle: w.cycle, window: w.window, k: 10 }),
    });
    return sharesFromExplanation(frame, r);
  },
};

export const AssetSourceContext = createContext<AssetSource>(apiSource);
