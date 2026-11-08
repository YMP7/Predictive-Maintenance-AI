import { useEffect, useRef, useState } from 'react';

import { useReducedMotion } from '../../design/hooks';
import { createAssetView, type AssetView, type Colours, type PartState } from '../../teardown/view';
import { AssetSchematic } from './AssetSchematic';
import type { FramePart } from './types';

export interface StageProps {
  kind: string;
  parts: FramePart[];
  dark: boolean;
  spin: number | null;
  why: Record<string, number> | null;
  selected: string | null;
  explode: boolean;
  cut: boolean;
  isolate: boolean;
  tour: boolean;
  autoTour: boolean;
  resetKey: number;
  callout: React.ReactNode;
  onSelect: (id: string | null) => void;
  onTourChange: (on: boolean) => void;
}

function webglAvailable(): boolean {
  if (new URLSearchParams(window.location.search).get('no3d') === '1') return false;
  try {
    const c = document.createElement('canvas');
    const gl = (c.getContext('webgl2') ?? c.getContext('webgl')) as WebGLRenderingContext | null;
    gl?.getExtension('WEBGL_lose_context')?.loseContext();
    return !!gl;
  } catch {
    return false;
  }
}

const colours = (): Colours => {
  const css = getComputedStyle(document.documentElement);
  const v = (name: string, fallback: string) => css.getPropertyValue(name).trim() || fallback;
  return { high: v('--p-high', '#c2410c'), elevated: v('--p-medium', '#a16207'), accent: v('--accent', '#1f6feb') };
};

/** The 3D view, or the 2-D schematic when WebGL is off or the model fails to build. */
export function AssetStage(p: StageProps) {
  const [gl] = useState(webglAvailable);
  const [failed, setFailed] = useState<string | null>(null);
  const host = useRef<HTMLDivElement>(null);
  const callout = useRef<HTMLDivElement>(null);
  const [view, setView] = useState<AssetView | null>(null);
  const reduced = useReducedMotion();
  // the latest callbacks, without rebuilding the scene when they change
  const handlers = useRef({ onSelect: p.onSelect, onTourChange: p.onTourChange });
  useEffect(() => {
    handlers.current = { onSelect: p.onSelect, onTourChange: p.onTourChange };
  });

  useEffect(() => {
    if (!gl || !host.current) return;
    // a fresh canvas per mount: a disposed view forces its context loss, and a canvas keeps a lost context
    const canvas = document.createElement('canvas');
    canvas.className = 'ax-stage__canvas';
    canvas.setAttribute('aria-label', 'Interactive 3D view of the machine. Drag to turn, scroll to zoom, click a part to select it. The parts list offers the same selection by keyboard.');
    canvas.setAttribute('role', 'img');
    host.current.prepend(canvas);
    let v: AssetView;
    try {
      v = createAssetView({
        canvas,
        callout: callout.current,
        kind: p.kind,
        dark: document.documentElement.getAttribute('data-theme') === 'dark',
        colours: colours(),
        reducedMotion: reduced,
        autoTour: p.autoTour,
        onSelect: id => handlers.current.onSelect(id),
        onTourChange: on => handlers.current.onTourChange(on),
      });
    } catch (e) {
      canvas.remove();
      queueMicrotask(() => setFailed(e instanceof Error ? e.message : String(e)));
      return;
    }
    queueMicrotask(() => setView(v));
    return () => {
      v.dispose();
      canvas.remove();
      setView(null);
    };
  }, [gl, p.kind, reduced, p.autoTour]);

  const statesKey = JSON.stringify(Object.fromEntries(p.parts.map(x => [x.id, x.state])));
  useEffect(() => view?.setStates(JSON.parse(statesKey) as Record<string, PartState>), [view, statesKey]);
  useEffect(() => view?.setWhy(p.why), [view, p.why]);
  useEffect(() => view?.setSpin(p.spin), [view, p.spin]);
  useEffect(() => view?.setSelected(p.selected), [view, p.selected]);
  useEffect(() => view?.setExplode(p.explode), [view, p.explode]);
  useEffect(() => view?.setCut(p.cut), [view, p.cut]);
  useEffect(() => view?.setIsolate(p.isolate), [view, p.isolate]);
  useEffect(() => view?.setTour(p.tour), [view, p.tour]);
  useEffect(() => view?.setTheme(p.dark, colours()), [view, p.dark]);
  useEffect(() => {
    if (p.resetKey) view?.resetView();
  }, [view, p.resetKey]);

  if (!gl || failed) {
    return (
      <AssetSchematic
        parts={p.parts}
        selected={p.selected}
        why={p.why}
        onSelect={p.onSelect}
        reason={failed ? `The 3D model could not be built (${failed}).` : 'WebGL is off or unavailable in this browser.'}
      />
    );
  }
  return (
    <div className="ax-stage" ref={host}>
      <div ref={callout} className="ax-stage__callout" data-visible="false" aria-hidden>
        {p.callout && <div className="ax-stage__label">{p.callout}</div>}
      </div>
    </div>
  );
}
