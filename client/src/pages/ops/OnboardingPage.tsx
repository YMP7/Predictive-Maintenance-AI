import { useId, useState, type ReactNode } from 'react';
import { Link } from 'react-router';

import { Button, QualityBadge, StatusPill, Timestamp } from '../../design/primitives';
import { Page } from '../../design/shell';
import type { DataQuality } from '../../design/types';
import { apiFetch, errorMessage, statusOf } from '../../lib/api';
import { usePoll } from '../../lib/usePoll';
import { useStream, type StreamReading } from '../../lib/useStream';
import { TokenNotice } from './AdminPages';
import { DOMAIN_LABEL } from './labels';

/* Mirrors server/adapters/configurable_adapter.py SensorProfile / ChannelSpec. */
interface Channel {
  channel: string;
  feature: string;
  unit: string;
  scale: number;
  offset: number;
  valid_min: number;
  valid_max: number;
  sampling_hz: number;
  health_weight: number;
  part: string | null;
}

interface Profile {
  machine_id: string;
  domain: string;
  display_name: string;
  simulated: boolean;
  channels: Channel[];
}

interface DomainProfile {
  kind: string;
  label: string;
  parts: { id: string; name: string }[];
}

type Protocol = 'http' | 'websocket' | 'mqtt' | 'modbus';

const STEPS = ['Register asset', 'Domain and profile', 'Protocol', 'Map channels', 'Live preview', 'Bind to 3D parts', 'Activate'];
const ID = /^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$/;
const blank = (): Channel => ({ channel: '', feature: '', unit: '', scale: 1, offset: 0, valid_min: 0, valid_max: 100, sampling_hz: 1, health_weight: 0, part: null });

function channelErrors(c: Channel): string | null {
  if (!ID.test(c.channel)) return 'Channel name: letters, digits, _ . - only';
  if (!ID.test(c.feature)) return 'Feature name: letters, digits, _ . - only';
  if (!c.unit.trim()) return 'Unit is required (SI after scaling)';
  if (!(c.valid_max > c.valid_min)) return 'Valid maximum must exceed the minimum';
  if (!c.scale) return 'Scale cannot be 0';
  return null;
}

export default function OnboardingPage() {
  const [step, setStep] = useState(0);
  const [p, setP] = useState<Profile>({ machine_id: '', domain: 'modbus', display_name: '', simulated: false, channels: [blank()] });
  const [protocol, setProtocol] = useState<Protocol>('http');
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [issued, setIssued] = useState<{ token: string; examples: Record<string, string> } | null>(null);
  const [done, setDone] = useState(false);
  const domainProfile = usePoll<DomainProfile>(`/api/atlas/domain/${p.domain}/profile`, 0);

  const set = (patch: Partial<Profile>) => {
    setP(prev => ({ ...prev, ...patch }));
    setSaved(false);
  };
  const setChannel = (i: number, patch: Partial<Channel>) => set({ channels: p.channels.map((c, j) => (j === i ? { ...c, ...patch } : c)) });

  const valid = [
    ID.test(p.machine_id) && p.display_name.trim().length > 0,
    !!p.domain,
    true,
    p.channels.length > 0 && p.channels.every(c => !channelErrors(c)) && new Set(p.channels.map(c => c.channel)).size === p.channels.length,
    true,
    true,
    true,
  ];

  const loadTemplate = async () => {
    setError(null);
    try {
      const t = await apiFetch<Profile>(`/api/admin/sensor-profiles/template?domain=${p.domain}&machine_id=${encodeURIComponent(p.machine_id)}&simulated=${p.simulated}`);
      set({ channels: t.channels.map(c => ({ ...blank(), ...c })) });
    } catch (e) {
      setError(statusOf(e) === 404 ? `No register map for ${DOMAIN_LABEL[p.domain] ?? p.domain}. Map the channels by hand in step 4.` : errorMessage(e));
    }
  };

  const save = async () => {
    setBusy(true);
    setError(null);
    try {
      await apiFetch(`/api/admin/sensor-profiles/${encodeURIComponent(p.machine_id)}`, { method: 'PUT', body: JSON.stringify({ ...p, display_name: p.display_name.trim() }) });
      setSaved(true);
      return true;
    } catch (e) {
      setError(errorMessage(e));
      return false;
    } finally {
      setBusy(false);
    }
  };

  const activate = async () => {
    if (!(await save())) return;
    setBusy(true);
    try {
      setIssued(await apiFetch('/api/admin/devices', { method: 'POST', body: JSON.stringify({ machine_id: p.machine_id, protocol }) }));
      setDone(true);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Page title="Sensor onboarding" purpose="Connect a new asset: describe its channels, check live samples, bind them to the 3D model, then issue the device token.">
      <ol className="ax-steps" aria-label="Onboarding steps">
        {STEPS.map((s, i) => (
          <li key={s} aria-current={i === step ? 'step' : undefined} data-done={i < step ? '' : undefined}>
            {s}
          </li>
        ))}
      </ol>

      <section className="ax-panel" aria-labelledby="ob-step">
        <div className="ax-panel__head">
          <h2 id="ob-step">
            Step {step + 1} of {STEPS.length}: {STEPS[step]}
          </h2>
          {saved && <StatusPill tone="quiet">Profile saved</StatusPill>}
        </div>
        <div className="ax-panel__body ax-stack">
          {step === 0 && <Register p={p} set={set} />}
          {step === 1 && <PickDomain p={p} set={set} domainProfile={domainProfile.data} onTemplate={loadTemplate} />}
          {step === 2 && <PickProtocol p={p} protocol={protocol} setProtocol={setProtocol} />}
          {step === 3 && <MapChannels p={p} setChannel={setChannel} set={set} />}
          {step === 4 && <Preview p={p} saved={saved} busy={busy} onSave={save} />}
          {step === 5 && <BindParts p={p} parts={domainProfile.data?.parts ?? []} setChannel={setChannel} />}
          {step === 6 &&
            (done ? (
              <div className="ax-stack">
                <p>
                  <strong>{p.display_name}</strong> is active. Its readings appear in the 3D Asset View and the device list as they arrive.
                </p>
                <div className="ax-row">
                  <Link to={`/assets/${p.domain}/${encodeURIComponent(p.machine_id)}`}>Open its 3D Asset View</Link>
                  <Link to="/admin/devices">Devices</Link>
                </div>
              </div>
            ) : (
              <div className="ax-stack">
                <dl className="ax-dl">
                  <dt>Asset</dt>
                  <dd>
                    {p.display_name} ({p.machine_id})
                  </dd>
                  <dt>Domain</dt>
                  <dd>{DOMAIN_LABEL[p.domain] ?? p.domain}</dd>
                  <dt>Protocol</dt>
                  <dd>{protocol}</dd>
                  <dt>Channels</dt>
                  <dd>{p.channels.map(c => `${c.channel} (${c.unit})`).join(', ')}</dd>
                  <dt>Bound to parts</dt>
                  <dd>
                    {p.channels.filter(c => c.part).length} of {p.channels.length}
                  </dd>
                </dl>
                <p className="ax-note">Activating saves the profile and issues a device token. The token is shown once.</p>
              </div>
            ))}
          {error && (
            <p className="ax-error" role="alert">
              {error}
            </p>
          )}
          <div className="ax-row">
            <Button disabled={step === 0 || done} onClick={() => setStep(s => s - 1)}>
              Back
            </Button>
            {step < STEPS.length - 1 ? (
              <Button variant="primary" disabled={!valid[step]} onClick={() => setStep(s => s + 1)}>
                Next: {STEPS[step + 1]}
              </Button>
            ) : (
              !done && (
                <Button variant="primary" disabled={busy || !valid.every(Boolean)} onClick={activate}>
                  {busy ? 'Activating' : 'Activate and issue token'}
                </Button>
              )
            )}
          </div>
        </div>
      </section>
      {issued && <TokenNotice token={issued.token} examples={issued.examples} onClose={() => setIssued(null)} />}
    </Page>
  );
}

function Field({ label, hint, children, id }: { label: string; hint?: string; children: ReactNode; id: string }) {
  return (
    <label className="ax-field" htmlFor={id}>
      <span className="ax-field__label">{label}</span>
      {children}
      {hint && <span className="ax-field__hint">{hint}</span>}
    </label>
  );
}

function Register({ p, set }: { p: Profile; set: (x: Partial<Profile>) => void }) {
  const a = useId();
  const b = useId();
  return (
    <div className="ax-form">
      <Field id={a} label="Asset id" hint="Letters, digits, _ . - (up to 64). Used in URLs and topics; cannot change later.">
        <input id={a} className="ax-input" value={p.machine_id} autoFocus onChange={e => set({ machine_id: e.target.value.trim() })} aria-invalid={!!p.machine_id && !ID.test(p.machine_id)} />
      </Field>
      <Field id={b} label="Display name">
        <input id={b} className="ax-input" value={p.display_name} onChange={e => set({ display_name: e.target.value })} placeholder="e.g. Cooling water pump 2, hall B" />
      </Field>
    </div>
  );
}

function PickDomain({ p, set, domainProfile, onTemplate }: { p: Profile; set: (x: Partial<Profile>) => void; domainProfile: DomainProfile | null; onTemplate: () => void }) {
  const a = useId();
  const b = useId();
  return (
    <div className="ax-form">
      <Field id={a} label="Machine type" hint="Sets the 3D model and the parts its channels can bind to.">
        <select id={a} className="ax-input" value={p.domain} onChange={e => set({ domain: e.target.value })}>
          {Object.entries(DOMAIN_LABEL).map(([d, l]) => (
            <option key={d} value={d}>
              {l}
            </option>
          ))}
        </select>
      </Field>
      {domainProfile && (
        <p className="ax-note">
          3D model: {domainProfile.label}, {domainProfile.parts.length} parts.
        </p>
      )}
      <label className="ax-row" htmlFor={b}>
        <input id={b} type="checkbox" checked={p.simulated} onChange={e => set({ simulated: e.target.checked })} />
        Data comes from a simulator, not a physical sensor (shown with SIMULATED badges)
      </label>
      <div className="ax-row">
        <Button onClick={onTemplate}>Load the register map for this machine type</Button>
        <span className="ax-note">Fills step 4 with channels, units and valid ranges where ATLAS knows the device (Modbus today).</span>
      </div>
    </div>
  );
}

const SNIPPET: Record<Protocol, (id: string, ch: string) => string> = {
  http: (id, ch) => `curl -X POST http://<host>:8000/api/ingest/${id} \\\n  -H "Authorization: Bearer <device token>" -H "Content-Type: application/json" \\\n  -d '{"values": {"${ch}": 12.5}}'`,
  websocket: id => `ws://<host>:8000/api/ingest/ws/${id}\nfirst message: {"token": "<device token>"}\nthen: {"values": {...}} per sample`,
  mqtt: (id, ch) => `topic:   factory/${id}/telemetry\npayload: {"values": {"${ch}": 12.5}}\nbroker credentials are per device in mosquitto/config`,
  modbus: id => `set ATLAS_DEVICE_TOKEN=<device token>\npython scripts/modbus_bridge.py --machine-id ${id} --host <plc ip> --port 502\n(add --simulate to run the bundled Modbus simulator instead)`,
};

function PickProtocol({ p, protocol, setProtocol }: { p: Profile; protocol: Protocol; setProtocol: (x: Protocol) => void }) {
  const ch = p.channels[0]?.channel || '<channel>';
  return (
    <div className="ax-stack">
      <div className="ax-row" role="radiogroup" aria-label="Protocol">
        {(['http', 'websocket', 'mqtt', 'modbus'] as Protocol[]).map(x => (
          <Button key={x} size="sm" role="radio" aria-checked={protocol === x} variant={protocol === x ? 'primary' : 'default'} onClick={() => setProtocol(x)}>
            {x === 'http' ? 'HTTP push' : x === 'websocket' ? 'WebSocket' : x === 'mqtt' ? 'MQTT' : 'Modbus TCP polling'}
          </Button>
        ))}
      </div>
      <p className="ax-note">Example with your asset id. The real token is generated in step 7 and shown once, with these examples filled in.</p>
      <code className="ax-code">{SNIPPET[protocol](p.machine_id || '<asset id>', ch)}</code>
    </div>
  );
}

const COLS: [keyof Channel, string, 'text' | 'number'][] = [
  ['channel', 'Device sends', 'text'],
  ['feature', 'Feature', 'text'],
  ['unit', 'SI unit', 'text'],
  ['scale', 'Scale', 'number'],
  ['offset', 'Offset', 'number'],
  ['valid_min', 'Valid min', 'number'],
  ['valid_max', 'Valid max', 'number'],
  ['sampling_hz', 'Rate (Hz)', 'number'],
  ['health_weight', 'Health weight', 'number'],
];

function MapChannels({ p, setChannel, set }: { p: Profile; setChannel: (i: number, x: Partial<Channel>) => void; set: (x: Partial<Profile>) => void }) {
  const num = (v: string) => (v === '' ? NaN : Number(v));
  return (
    <div className="ax-stack">
      <p className="ax-note">
        Value seen by the pipeline = raw × scale + offset, in the SI unit. Values outside the valid range are flagged OUT_OF_RANGE, never silently clipped. Health weight 0 means shown but not counted in the health index.
      </p>
      <div tabIndex={0} role="region" aria-label="Channel mapping table" className="ax-table-scroll">
        <table className="ax-table">
          <caption className="visually-hidden">Channel mapping</caption>
          <thead>
            <tr>
              {COLS.map(([, h]) => (
                <th key={h} scope="col">
                  {h}
                </th>
              ))}
              <th scope="col">
                <span className="visually-hidden">Remove</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {p.channels.map((c, i) => {
              const err = channelErrors(c);
              return (
                <tr key={i}>
                  {COLS.map(([k, h, type]) => (
                    <td key={k}>
                      <input
                        className="ax-input"
                        style={{ width: type === 'number' ? '6rem' : '9rem' }}
                        aria-label={`${h}, row ${i + 1}`}
                        type={type}
                        step="any"
                        value={type === 'number' ? (Number.isNaN(c[k] as number) ? '' : (c[k] as number)) : ((c[k] as string) ?? '')}
                        onChange={e => setChannel(i, { [k]: type === 'number' ? num(e.target.value) : e.target.value.trim() } as Partial<Channel>)}
                        aria-invalid={!!err}
                      />
                    </td>
                  ))}
                  <td>
                    <Button size="sm" variant="ghost" disabled={p.channels.length === 1} onClick={() => set({ channels: p.channels.filter((_, j) => j !== i) })}>
                      Remove
                    </Button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {p.channels.map((c, i) => {
        const err = channelErrors(c);
        return err ? (
          <p key={i} className="ax-error">
            Row {i + 1}: {err}
          </p>
        ) : null;
      })}
      <div>
        <Button onClick={() => set({ channels: [...p.channels, blank()] })}>Add channel</Button>
      </div>
    </div>
  );
}

interface IngestSummary {
  accepted_points: number;
  rejected: number;
  rejects: { reason: string; channel?: string }[];
}

function Preview({ p, saved, busy, onSave }: { p: Profile; saved: boolean; busy: boolean; onSave: () => Promise<boolean> }) {
  const [events, setEvents] = useState<StreamReading[]>([]);
  const [values, setValues] = useState<Record<string, string>>({});
  const [result, setResult] = useState<IngestSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const live = useStream(saved ? p.machine_id : null, r => setEvents(ev => [r, ...ev].slice(0, 10)));

  const send = async () => {
    setError(null);
    const body: Record<string, number> = {};
    for (const [k, v] of Object.entries(values)) if (v.trim() !== '') body[k] = Number(v);
    try {
      setResult(await apiFetch<IngestSummary>(`/api/machines/${encodeURIComponent(p.machine_id)}/manual-readings`, { method: 'POST', body: JSON.stringify({ values: body, note: 'onboarding test sample' }) }));
    } catch (e) {
      setError(errorMessage(e));
    }
  };

  if (!saved)
    return (
      <div className="ax-stack">
        <p>Save the profile to start the live preview. Devices can send only after activation, but you can send test samples now.</p>
        <div>
          <Button variant="primary" disabled={busy} onClick={onSave}>
            {busy ? 'Saving' : 'Save profile and open preview'}
          </Button>
        </div>
      </div>
    );

  return (
    <div className="ax-stack">
      <p className="ax-row">
        Live stream: {live ? <StatusPill tone="quiet">Connected</StatusPill> : <StatusPill tone="medium">Connecting</StatusPill>}
        <span className="ax-note">Samples from any source (device, test, upload) appear below as they are validated.</span>
      </p>
      <div className="ax-form__row">
        {p.channels.map(c => (
          <label key={c.channel} className="ax-field">
            <span className="ax-field__label">{c.channel} (raw)</span>
            <input className="ax-input" type="number" step="any" value={values[c.channel] ?? ''} onChange={e => setValues(v => ({ ...v, [c.channel]: e.target.value }))} />
          </label>
        ))}
      </div>
      <div className="ax-row">
        <Button disabled={!Object.values(values).some(v => v.trim() !== '')} onClick={send}>
          Send test sample
        </Button>
        {result && (
          <span className="ax-note">
            {result.accepted_points} points accepted, {result.rejected} rejected
            {result.rejects.length > 0 && `: ${result.rejects.map(r => `${r.channel ?? ''} ${r.reason}`).join('; ')}`}
          </span>
        )}
      </div>
      {error && <p className="ax-error">{error}</p>}
      {events.length === 0 ? (
        <p className="ax-note">No samples yet.</p>
      ) : (
        <ul className="ax-list" aria-live="polite">
          {events.map((r, i) => (
            <li key={`${r.ts}-${i}`}>
              <span className="num ax-note">
                <Timestamp value={r.ts} style="time" />
              </span>
              <span>{r.source}</span>
              <span className="ax-row">
                {Object.entries(r.channels).map(([ch, v]) => (
                  <span key={ch} className="ax-row">
                    <QualityBadge quality={v.quality as DataQuality} compact={v.quality === 'GOOD'} />
                    {ch} <span className="num">{v.value}</span> {v.unit}
                  </span>
                ))}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function BindParts({ p, parts, setChannel }: { p: Profile; parts: { id: string; name: string }[]; setChannel: (i: number, x: Partial<Channel>) => void }) {
  return (
    <div className="ax-stack">
      <p className="ax-note">Each channel tints the part it is bound to in the 3D Asset View. Unbound channels are listed but tint nothing.</p>
      <ul className="ax-list">
        {p.channels.map((c, i) => (
          <li key={c.channel}>
            <span>
              <strong>{c.channel}</strong> <span className="ax-note">{c.unit}</span>
            </span>
            <select className="ax-input" aria-label={`3D part for ${c.channel}`} value={c.part ?? ''} onChange={e => setChannel(i, { part: e.target.value || null })} style={{ marginLeft: 'auto' }}>
              <option value="">Not bound</option>
              {parts.map(x => (
                <option key={x.id} value={x.id}>
                  {x.name}
                </option>
              ))}
            </select>
          </li>
        ))}
      </ul>
    </div>
  );
}
