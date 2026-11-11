import { Eye, Layers, RotateCcw, Route, Scissors, Sparkles } from 'lucide-react';
import { useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router';

import { useKiosk } from '../../app/kioskState';
import { KpiTile, LiveValue } from '../../design/data';
import { formatPercent } from '../../design/format';
import { Button, PriorityGlyph, QualityBadge, SimBadge, StatusPill, Timestamp } from '../../design/primitives';
import { Page } from '../../design/shell';
import { EmptyState, ErrorState, Skeleton, StaleNotice } from '../../design/states';
import { useTheme } from '../../hooks/useTheme';
import { errorMessage, statusOf } from '../../lib/api';
import { useStream } from '../../lib/useStream';
import { AssetInsights } from './AssetInsights';
import { AssetStage } from './AssetStage';
import { apiSource, AssetSourceContext } from './source';
import { STATE_LABEL, type FrameChannel, type FramePart, type TwinFrame, type WhyResult } from './types';

const POLL_MS = 2000;

/** RUL engine status mapped onto ISA-18.2 priorities; normal shows no colour. */
const STATUS_TONE: Record<string, 'high' | 'medium' | undefined> = { Critical: 'high', Degrading: 'medium' };

function useFrame(domain: string, machineId: string) {
  const source = useContext(AssetSourceContext);
  const [frame, setFrame] = useState<TwinFrame | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [tick, setTick] = useState(0);
  useEffect(() => {
    let alive = true;
    let timer = 0;
    const ctrl = new AbortController();
    const load = async () => {
      try {
        const f = await source.frame(domain, machineId, ctrl.signal);
        if (!alive) return;
        setFrame(f);
        setError(null);
      } catch (e) {
        if (!alive || ctrl.signal.aborted) return;
        setError(e);
      }
      if (alive) timer = window.setTimeout(load, POLL_MS);
    };
    load();
    return () => {
      alive = false;
      ctrl.abort();
      clearTimeout(timer);
    };
  }, [source, domain, machineId, tick]);
  return { frame, error, retry: () => setTick(t => t + 1) };
}

/** Engineering value when the adapter reports one, otherwise the normalised value as % of range. */
function channelValue(c: FrameChannel) {
  if (c.raw !== null && c.unit) return { value: c.raw, unit: c.unit, digits: Math.abs(c.raw) >= 100 ? 1 : 2 };
  return { value: c.value === null ? null : c.value * 100, unit: '% of range', digits: 0 };
}

const partPriority = (state: FramePart['state']) => (state === 'high' ? 'high' : state === 'elevated' ? 'medium' : null);

/** Keyed on the asset, so explode, cutaway, selection and Why start fresh on every machine. */
export default function AssetPage() {
  const { domain = '', machineId = '' } = useParams();
  return <AssetView key={`${domain}/${machineId}`} domain={domain} machineId={machineId} />;
}

function AssetView({ domain, machineId }: { domain: string; machineId: string }) {
  const { frame, error, retry } = useFrame(domain, machineId);
  // Pushed readings (HTTP, WebSocket, MQTT, Modbus bridge) refresh the frame at once instead of on the next poll.
  const live = useContext(AssetSourceContext) === apiSource;
  useStream(live ? machineId : null, retry);
  const source = useContext(AssetSourceContext);
  const { theme } = useTheme();
  const kiosk = useKiosk();
  const [selected, setSelected] = useState<string | null>(null);
  const [explode, setExplode] = useState(false);
  const [cut, setCut] = useState(false);
  const [isolate, setIsolate] = useState(false);
  const [tour, setTour] = useState(false);
  const [resetKey, setResetKey] = useState(0);
  const [why, setWhy] = useState<{ busy: boolean; result: WhyResult | null; error: string | null }>({ busy: false, result: null, error: null });
  const onTourChange = useCallback((on: boolean) => setTour(on), []);
  const channels = useMemo(() => new Map(frame?.channels.map(c => [c.feature, c])), [frame]);

  if (error && !frame) {
    const notFound = statusOf(error) === 404;
    return (
      <Page title={machineId} purpose="3D Asset View">
        {notFound ? (
          <EmptyState title="No data for this asset yet" body={`ATLAS has no reading for ${domain}/${machineId}. It appears here once its adapter or device sends data.`} action={<Link to="/assets">All assets</Link>} />
        ) : (
          <ErrorState error={error} onRetry={retry} />
        )}
      </Page>
    );
  }
  if (!frame) {
    return (
      <Page title={machineId} purpose="3D Asset View">
        <Skeleton height="28rem" label="Loading the asset" />
      </Page>
    );
  }

  const tone = frame.status ? STATUS_TONE[frame.status] : undefined;
  const stale = frame.channels.some(c => c.quality === 'STALE');
  const quality = frame.simulated ? 'SIMULATED' : stale ? 'STALE' : 'GOOD';
  const shares = why.result?.shares ?? null;
  const sel = frame.parts.find(p => p.id === selected) ?? null;
  const selChannels = sel ? sel.channels.map(f => channels.get(f)).filter((c): c is FrameChannel => !!c) : [];
  // the callout shows the channel that sets the part's load, else the first with a reading
  const calloutCh = [...selChannels].sort((a, b) => (b.load ?? -1) - (a.load ?? -1)).find(c => c.value !== null);
  const calloutValue = calloutCh ? channelValue(calloutCh) : null;

  const toggleWhy = async () => {
    if (why.result || why.error) {
      setWhy({ busy: false, result: null, error: null });
      return;
    }
    setWhy({ busy: true, result: null, error: null });
    try {
      setWhy({ busy: false, result: await source.why(frame), error: null });
    } catch (e) {
      const s = statusOf(e);
      const msg = s === 403
        ? 'Explanations need an operator or admin role.'
        : s === 409
          ? 'The model is still collecting its first 30 readings for this machine.'
          : s === 404
            ? frame.rul_note ?? 'No model explains this machine yet.'
            : errorMessage(e);
      setWhy({ busy: false, result: null, error: msg });
    }
  };

  return (
    <Page
      title={frame.machine_id}
      purpose={frame.label}
      actions={
        <>
          {frame.simulated && <SimBadge />}
          {frame.status && <StatusPill tone={tone ?? 'quiet'}>{frame.status}</StatusPill>}
        </>
      }
    >
      {stale && frame.ts && <StaleNotice lastUpdate={frame.ts} />}
      <div className="ax-asset__kpis">
        <KpiTile label="Health index" value={frame.health_index === null ? null : frame.health_index * 100} unit="%" quality={quality} ts={frame.ts ?? undefined} caption="0 is fresh, 100 is at its limit" />
        {frame.rul ? (
          <KpiTile
            label="Remaining useful life"
            value={frame.rul.value}
            unit={frame.rul.unit}
            quality={quality}
            priority={tone}
            ts={frame.ts ?? undefined}
            caption={frame.rul.uncertainty !== null ? `± ${frame.rul.uncertainty.toFixed(1)} ${frame.rul.unit}, 1 sd${frame.rul.using_lstm === false ? ', EMA fallback' : ''}${frame.rul.provenance === 'SIMULATED' ? ', model trained on simulated failures' : ''}` : undefined}
          />
        ) : (
          <section className="ax-kpi">
            <div className="ax-kpi__head">
              <span>Remaining useful life</span>
              {frame.rul_pending && <StatusPill tone="quiet">Collecting</StatusPill>}
            </div>
            <p className="ax-asset__note">{frame.rul_note ?? 'No prediction for this machine.'}</p>
          </section>
        )}
        <section className="ax-kpi">
          <div className="ax-kpi__head">
            <span>Last reading</span>
          </div>
          {frame.ts ? <Timestamp value={frame.ts} showZone /> : <QualityBadge quality="MISSING" />}
          <p className="ax-asset__note">Refreshed every {POLL_MS / 1000} s</p>
        </section>
      </div>

      <div className="ax-asset">
        <section className="ax-panel ax-asset__stage" aria-label="3D Asset View">
          <div className="ax-asset__tools" role="toolbar" aria-label="View controls">
            <Button size="sm" variant="ghost" icon={<Layers />} aria-pressed={explode} onClick={() => setExplode(v => !v)}>Explode</Button>
            <Button size="sm" variant="ghost" icon={<Scissors />} aria-pressed={cut} onClick={() => setCut(v => !v)}>Cutaway</Button>
            <Button size="sm" variant="ghost" icon={<Eye />} aria-pressed={isolate} disabled={!selected} onClick={() => setIsolate(v => !v)}>Isolate</Button>
            <Button size="sm" variant="ghost" icon={<Sparkles />} aria-pressed={!!shares} disabled={why.busy} onClick={toggleWhy}>{why.busy ? 'Explaining' : 'Show why'}</Button>
            <Button size="sm" variant="ghost" icon={<Route />} aria-pressed={tour} onClick={() => setTour(v => !v)}>Tour</Button>
            <Button size="sm" variant="ghost" icon={<RotateCcw />} onClick={() => { setSelected(null); setResetKey(k => k + 1); }}>Reset view</Button>
          </div>
          <AssetStage
            kind={frame.kind}
            parts={frame.parts}
            dark={theme === 'dark'}
            spin={frame.spin}
            why={shares}
            selected={selected}
            explode={explode}
            cut={cut}
            isolate={isolate}
            tour={tour}
            autoTour={kiosk.active}
            resetKey={resetKey}
            onSelect={setSelected}
            onTourChange={onTourChange}
            callout={sel && (
              <>
                <strong>{sel.name}</strong>
                {calloutCh && calloutValue && (
                  <span className="num">{calloutValue.value === null ? 'no data' : `${calloutValue.value.toFixed(calloutValue.digits)} ${calloutValue.unit}`}</span>
                )}
              </>
            )}
          />
          <p className="ax-asset__legend">
            {shares ? (
              <span><i className="ax-asset__swatch" aria-hidden /> Brighter means a larger share of the model's attribution</span>
            ) : (
              <>
                <span><PriorityGlyph priority="high" /> High load</span>
                <span><PriorityGlyph priority="medium" /> Elevated load</span>
              </>
            )}
            {frame.spin !== null && frame.spin_label && <span>Rotation follows {frame.spin_label.charAt(0).toLowerCase() + frame.spin_label.slice(1)}, shown slowed</span>}
          </p>
        </section>

        <aside className="ax-panel ax-asset__side" aria-label="Parts and sensors">
          {(why.result || why.error) && (
            <section className="ax-asset__why" aria-live="polite">
              <h2 className="ax-asset__h">Why</h2>
              {why.error && <p>{why.error}</p>}
              {why.result && (
                <>
                  {shares ? (
                    <ol>
                      {why.result.top.map(t => (
                        <li key={t.label}>
                          <span>{t.label}</span>
                          <span className="num">{t.magnitude.toFixed(2)} {frame.rul?.unit ?? ''}</span>
                        </li>
                      ))}
                    </ol>
                  ) : (
                    <p>{why.result.reason ?? 'No per-sensor attribution for this machine.'}</p>
                  )}
                  <p>{why.result.justification}</p>
                  {why.result.citations.length > 0 && <p className="ax-asset__note">Grounded in {why.result.citations.length} similar past cases from memory (AMKB).</p>}
                  {shares && <p className="ax-asset__note">Occlusion attribution: how much the RUL moves when each sensor is masked, summed per part.</p>}
                </>
              )}
            </section>
          )}

          <h2 className="ax-asset__h">Parts</h2>
          <ul className="ax-asset__parts">
            {frame.parts.map(p => {
              const pr = shares ? null : partPriority(p.state);
              return (
                <li key={p.id}>
                  <button type="button" aria-pressed={selected === p.id} onClick={() => setSelected(selected === p.id ? null : p.id)}>
                    <span className="ax-asset__glyph">{pr && <PriorityGlyph priority={pr} />}</span>
                    <span className="ax-asset__name">{p.name}</span>
                    <span className="ax-asset__state num">
                      {shares ? formatPercent(shares[p.id] ?? 0) : p.load === null ? STATE_LABEL[p.state] : formatPercent(p.load)}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>

          {sel ? (
            <section className="ax-asset__detail">
              <h3>{sel.name}</h3>
              <p>{sel.detail}</p>
              {selChannels.length === 0 ? (
                <p className="ax-asset__note">No sensor is bound to this part.</p>
              ) : (
                selChannels.map(c => {
                  const v = channelValue(c);
                  return <LiveValue key={c.feature} label={c.label} value={v.value} unit={v.unit} digits={v.digits} quality={c.quality} ts={frame.ts ?? undefined} relative size="sm" />;
                })
              )}
            </section>
          ) : (
            <p className="ax-asset__note">Select a part here or in the view to see its sensors.</p>
          )}
          <p className="ax-asset__note">Load per part is a heuristic: the bound sensor furthest toward its load end, as a share of its range.</p>
        </aside>
      </div>
      {!kiosk.active && <AssetInsights frame={frame} focus={selChannels} />}
    </Page>
  );
}
