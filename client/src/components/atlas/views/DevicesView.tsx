import React, { useCallback, useEffect, useRef, useState } from 'react';
import { apiFetch } from '../../../lib/api';
import { useSession } from '../../../contexts/SessionContext';
import { recognizeMachine } from '../../../twin/machineModels';

type Metric = 'vibration' | 'temperature' | 'current';
type Limits = Record<Metric, { warning: number; critical: number }>;

interface Device {
  machine_id: string;
  name: string;
  type: string;
  location: string;
  thresholds: Limits;
}

const METRICS: { key: Metric; label: string; unit: string }[] = [
  { key: 'vibration', label: 'Vibration', unit: 'mm/s RMS' },
  { key: 'temperature', label: 'Temperature', unit: '°C' },
  { key: 'current', label: 'Current', unit: 'A' },
];

const DEFAULT_LIMITS: Limits = {
  vibration: { warning: 1.5, critical: 3.0 },
  temperature: { warning: 60, critical: 75 },
  current: { warning: 3.5, critical: 4.5 },
};

// Same rule as server/machine_registry.py MACHINE_ID_PATTERN.
const ID_PATTERN = /^[A-Za-z0-9_-]{1,32}$/;
const TYPE_SUGGESTIONS = ['Lathe', 'Pump', 'Motor', 'Compressor', 'Blower', 'Drill', 'Furnace', 'Heater'];
const OTHER = '__other__';

interface FormState {
  machine_id: string;
  name: string;
  type: string;
  location: string;
  thresholds: Record<Metric, { warning: string; critical: string }>;
}

const toForm = (d?: Device): FormState => ({
  machine_id: d?.machine_id ?? '',
  name: d?.name ?? '',
  type: d?.type ?? '',
  location: d?.location ?? '',
  thresholds: Object.fromEntries(METRICS.map(({ key }) => {
    const l = d?.thresholds?.[key] ?? DEFAULT_LIMITS[key];
    return [key, { warning: String(l.warning), critical: String(l.critical) }];
  })) as FormState['thresholds'],
});

function validate(f: FormState, isNew: boolean, existing: string[]): Record<string, string> {
  const errors: Record<string, string> = {};
  if (isNew) {
    if (!ID_PATTERN.test(f.machine_id)) errors.machine_id = 'Use 1 to 32 letters, digits, hyphens or underscores.';
    else if (existing.includes(f.machine_id)) errors.machine_id = 'A device with this ID already exists.';
  }
  if (!f.name.trim()) errors.name = 'Enter a name.';
  if (!f.type.trim()) errors.type = 'Enter a machine type.';
  for (const { key, label } of METRICS) {
    const w = Number(f.thresholds[key].warning);
    const c = Number(f.thresholds[key].critical);
    if (f.thresholds[key].warning === '' || f.thresholds[key].critical === '' || !Number.isFinite(w) || !Number.isFinite(c) || w < 0 || c < 0) {
      errors[key] = `${label}: enter two numbers of 0 or more.`;
    } else if (c <= w) {
      errors[key] = `${label}: critical must be higher than warning.`;
    }
  }
  return errors;
}

export default function DevicesView() {
  const { role } = useSession();
  const [devices, setDevices] = useState<Device[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [editing, setEditing] = useState<{ isNew: boolean; form: FormState } | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [notice, setNotice] = useState<{ text: string; brokerFor?: string } | null>(null);
  const [toDelete, setToDelete] = useState<Device | null>(null);
  const [otherType, setOtherType] = useState(false);
  const dialogRef = useRef<HTMLDialogElement>(null);

  const load = useCallback(async () => {
    try {
      setLoadError(null);
      setDevices(await apiFetch<Device[]>('/api/machines'));
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Could not load devices');
    }
  }, []);

  // Initial load; later refreshes (after a save, delete or retry) call load() directly.
  useEffect(() => {
    let active = true;
    apiFetch<Device[]>('/api/machines')
      .then(d => { if (active) setDevices(d); })
      .catch(err => { if (active) setLoadError(err instanceof Error ? err.message : 'Could not load devices'); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    const d = dialogRef.current;
    if (!d) return;
    if (toDelete && !d.open) {
      d.showModal();
      // Start on Cancel so a stray Enter cannot delete a device.
      d.querySelector<HTMLButtonElement>('[data-safe-default]')?.focus();
    }
    if (!toDelete && d.open) d.close();
  }, [toDelete]);

  if (role !== 'admin') {
    return (
      <div className="mission-panel dev-panel">
        <h2 className="dev-title">Manage devices</h2>
        <p className="dev-muted">Only admins can add, edit or remove devices. Ask an admin to make changes.</p>
      </div>
    );
  }

  const startAdd = () => { setEditing({ isNew: true, form: toForm() }); setOtherType(false); setErrors({}); setSaveError(null); setNotice(null); };
  const startEdit = (d: Device) => { setEditing({ isNew: false, form: toForm(d) }); setOtherType(!TYPE_SUGGESTIONS.includes(d.type)); setErrors({}); setSaveError(null); setNotice(null); };

  const setField = (patch: Partial<FormState>) => setEditing(e => (e ? { ...e, form: { ...e.form, ...patch } } : e));
  const setLimit = (key: Metric, which: 'warning' | 'critical', value: string) =>
    setEditing(e => (e ? { ...e, form: { ...e.form, thresholds: { ...e.form.thresholds, [key]: { ...e.form.thresholds[key], [which]: value } } } } : e));

  const save = async (ev: React.FormEvent) => {
    ev.preventDefault();
    if (!editing) return;
    const { isNew, form } = editing;
    const found = validate(form, isNew, (devices ?? []).map(d => d.machine_id));
    setErrors(found);
    if (Object.keys(found).length) return;

    const body = {
      name: form.name.trim(),
      type: form.type.trim(),
      location: form.location.trim(),
      thresholds: Object.fromEntries(METRICS.map(({ key }) => [key, {
        warning: Number(form.thresholds[key].warning),
        critical: Number(form.thresholds[key].critical),
      }])),
    };
    setSaving(true);
    setSaveError(null);
    try {
      if (isNew) {
        await apiFetch('/api/admin/machines', { method: 'POST', body: JSON.stringify({ machine_id: form.machine_id, ...body }) });
        setNotice({ text: `${form.machine_id} added.`, brokerFor: form.machine_id });
      } else {
        await apiFetch(`/api/admin/machines/${encodeURIComponent(form.machine_id)}`, { method: 'PUT', body: JSON.stringify(body) });
        setNotice({ text: `${form.machine_id} updated.` });
      }
      setEditing(null);
      await load();
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Could not save the device');
    } finally {
      setSaving(false);
    }
  };

  const confirmDelete = async () => {
    if (!toDelete) return;
    const id = toDelete.machine_id;
    try {
      await apiFetch(`/api/admin/machines/${encodeURIComponent(id)}`, { method: 'DELETE' });
      setNotice({ text: `${id} removed. Its stored readings are kept.` });
      setToDelete(null);
      await load();
    } catch (err) {
      setToDelete(null);
      setNotice({ text: `Could not remove ${id}: ${err instanceof Error ? err.message : 'unknown error'}` });
    }
  };

  const preview = editing?.form.type.trim()
    ? recognizeMachine({ type: editing.form.type, name: editing.form.name })
    : null;

  return (
    <div className="dev-view">
      <div className="mission-panel dev-panel dev-head">
        <div>
          <h2 className="dev-title">Manage devices</h2>
          <p className="dev-muted">
            Shop-floor machines that send vibration, temperature and current over MQTT. Changes apply
            immediately and are saved to <code>config/machines.json</code>.
          </p>
        </div>
        {!editing && <button type="button" className="dev-btn dev-btn-primary" onClick={startAdd}>Add device</button>}
      </div>

      {notice && (
        <div className="mission-panel dev-panel dev-notice" role="status">
          <p>{notice.text}</p>
          {notice.brokerFor && (
            <p className="dev-muted">
              One manual step remains before it can send data: give it a broker login. Add
              {' '}<code>user device_{notice.brokerFor}</code> and <code>topic write factory/{notice.brokerFor}/telemetry</code>{' '}
              to <code>mosquitto/config/mosquitto.acl</code>, add its password with <code>scripts/generate_mqtt_passwords.py</code>,
              then restart the broker.
            </p>
          )}
        </div>
      )}

      {editing && (
        <form className="mission-panel dev-panel dev-form" onSubmit={save} noValidate>
          <h3 className="dev-subtitle">{editing.isNew ? 'Add a device' : `Edit ${editing.form.machine_id}`}</h3>
          <div className="dev-grid">
            <label className="dev-field">
              <span>Device ID</span>
              <input
                value={editing.form.machine_id}
                onChange={e => setField({ machine_id: e.target.value })}
                disabled={!editing.isNew}
                placeholder="M005"
                aria-invalid={!!errors.machine_id}
                aria-describedby="dev-id-help"
              />
              <small id="dev-id-help" className={errors.machine_id ? 'dev-error' : 'dev-muted'}>
                {errors.machine_id ?? (editing.isNew ? 'Also used in its MQTT topic. Cannot be changed later.' : 'The ID cannot be changed.')}
              </small>
            </label>
            <label className="dev-field">
              <span>Name</span>
              <input value={editing.form.name} onChange={e => setField({ name: e.target.value })} placeholder="Air compressor" aria-invalid={!!errors.name} />
              {errors.name && <small className="dev-error">{errors.name}</small>}
            </label>
            <label className="dev-field">
              <span>Machine type</span>
              {/* A native select anchors its list under the field; datalist popups are placed by the browser and can drift. */}
              <select
                value={otherType ? OTHER : editing.form.type}
                onChange={e => {
                  const custom = e.target.value === OTHER;
                  setOtherType(custom);
                  setField({ type: custom ? '' : e.target.value });
                }}
                aria-invalid={!!errors.type && !otherType}
              >
                <option value="" disabled>Choose a type</option>
                {TYPE_SUGGESTIONS.map(t => <option key={t} value={t}>{t}</option>)}
                <option value={OTHER}>Other type…</option>
              </select>
              {otherType && (
                <input
                  value={editing.form.type}
                  onChange={e => setField({ type: e.target.value })}
                  placeholder="Type name, for example Kiln"
                  aria-label="Other machine type"
                  aria-invalid={!!errors.type}
                  autoFocus
                />
              )}
              <small className={errors.type ? 'dev-error' : 'dev-muted'}>
                {errors.type ?? (preview ? `3D model: ${preview.model.label}${preview.model.kind === 'generic' ? ' (type not recognised)' : ''}` : 'Picks the 3D model, for example Lathe or Pump.')}
              </small>
            </label>
            <label className="dev-field">
              <span>Location <em>(optional)</em></span>
              <input value={editing.form.location} onChange={e => setField({ location: e.target.value })} placeholder="Section E" />
            </label>
          </div>

          <fieldset className="dev-limits">
            <legend>Alert limits</legend>
            {METRICS.map(({ key, label, unit }) => (
              <div key={key} className="dev-limit-row">
                <span className="dev-limit-name">{label} <em>({unit})</em></span>
                <label>
                  <span>Warning</span>
                  <input type="number" min="0" step="any" inputMode="decimal" value={editing.form.thresholds[key].warning} onChange={e => setLimit(key, 'warning', e.target.value)} aria-invalid={!!errors[key]} />
                </label>
                <label>
                  <span>Critical</span>
                  <input type="number" min="0" step="any" inputMode="decimal" value={editing.form.thresholds[key].critical} onChange={e => setLimit(key, 'critical', e.target.value)} aria-invalid={!!errors[key]} />
                </label>
                {errors[key] && <small className="dev-error dev-limit-error">{errors[key]}</small>}
              </div>
            ))}
          </fieldset>

          {saveError && <p className="dev-error" role="alert">{saveError}</p>}
          <div className="dev-actions">
            <button type="submit" className="dev-btn dev-btn-primary" disabled={saving}>{saving ? 'Saving' : editing.isNew ? 'Add device' : 'Save changes'}</button>
            <button type="button" className="dev-btn" onClick={() => setEditing(null)} disabled={saving}>Cancel</button>
          </div>
        </form>
      )}

      <div className="mission-panel dev-panel">
        {loadError ? (
          <p className="dev-error" role="alert">
            Could not load devices ({loadError}). <button type="button" className="dev-link" onClick={() => void load()}>Try again</button>
          </p>
        ) : devices === null ? (
          <p className="dev-muted" role="status">Loading devices</p>
        ) : devices.length === 0 ? (
          <p className="dev-muted">No devices are registered. Use Add device to register the first machine.</p>
        ) : (
          <div className="dev-table-wrap">
            <table className="dev-table">
              <thead>
                <tr>
                  <th scope="col">ID</th>
                  <th scope="col">Name and type</th>
                  <th scope="col">Location</th>
                  <th scope="col">Limits (warning / critical)</th>
                  <th scope="col">MQTT topic</th>
                  <th scope="col"><span className="dev-sr">Actions</span></th>
                </tr>
              </thead>
              <tbody>
                {devices.map(d => (
                  <tr key={d.machine_id}>
                    <td className="dev-mono">{d.machine_id}</td>
                    <td>
                      <div>{d.name}</div>
                      <div className="dev-muted">{d.type} · {recognizeMachine({ type: d.type, name: d.name }).model.label} model</div>
                    </td>
                    <td>{d.location || <span className="dev-muted">Not set</span>}</td>
                    <td className="dev-mono dev-limits-cell">
                      {d.thresholds ? METRICS.map(({ key, label }) => (
                        <div key={key}>{label}: {d.thresholds[key]?.warning} / {d.thresholds[key]?.critical}</div>
                      )) : <span className="dev-muted">Defaults</span>}
                    </td>
                    <td className="dev-mono">factory/{d.machine_id}/telemetry</td>
                    <td className="dev-row-actions">
                      <button type="button" className="dev-btn" onClick={() => startEdit(d)}>Edit</button>
                      <button type="button" className="dev-btn dev-btn-danger" onClick={() => setToDelete(d)}>Delete</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <dialog ref={dialogRef} className="dev-dialog" onClose={() => setToDelete(null)} aria-labelledby="dev-del-title">
        {toDelete && (
          <>
            <h3 id="dev-del-title" className="dev-subtitle">Delete {toDelete.machine_id}?</h3>
            <p className="dev-muted">
              {toDelete.name} will disappear from the dashboard and its MQTT messages will be rejected.
              Readings already stored stay in the database.
            </p>
            <div className="dev-actions">
              <button type="button" className="dev-btn dev-btn-danger" onClick={() => void confirmDelete()}>Delete device</button>
              <button type="button" className="dev-btn" onClick={() => setToDelete(null)} data-safe-default>Cancel</button>
            </div>
          </>
        )}
      </dialog>
    </div>
  );
}
