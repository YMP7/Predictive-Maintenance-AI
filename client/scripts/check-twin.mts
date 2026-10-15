import assert from 'node:assert/strict';
import * as m from '../src/twin/machineModels.ts';
const r = (d) => m.recognizeMachine(d);
assert.equal(r({ type: 'Lathe', name: 'Lathe Machine' }).model.kind, 'lathe');
assert.equal(r({ type: 'Motor', name: 'Pump Motor' }).model.kind, 'motor_pump');
assert.equal(r({ type: 'Drill', name: 'Drill Press' }).model.kind, 'drill_press');
assert.equal(r({ type: 'Heater', name: 'Furnace' }).model.kind, 'furnace');
for (const [d, k] of [['cmapss','turbofan'],['laptop','laptop'],['mobile','phone'],['server','server']]) assert.equal(r({ domain: d }).model.kind, k);
assert.equal(r({ type: 'Compressor X' }).model.kind, 'motor_pump');
assert.equal(r({ channels: ['vibration_rms', 'current'] }).model.kind, 'motor_pump');
assert.equal(r({ type: 'Widget' }).model.kind, 'generic');
// every fault mapping points at real parts
for (const kind of ['lathe','motor_pump','drill_press','furnace']) {
  const model = r({ type: kind === 'motor_pump' ? 'pump' : kind === 'drill_press' ? 'drill' : kind }).model;
  for (const [f, map] of Object.entries(model.faults)) for (const id of map.parts) assert.ok(model.parts.some(p => p.id === id), `${kind}/${f}/${id}`);
  for (const f of ['Bearing Wear','Misalignment','Overheating','Electrical Fault']) {
    const dx = m.diagnoseFromFaultType(model, f, 'Critical', ['x'], 'rec');
    assert.ok(dx.parts.length > 0 && dx.steps.length === 4 && dx.severity === 'critical', `${kind} ${f}`);
  }
}
const lathe = r({ type: 'Lathe' }).model;
assert.equal(m.diagnoseFromFaultType(lathe, 'Normal', 'Normal', [], '').severity, 'normal');
assert.equal(m.diagnoseFromFaultType(lathe, 'Imbalance', 'Warning', [], 'r').parts.length, 0);
// limits
const lap = r({ domain: 'laptop' }).model;
let dx = m.diagnoseFromLimits(lap, 'laptop', { cpu_usage: 0.5, memory_usage: 0.95, swap_usage: 0.2, thermal_headroom: 0.5, battery_percent: 0.9, is_charging: 1 }, 'Degrading');
assert.deepEqual(dx.parts, ['ram']); assert.match(dx.evidence[0], /Memory use 95%/);
dx = m.diagnoseFromLimits(lap, 'laptop', { cpu_usage: 0.5, memory_usage: 0.5, battery_percent: 0.1, is_charging: 1 }, 'Stable');
assert.equal(dx.severity, 'normal', 'charging battery is not a fault');
dx = m.diagnoseFromLimits(lap, 'laptop', { battery_percent: 0.1, is_charging: 0 }, 'Stable');
assert.deepEqual(dx.parts, ['battery']);
dx = m.diagnoseFromLimits(lap, 'laptop', { thermal_headroom: 0.8 }, 'Stable');
assert.match(dx.evidence[0], /83 °C/);
const ph = r({ domain: 'mobile' }).model;
dx = m.diagnoseFromLimits(ph, 'mobile', { battery_temp: 0.7, battery_level: 0.5 }, 'Degrading');
assert.deepEqual(dx.parts, ['battery']); assert.match(dx.evidence[0], /48 °C/);
// every limit/sensor part exists
const sv = r({ domain: 'server' }).model;
for (const [model, dom, f] of [[lap,'laptop',{cpu_core_p90:1,cpu_usage:1,memory_usage:1,swap_usage:1,disk_usage:1,thermal_headroom:1,battery_percent:0,is_charging:0}],[ph,'mobile',{battery_temp:1,battery_level:0,cpu_usage:1,memory_used_percent:1}],[sv,'server',{cpu_usage:1,memory_usage:1,disk_usage:1,network_io_rate:1,gpu_utilization:1}]]) {
  const d = m.diagnoseFromLimits(model, dom, f, 'Critical');
  for (const id of d.parts) assert.ok(model.parts.some(p => p.id === id), `${dom}/${id}`);
}
// turbofan
const tf = r({ domain: 'cmapss' }).model;
const base = { s2: .4, s3: .4, s4: .4, s7: .5, s8: .3, s9: .2, s11: .3, s12: .6, s13: .2, s14: .2, s15: .3, s17: .4, s20: .5, s21: .6 };
const fleet = Array.from({ length: 9 }, (_, i) => Object.fromEntries(Object.entries(base).map(([k, v]) => [k, v + (i - 4) * 0.01])));
dx = m.diagnoseTurbofan(tf, { ...base, s4: 0.9 }, fleet, 'Critical');
assert.deepEqual(dx.parts, ['lpt']); assert.equal(dx.severity, 'critical');
dx = m.diagnoseTurbofan(tf, { ...base, s7: 0.1 }, fleet, 'Degrading');
assert.deepEqual(dx.parts, ['hpc'], 'falling P30 points at HPC');
assert.equal(m.diagnoseTurbofan(tf, base, fleet, 'Stable').severity, 'normal');
for (const s of Object.keys(base)) { const d = m.diagnoseTurbofan(tf, { ...base, [s]: base[s] + (['s7','s12','s20','s21'].includes(s) ? -0.5 : 0.5) }, fleet, 'Critical'); assert.ok(tf.parts.some(p => p.id === d.parts[0]), s); }
console.log('twin checks passed');
