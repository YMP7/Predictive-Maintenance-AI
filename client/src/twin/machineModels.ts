// Procedural 3D models for machines attached to the platform.
// recognizeMachine() picks a model from what the platform already knows about a machine
// (registered type and name, the adapter domain it arrives through, its sensor channels),
// so a newly linked machine gets a model with no manual setup.

export type Vec3 = [number, number, number];

export interface Shape {
  k: 'box' | 'cyl' | 'torus' | 'sphere';
  // box: [x, y, z]; cyl: [radiusStart, radiusEnd, length]; torus: [radius, tube]; sphere: [radius]
  s: number[];
  p?: Vec3;
  axis?: 'x' | 'y' | 'z'; // cylinder / torus axis, default 'y'
}

export interface PartDef {
  id: string;
  name: string;
  detail: string;
  color: string;
  pos: Vec3;
  apart: Vec3;
  shapes: Shape[];
  check?: string; // what to inspect when this part is flagged by a sensor limit
}

export interface FaultMapping {
  parts: string[];
  steps?: string[];
}

export interface MachineModel {
  kind: string;
  label: string;
  parts: PartDef[];
  context?: Shape[]; // non-selectable structure (shafts, frames)
  faults?: Record<string, FaultMapping>;
}

// Muted, distinguishable part hues. Red is reserved for faults.
const C = {
  steel: '#7FA7D9',
  teal: '#6CC4B0',
  sand: '#D9B26F',
  sage: '#A7C46B',
  sky: '#8EC9E8',
  stone: '#C9C3B8',
  copper: '#D69A62',
  mint: '#9FDCC8',
};

const MOTOR_PUMP: MachineModel = {
  kind: 'motor_pump',
  label: 'Motor-driven pump',
  context: [{ k: 'cyl', s: [0.06, 0.06, 1.6], p: [0.3, 0, 0], axis: 'x' }, { k: 'box', s: [3.6, 0.08, 1], p: [0.1, -0.6, 0] }],
  parts: [
    { id: 'fan', name: 'Cooling fan', detail: 'Pulls air over the motor body', color: C.sky, pos: [-1.25, 0, 0], apart: [-0.7, 0, 0], shapes: [{ k: 'cyl', s: [0.45, 0.45, 0.4], axis: 'x' }] },
    { id: 'bearing_nde', name: 'Rear bearing', detail: 'Non-drive end, supports the shaft', color: C.sand, pos: [-0.95, 0, 0], apart: [-0.35, 0.6, 0], shapes: [{ k: 'torus', s: [0.2, 0.06], axis: 'x' }] },
    { id: 'stator', name: 'Motor body', detail: 'Stator windings turn power into rotation', color: C.steel, pos: [-0.3, 0, 0], apart: [0, 0, 0], shapes: [{ k: 'cyl', s: [0.5, 0.5, 1.1], axis: 'x' }] },
    { id: 'terminal', name: 'Terminal box', detail: 'Supply cables connect here', color: C.stone, pos: [-0.3, 0.6, 0], apart: [0, 0.6, 0], shapes: [{ k: 'box', s: [0.35, 0.22, 0.3] }] },
    { id: 'bearing_de', name: 'Front bearing', detail: 'Drive end, carries the highest load', color: C.sand, pos: [0.35, 0, 0], apart: [0, 0.65, 0], shapes: [{ k: 'torus', s: [0.2, 0.06], axis: 'x' }] },
    { id: 'coupling', name: 'Shaft coupling', detail: 'Joins motor shaft to the pump', color: C.copper, pos: [0.85, 0, 0], apart: [0.1, 0.65, 0], shapes: [{ k: 'cyl', s: [0.17, 0.17, 0.22], axis: 'x' }] },
    { id: 'pump', name: 'Pump and impeller', detail: 'Driven load', color: C.teal, pos: [1.45, 0, 0], apart: [0.75, 0, 0], shapes: [{ k: 'cyl', s: [0.42, 0.42, 0.6], axis: 'x' }, { k: 'cyl', s: [0.12, 0.12, 0.4], p: [0, 0.5, 0] }] },
  ],
  faults: {
    'Bearing Wear': { parts: ['bearing_de', 'bearing_nde'] },
    Misalignment: { parts: ['coupling'] },
    Overheating: { parts: ['fan', 'stator'] },
    'Electrical Fault': { parts: ['terminal'] },
  },
};

const LATHE: MachineModel = {
  kind: 'lathe',
  label: 'Lathe',
  context: [{ k: 'box', s: [0.25, 0.7, 0.6], p: [-1.4, -0.95, 0] }, { k: 'box', s: [0.25, 0.7, 0.6], p: [1.4, -0.95, 0] }],
  parts: [
    { id: 'bed', name: 'Bed and ways', detail: 'Rigid base the carriage slides on', color: C.stone, pos: [0, -0.5, 0], apart: [0, -0.35, 0], shapes: [{ k: 'box', s: [3.3, 0.25, 0.75] }] },
    { id: 'headstock', name: 'Headstock', detail: 'Gearbox housing for the spindle', color: C.steel, pos: [-1.2, 0.05, 0], apart: [-0.45, 0, 0], shapes: [{ k: 'box', s: [0.8, 0.85, 0.7] }] },
    { id: 'spindle_bearings', name: 'Spindle bearings', detail: 'Hold the spindle true at speed', color: C.sand, pos: [-0.7, 0.25, 0], apart: [0, 0.75, 0], shapes: [{ k: 'torus', s: [0.16, 0.05], axis: 'x' }, { k: 'torus', s: [0.16, 0.05], axis: 'x', p: [-0.25, 0, 0] }] },
    { id: 'chuck', name: 'Chuck', detail: 'Grips and spins the workpiece', color: C.sky, pos: [-0.55, 0.25, 0], apart: [0.15, 0, 0.65], shapes: [{ k: 'cyl', s: [0.32, 0.32, 0.2], axis: 'x' }] },
    { id: 'workpiece', name: 'Workpiece', detail: 'Part being turned', color: C.mint, pos: [0.15, 0.25, 0], apart: [0.2, 0.25, 0], shapes: [{ k: 'cyl', s: [0.08, 0.08, 1.2], axis: 'x' }] },
    { id: 'carriage', name: 'Carriage and tool post', detail: 'Moves the cutting tool along the work', color: C.copper, pos: [0.15, -0.2, 0.2], apart: [0, -0.05, 0.75], shapes: [{ k: 'box', s: [0.55, 0.15, 0.5] }, { k: 'box', s: [0.18, 0.25, 0.18], p: [0, 0.2, -0.05] }] },
    { id: 'tailstock', name: 'Tailstock', detail: 'Supports the far end of long work', color: C.teal, pos: [1.25, 0.0, 0], apart: [0.6, 0, 0], shapes: [{ k: 'box', s: [0.45, 0.55, 0.5] }, { k: 'cyl', s: [0.07, 0.07, 0.35], axis: 'x', p: [-0.35, 0.25, 0] }] },
    { id: 'drive_motor', name: 'Drive motor', detail: 'Powers the spindle through the gearbox', color: C.sage, pos: [-1.2, -0.95, 0], apart: [-0.4, -0.35, 0.6], shapes: [{ k: 'cyl', s: [0.22, 0.22, 0.55], axis: 'x' }] },
    { id: 'control_panel', name: 'Control panel', detail: 'Switchgear and motor drive', color: C.stone, pos: [-1.2, 0.25, 0.4], apart: [-0.3, 0.35, 0.55], shapes: [{ k: 'box', s: [0.5, 0.4, 0.08] }] },
  ],
  faults: {
    'Bearing Wear': { parts: ['spindle_bearings'] },
    Misalignment: { parts: ['tailstock'], steps: [
      'Stop the machine and lock out the power supply.',
      'Check the tailstock and spindle alignment with a test bar and dial indicator.',
      'Adjust the tailstock set-over until both ends read within the maker tolerance.',
      'Restart and confirm vibration is back under the warning limit.',
    ] },
    Overheating: { parts: ['drive_motor'] },
    'Electrical Fault': { parts: ['control_panel'] },
  },
};

const DRILL_PRESS: MachineModel = {
  kind: 'drill_press',
  label: 'Drill press',
  parts: [
    { id: 'base', name: 'Base', detail: 'Floor or bench mount', color: C.stone, pos: [0, -1.15, 0], apart: [0, -0.35, 0], shapes: [{ k: 'box', s: [1.2, 0.12, 0.9] }] },
    { id: 'column', name: 'Column', detail: 'Carries the head and table', color: C.steel, pos: [0, -0.05, -0.3], apart: [0, 0, -0.5], shapes: [{ k: 'cyl', s: [0.09, 0.09, 2.2] }] },
    { id: 'table', name: 'Work table', detail: 'Holds the part under the drill', color: C.teal, pos: [0, -0.35, 0.15], apart: [0, -0.25, 0.5], shapes: [{ k: 'box', s: [0.85, 0.07, 0.7] }] },
    { id: 'head', name: 'Head casting', detail: 'Houses the spindle and quill', color: C.sky, pos: [0, 0.75, 0.05], apart: [0, 0.2, 0], shapes: [{ k: 'box', s: [0.55, 0.45, 0.85] }] },
    { id: 'motor', name: 'Motor', detail: 'Drives the spindle by belt', color: C.sage, pos: [0, 0.95, -0.55], apart: [0, 0.3, -0.55], shapes: [{ k: 'cyl', s: [0.22, 0.22, 0.45] }] },
    { id: 'belt_cover', name: 'Belt and pulleys', detail: 'Sets the spindle speed', color: C.stone, pos: [0, 1.1, 0.0], apart: [0, 0.75, 0], shapes: [{ k: 'box', s: [0.5, 0.12, 0.95] }] },
    { id: 'spindle_bearings', name: 'Spindle bearings', detail: 'Keep the spindle running true', color: C.sand, pos: [0, 0.48, 0.3], apart: [0.6, 0.1, 0.3], shapes: [{ k: 'torus', s: [0.11, 0.04] }, { k: 'torus', s: [0.11, 0.04], p: [0, 0.18, 0] }] },
    { id: 'quill', name: 'Quill and chuck', detail: 'Feeds the drill bit down', color: C.copper, pos: [0, 0.12, 0.3], apart: [0, -0.15, 0.6], shapes: [{ k: 'cyl', s: [0.06, 0.06, 0.4] }, { k: 'cyl', s: [0.1, 0.05, 0.18], p: [0, -0.28, 0] }] },
    { id: 'switch', name: 'Switch box', detail: 'Motor starter and wiring', color: C.stone, pos: [0.36, 0.8, 0.35], apart: [0.55, 0.15, 0.2], shapes: [{ k: 'box', s: [0.12, 0.2, 0.12] }] },
  ],
  faults: {
    'Bearing Wear': { parts: ['spindle_bearings'] },
    Misalignment: { parts: ['quill'], steps: [
      'Stop the machine and lock out the power supply.',
      'Measure spindle runout with a dial indicator on a test bar in the chuck.',
      'Clean the chuck taper, reseat the chuck and replace a bent bit or worn quill.',
      'Restart and confirm vibration is back under the warning limit.',
    ] },
    Overheating: { parts: ['motor'] },
    'Electrical Fault': { parts: ['switch'] },
  },
};

const FURNACE: MachineModel = {
  kind: 'furnace',
  label: 'Industrial furnace',
  parts: [
    { id: 'chamber', name: 'Heating chamber', detail: 'Insulated refractory shell', color: C.steel, pos: [0, 0, 0], apart: [0, 0, 0], shapes: [{ k: 'box', s: [1.6, 1.3, 1.3] }] },
    { id: 'door', name: 'Door and seal', detail: 'Keeps heat in during the cycle', color: C.stone, pos: [0, 0, 0.7], apart: [0, 0, 1.0], shapes: [{ k: 'box', s: [1.2, 0.95, 0.08] }] },
    { id: 'elements', name: 'Heating elements', detail: 'Resistive coils that heat the load', color: C.copper, pos: [0, 0, 0], apart: [0, 0, 0.55], shapes: [-0.35, 0, 0.35].map(y => ({ k: 'cyl' as const, s: [0.04, 0.04, 1.3], axis: 'x' as const, p: [0, y, 0.45] as Vec3 })) },
    { id: 'thermocouple', name: 'Thermocouple', detail: 'Measures chamber temperature', color: C.sand, pos: [0.4, 0.85, 0], apart: [0, 0.55, 0], shapes: [{ k: 'cyl', s: [0.03, 0.03, 0.55] }] },
    { id: 'blower', name: 'Combustion air blower', detail: 'Fan and bearings feeding air', color: C.sky, pos: [-1.05, -0.3, 0], apart: [-0.6, 0, 0], shapes: [{ k: 'cyl', s: [0.3, 0.3, 0.35], axis: 'x' }] },
    { id: 'stack', name: 'Exhaust stack', detail: 'Carries flue gas away', color: C.sage, pos: [-0.4, 1.05, -0.3], apart: [0, 0.6, 0], shapes: [{ k: 'cyl', s: [0.14, 0.14, 0.8] }] },
    { id: 'controller', name: 'Power controller', detail: 'Switches current to the elements', color: C.teal, pos: [1.15, -0.2, 0], apart: [0.6, 0, 0], shapes: [{ k: 'box', s: [0.35, 0.85, 0.45] }] },
  ],
  faults: {
    'Bearing Wear': { parts: ['blower'] },
    Misalignment: { parts: ['blower'] },
    Overheating: { parts: ['elements', 'thermocouple'], steps: [
      'Reduce the setpoint or stop the heating cycle.',
      'Compare the thermocouple reading with a calibrated reference probe.',
      'Check the power controller is not stuck on and the elements are not shorted to the casing.',
      'Inspect the door seal and insulation for hot spots, then watch the temperature trend after restart.',
    ] },
    'Electrical Fault': { parts: ['controller'] },
  },
};

const TURBOFAN: MachineModel = {
  kind: 'turbofan',
  label: 'Turbofan engine',
  context: [{ k: 'cyl', s: [0.05, 0.05, 3.4], axis: 'x', p: [0, 0, 0] }],
  parts: [
    { id: 'fan', name: 'Fan', detail: 'Moves most of the thrust air', color: C.sky, pos: [-1.55, 0, 0], apart: [-0.7, 0, 0], shapes: [{ k: 'cyl', s: [0.9, 0.9, 0.22], axis: 'x' }, { k: 'sphere', s: [0.22], p: [-0.18, 0, 0] }], check: 'Inspect fan blades for erosion, nicks or imbalance and check fan speed trend.' },
    { id: 'bypass', name: 'Bypass duct', detail: 'Outer duct around the core', color: C.stone, pos: [-0.55, 0, 0], apart: [0, 0, 0], shapes: [{ k: 'cyl', s: [1.0, 0.95, 1.9], axis: 'x' }] },
    { id: 'lpc', name: 'Low-pressure compressor', detail: 'First stage of core compression', color: C.teal, pos: [-1.05, 0, 0], apart: [-0.3, 1.2, 0], shapes: [{ k: 'cyl', s: [0.55, 0.5, 0.45], axis: 'x' }], check: 'Borescope the LPC for fouling or blade damage.' },
    { id: 'hpc', name: 'High-pressure compressor', detail: 'Raises pressure before combustion', color: C.steel, pos: [-0.35, 0, 0], apart: [0, 1.3, 0], shapes: [{ k: 'cyl', s: [0.48, 0.34, 0.85], axis: 'x' }], check: 'Borescope the HPC for blade tip erosion and fouling; consider a compressor wash.' },
    { id: 'combustor', name: 'Combustor', detail: 'Burns fuel with compressed air', color: C.copper, pos: [0.35, 0, 0], apart: [0, -1.2, 0], shapes: [{ k: 'torus', s: [0.36, 0.12], axis: 'x' }, { k: 'cyl', s: [0.38, 0.38, 0.4], axis: 'x' }], check: 'Inspect fuel nozzles and liner for coking or burn-through.' },
    { id: 'hpt', name: 'High-pressure turbine', detail: 'Drives the compressor', color: C.sand, pos: [0.78, 0, 0], apart: [0.2, -1.25, 0], shapes: [{ k: 'cyl', s: [0.4, 0.4, 0.22], axis: 'x' }], check: 'Borescope HPT blades for thermal distress and check coolant bleed.' },
    { id: 'lpt', name: 'Low-pressure turbine', detail: 'Drives the fan', color: C.sage, pos: [1.15, 0, 0], apart: [0.45, 1.2, 0], shapes: [{ k: 'cyl', s: [0.4, 0.5, 0.5], axis: 'x' }], check: 'Borescope LPT blades and check exhaust gas temperature margin.' },
    { id: 'nozzle', name: 'Exhaust nozzle', detail: 'Accelerates core exhaust', color: C.mint, pos: [1.65, 0, 0], apart: [0.9, 0, 0], shapes: [{ k: 'cyl', s: [0.42, 0.24, 0.5], axis: 'x' }] },
  ],
};

const LAPTOP: MachineModel = {
  kind: 'laptop',
  label: 'Laptop',
  parts: [
    { id: 'chassis', name: 'Bottom chassis', detail: 'Holds the mainboard', color: C.stone, pos: [0, -0.35, 0], apart: [0, -0.4, 0], shapes: [{ k: 'box', s: [2.2, 0.08, 1.5] }] },
    { id: 'screen', name: 'Display lid', detail: 'Screen panel', color: C.steel, pos: [0, 0.35, -0.8], apart: [0, 0.3, -0.5], shapes: [{ k: 'box', s: [2.2, 1.4, 0.05] }] },
    { id: 'keyboard', name: 'Keyboard deck', detail: 'Top cover and keys', color: C.sky, pos: [0, -0.22, 0], apart: [0, 1.0, 0.3], shapes: [{ k: 'box', s: [2.1, 0.03, 1.4] }] },
    { id: 'cpu', name: 'CPU', detail: 'Processor package', color: C.copper, pos: [0.25, -0.27, -0.3], apart: [0.2, 0.45, 0], shapes: [{ k: 'box', s: [0.35, 0.05, 0.35] }], check: 'Close or reschedule the heaviest processes, then watch the CPU load trend.' },
    { id: 'ram', name: 'Memory (RAM)', detail: 'Working memory modules', color: C.teal, pos: [-0.35, -0.28, -0.3], apart: [-0.2, 0.45, 0], shapes: [{ k: 'box', s: [0.55, 0.03, 0.14], p: [0, 0, -0.1] }, { k: 'box', s: [0.55, 0.03, 0.14], p: [0, 0, 0.1] }], check: 'Close memory-heavy applications. If swap stays high, add RAM or reduce the workload.' },
    { id: 'ssd', name: 'SSD', detail: 'Storage drive', color: C.sage, pos: [-0.65, -0.28, 0.2], apart: [-0.35, 0.45, 0.2], shapes: [{ k: 'box', s: [0.6, 0.03, 0.2] }], check: 'Free disk space and keep at least 10 to 15% of the drive empty.' },
    { id: 'cooling', name: 'Fan and heatsink', detail: 'Moves heat out of the case', color: C.sky, pos: [0.75, -0.27, -0.4], apart: [0.45, 0.45, -0.1], shapes: [{ k: 'cyl', s: [0.2, 0.2, 0.06] }, { k: 'box', s: [0.6, 0.02, 0.06], p: [-0.35, 0, 0.05] }], check: 'Clean the vents and fan, use the laptop on a hard surface and watch the estimated temperature.' },
    { id: 'battery', name: 'Battery', detail: 'Lithium-ion pack', color: C.sand, pos: [0, -0.28, 0.4], apart: [0, 0.45, 0.5], shapes: [{ k: 'box', s: [1.4, 0.06, 0.4] }], check: 'Connect the charger and check the battery health report.' },
    { id: 'wifi', name: 'Wi-Fi card', detail: 'Network adapter', color: C.mint, pos: [0.75, -0.28, 0.15], apart: [0.45, 0.45, 0.2], shapes: [{ k: 'box', s: [0.22, 0.02, 0.18] }] },
  ],
};

const PHONE: MachineModel = {
  kind: 'phone',
  label: 'Smartphone',
  parts: [
    { id: 'screen', name: 'Display', detail: 'Touch screen and glass', color: C.steel, pos: [0, 0, 0.06], apart: [0, 0, 0.9], shapes: [{ k: 'box', s: [0.78, 1.58, 0.02] }] },
    { id: 'frame', name: 'Frame and back', detail: 'Housing', color: C.stone, pos: [0, 0, -0.04], apart: [0, 0, -0.8], shapes: [{ k: 'box', s: [0.82, 1.62, 0.06] }] },
    { id: 'battery', name: 'Battery', detail: 'Lithium-ion cell', color: C.sand, pos: [0, -0.25, 0.01], apart: [0, -0.15, 0.25], shapes: [{ k: 'box', s: [0.6, 0.8, 0.04] }], check: 'Stop charging and heavy use until the battery cools below 40 °C, then check charge level.' },
    { id: 'soc', name: 'Processor (SoC)', detail: 'Main chip', color: C.copper, pos: [0.1, 0.45, 0.01], apart: [0.2, 0.25, 0.45], shapes: [{ k: 'box', s: [0.2, 0.2, 0.03] }], check: 'Close background apps and check which app is using the CPU.' },
    { id: 'memory', name: 'Memory', detail: 'RAM package', color: C.teal, pos: [-0.15, 0.45, 0.01], apart: [-0.2, 0.25, 0.45], shapes: [{ k: 'box', s: [0.16, 0.16, 0.03] }], check: 'Close unused apps and clear cached data.' },
    { id: 'imu', name: 'Motion sensor', detail: 'Accelerometer and gyroscope', color: C.sage, pos: [-0.25, 0.15, 0.01], apart: [-0.45, 0, 0.3], shapes: [{ k: 'box', s: [0.08, 0.08, 0.02] }] },
    { id: 'front_sensors', name: 'Light and proximity', detail: 'Front sensor window', color: C.mint, pos: [0.15, 0.74, 0.05], apart: [0.3, 0.35, 0.6], shapes: [{ k: 'box', s: [0.14, 0.04, 0.02] }] },
    { id: 'magnetometer', name: 'Compass', detail: 'Magnetometer', color: C.sky, pos: [0.28, 0.2, 0.01], apart: [0.45, 0, 0.3], shapes: [{ k: 'box', s: [0.06, 0.06, 0.02] }] },
    { id: 'camera', name: 'Rear camera', detail: 'Camera module', color: C.stone, pos: [-0.2, 0.6, -0.08], apart: [-0.2, 0.2, -0.45], shapes: [{ k: 'cyl', s: [0.08, 0.08, 0.05], axis: 'z' }] },
  ],
};

const SERVER: MachineModel = {
  kind: 'server',
  label: 'Rack server',
  parts: [
    { id: 'chassis', name: 'Chassis', detail: '2U rack enclosure', color: C.stone, pos: [0, -0.2, 0], apart: [0, -0.35, 0], shapes: [{ k: 'box', s: [2.4, 0.06, 1.6] }, { k: 'box', s: [0.04, 0.4, 1.6], p: [-1.2, 0.2, 0] }, { k: 'box', s: [0.04, 0.4, 1.6], p: [1.2, 0.2, 0] }] },
    { id: 'cpu', name: 'CPUs and heatsinks', detail: 'Two processor sockets', color: C.copper, pos: [-0.1, 0, -0.1], apart: [0, 0.6, 0], shapes: [{ k: 'box', s: [0.35, 0.3, 0.35], p: [-0.3, 0, 0] }, { k: 'box', s: [0.35, 0.3, 0.35], p: [0.3, 0, 0] }], check: 'Find the busiest services and rebalance or scale out the load.' },
    { id: 'dimm', name: 'Memory DIMMs', detail: 'RAM banks beside each socket', color: C.teal, pos: [-0.1, -0.05, 0.35], apart: [0, 0.6, 0.4], shapes: [-0.6, -0.45, 0.45, 0.6].map(x => ({ k: 'box' as const, s: [0.04, 0.2, 0.6], p: [x, 0, -0.45] as Vec3 })) },
    { id: 'storage', name: 'Drive bays', detail: 'Front-loaded disks', color: C.sage, pos: [-0.6, -0.05, 0.7], apart: [0, 0.3, 0.6], shapes: [-0.3, 0, 0.3, 0.6, 0.9].map(x => ({ k: 'box' as const, s: [0.26, 0.25, 0.3], p: [x - 0.3, 0, 0] as Vec3 })), check: 'Free or expand storage before the volume fills.' },
    { id: 'fans', name: 'Fan wall', detail: 'Cooling airflow', color: C.sky, pos: [0, 0, 0.3], apart: [0, 0.3, 0.2], shapes: [-0.75, -0.25, 0.25, 0.75].map(x => ({ k: 'cyl' as const, s: [0.14, 0.14, 0.08], axis: 'z' as const, p: [x, 0, 0] as Vec3 })) },
    { id: 'psu', name: 'Power supplies', detail: 'Redundant PSUs', color: C.sand, pos: [0.9, -0.05, -0.55], apart: [0.5, 0.2, -0.3], shapes: [{ k: 'box', s: [0.35, 0.25, 0.45] }] },
    { id: 'nic', name: 'Network card', detail: 'Network interface', color: C.mint, pos: [-0.85, 0.0, -0.6], apart: [-0.5, 0.4, -0.3], shapes: [{ k: 'box', s: [0.4, 0.2, 0.03] }], check: 'Check link utilisation and spread traffic across interfaces.' },
    { id: 'gpu', name: 'GPU', detail: 'Accelerator card', color: C.steel, pos: [0.35, 0.0, -0.6], apart: [0.2, 0.8, -0.3], shapes: [{ k: 'box', s: [0.6, 0.22, 0.06] }], check: 'Check GPU jobs and cooling; queue work if it stays saturated.' },
  ],
};

const GENERIC: MachineModel = {
  kind: 'generic',
  label: 'Generic machine',
  parts: [
    { id: 'housing', name: 'Housing', detail: 'Main enclosure', color: C.steel, pos: [0, 0, 0], apart: [0, 0, 0], shapes: [{ k: 'box', s: [1.4, 0.9, 0.9] }] },
    { id: 'base', name: 'Mounting base', detail: 'Foundation and fixings', color: C.stone, pos: [0, -0.6, 0], apart: [0, -0.4, 0], shapes: [{ k: 'box', s: [1.8, 0.1, 1.2] }] },
    { id: 'sensor', name: 'Sensor node', detail: 'Telemetry source', color: C.sage, pos: [0, 0.6, 0], apart: [0, 0.5, 0], shapes: [{ k: 'box', s: [0.25, 0.2, 0.25] }] },
    { id: 'terminal', name: 'Terminal box', detail: 'Power and signal wiring', color: C.sand, pos: [0.85, 0, 0], apart: [0.5, 0, 0], shapes: [{ k: 'box', s: [0.25, 0.35, 0.3] }] },
  ],
};

const MODELS: Record<string, MachineModel> = Object.fromEntries(
  [MOTOR_PUMP, LATHE, DRILL_PRESS, FURNACE, TURBOFAN, LAPTOP, PHONE, SERVER, GENERIC].map(m => [m.kind, m])
);

/** Machine kinds the platform recognises (the generic fallback is left out). */
export const RECOGNISED_MODELS = Object.values(MODELS).filter(m => m.kind !== 'generic');

export const getModel = (kind: string): MachineModel => MODELS[kind] ?? MODELS.generic;

// Ordered keyword rules matched against the machine's registered type and name.
const KEYWORDS: [RegExp, string][] = [
  [/lathe|turning/i, 'lathe'],
  [/drill/i, 'drill_press'],
  [/furnace|heater|oven|kiln|boiler/i, 'furnace'],
  [/turbofan|turbine engine|jet|c-?mapss/i, 'turbofan'],
  [/pump|motor|compressor|fan|blower/i, 'motor_pump'],
  [/laptop|notebook|workstation/i, 'laptop'],
  [/phone|mobile|android|ios/i, 'phone'],
  [/server|rack|node|host/i, 'server'],
];

const DOMAIN_MODEL: Record<string, string> = { cmapss: 'turbofan', laptop: 'laptop', mobile: 'phone', server: 'server' };

export interface MachineDescriptor {
  type?: string;
  name?: string;
  domain?: string;
  channels?: string[];
}

export interface Recognition {
  model: MachineModel;
  reason: string;
}

export function recognizeMachine(d: MachineDescriptor): Recognition {
  for (const [field, value] of [['type', d.type], ['name', d.name]] as const) {
    if (!value) continue;
    const hit = KEYWORDS.find(([re]) => re.test(value));
    if (hit) return { model: MODELS[hit[1]], reason: `Matched on machine ${field} "${value}"` };
  }
  if (d.domain && DOMAIN_MODEL[d.domain]) {
    return { model: MODELS[DOMAIN_MODEL[d.domain]], reason: `Matched on the ${d.domain} adapter it is connected through` };
  }
  const ch = d.channels ?? [];
  if (ch.some(c => /vibration/i.test(c)) && ch.some(c => /current/i.test(c))) {
    return { model: MODELS.motor_pump, reason: 'Matched on its vibration and current sensors' };
  }
  return { model: MODELS.generic, reason: 'Not recognised. Showing a generic model; set a machine type to get a specific one' };
}

// ---------- Diagnosis: which parts are at fault and what to do ----------

export type Severity = 'normal' | 'warning' | 'critical';

export interface Diagnosis {
  severity: Severity;
  parts: string[];
  title: string;
  evidence: string[];
  action?: string;
  steps?: string[];
  note?: string;
}

const GENERIC_STEPS: Record<string, (parts: string) => string[]> = {
  'Bearing Wear': parts => [
    'Stop the machine and lock out the power supply.',
    `Feel and listen at the ${parts} for heat, grinding or knocking.`,
    'Regrease to the maker spec. Replace the bearing if the grease is dark or the race is pitted.',
    'Restart and confirm vibration is back under the warning limit.',
  ],
  Misalignment: parts => [
    'Stop the machine and lock out the power supply.',
    `Inspect the ${parts} for worn inserts, cracks or loose bolts.`,
    'Measure alignment with a dial indicator or laser tool and correct it to the maker tolerance.',
    'Retighten fixings, restart and confirm vibration is back under the warning limit.',
  ],
  Overheating: parts => [
    'Reduce the load, or stop the machine if the temperature is critical.',
    `Clear dust and debris from the ${parts} and any cooling vents.`,
    'Check that cooling fans turn freely and airflow paths are open.',
    'Confirm the load and room temperature are within rating, then watch the temperature trend after restart.',
  ],
  'Electrical Fault': parts => [
    'Isolate the supply, lock it out and test that the circuit is dead.',
    `Open the ${parts} and look for loose, burnt or corroded connections.`,
    'Measure the current on each phase and the insulation resistance.',
    'Tighten or replace damaged connections, restart and confirm the current draw is normal.',
  ],
};

const lower = (s: string) => s.charAt(0).toLowerCase() + s.slice(1);

export function partNames(model: MachineModel, ids: string[]): string {
  return ids.map(id => model.parts.find(p => p.id === id)?.name ?? id).join(' and ');
}

/** Shop Floor (MQTT) machines: the server already classifies the fault type. */
export function diagnoseFromFaultType(model: MachineModel, faultType: string, status: string, issues: string[], recommendation: string): Diagnosis {
  if (faultType === 'Normal') return { severity: 'normal', parts: [], title: 'No fault detected', evidence: [] };
  const severity: Severity = status === 'Critical' ? 'critical' : 'warning';
  const mapping = model.faults?.[faultType];
  if (!mapping) {
    return { severity, parts: [], title: faultType, evidence: issues, action: recommendation, note: `"${faultType}" is not mapped to a part on the ${lower(model.label)} model yet.` };
  }
  const names = lower(partNames(model, mapping.parts));
  return {
    severity,
    parts: mapping.parts,
    title: faultType,
    evidence: issues,
    action: recommendation,
    steps: mapping.steps ?? GENERIC_STEPS[faultType]?.(names),
  };
}

interface Limit {
  channel: string;
  part: string;
  limit: number;
  below?: boolean; // fault when the value drops below the limit
  label: (v: number) => string;
  when?: (f: Record<string, number>) => boolean;
}

const pct = (v: number) => `${Math.round(v * 100)}%`;

// Limits on the adapters' normalised [0, 1] channels; scales from server/adapters/*_adapter.py.
const LIMITS: Record<string, Limit[]> = {
  laptop: [
    { channel: 'cpu_core_p90', part: 'cpu', limit: 0.9, label: v => `Busiest CPU cores at ${pct(v)} (limit 90%)` },
    { channel: 'cpu_usage', part: 'cpu', limit: 0.9, label: v => `CPU load ${pct(v)} (limit 90%)` },
    { channel: 'memory_usage', part: 'ram', limit: 0.9, label: v => `Memory use ${pct(v)} (limit 90%)` },
    { channel: 'swap_usage', part: 'ram', limit: 0.8, label: v => `Swap use ${pct(v)} (limit 80%)` },
    { channel: 'disk_usage', part: 'ssd', limit: 0.9, label: v => `Disk ${pct(v)} full (limit 90%)` },
    // thermal_headroom is an estimated die temperature scaled 35 to 95 °C; 0.75 is 80 °C.
    { channel: 'thermal_headroom', part: 'cooling', limit: 0.75, label: v => `Estimated CPU temperature ${Math.round(35 + v * 60)} °C (limit 80 °C)` },
    { channel: 'battery_percent', part: 'battery', limit: 0.15, below: true, when: f => !f.is_charging, label: v => `Battery at ${pct(v)} and not charging (limit 15%)` },
  ],
  mobile: [
    // battery_temp is scaled 20 to 60 °C; 0.625 is 45 °C.
    { channel: 'battery_temp', part: 'battery', limit: 0.625, label: v => `Battery temperature ${Math.round(20 + v * 40)} °C (limit 45 °C)` },
    { channel: 'battery_level', part: 'battery', limit: 0.15, below: true, label: v => `Battery at ${pct(v)} (limit 15%)` },
    { channel: 'cpu_usage', part: 'soc', limit: 0.9, label: v => `CPU load ${pct(v)} (limit 90%)` },
    { channel: 'memory_used_percent', part: 'memory', limit: 0.9, label: v => `Memory use ${pct(v)} (limit 90%)` },
  ],
  server: [
    { channel: 'cpu_usage', part: 'cpu', limit: 0.9, label: v => `CPU load ${pct(v)} (limit 90%)` },
    { channel: 'memory_usage', part: 'dimm', limit: 0.9, label: v => `Memory use ${pct(v)} (limit 90%)` },
    { channel: 'disk_usage', part: 'storage', limit: 0.9, label: v => `Storage ${pct(v)} full (limit 90%)` },
    { channel: 'network_io_rate', part: 'nic', limit: 0.9, label: v => `Network at ${pct(v)} of capacity (limit 90%)` },
    { channel: 'gpu_utilization', part: 'gpu', limit: 0.95, label: v => `GPU load ${pct(v)} (limit 95%)` },
  ],
};

/** Laptop, mobile and server units: flag parts whose live reading is past a stated limit. */
export function diagnoseFromLimits(model: MachineModel, domain: string, features: Record<string, number>, status: string): Diagnosis {
  const scored = (LIMITS[domain] ?? [])
    .filter(l => typeof features[l.channel] === 'number' && (!l.when || l.when(features)))
    .map(l => {
      const v = features[l.channel];
      const ratio = l.below ? l.limit / Math.max(v, 1e-6) : v / l.limit;
      return { l, v, ratio };
    })
    .sort((a, b) => b.ratio - a.ratio);
  const over = scored.filter(s => s.ratio >= 1);
  if (over.length === 0) {
    const top = scored[0];
    return {
      severity: 'normal',
      parts: [],
      title: 'No part over its limit',
      evidence: [],
      note: top ? `Highest relative load: ${partNames(model, [top.l.part])}, ${lower(top.l.label(top.v))}. Overall model status: ${status}.` : undefined,
    };
  }
  const parts = [...new Set(over.map(s => s.l.part))];
  const action = model.parts.find(p => p.id === parts[0])?.check;
  return {
    severity: over.some(s => s.ratio >= 1.05) || status === 'Critical' ? 'critical' : 'warning',
    parts,
    title: 'Over limit',
    evidence: over.map(s => s.l.label(s.v)),
    action,
  };
}

// C-MAPSS FD001 sensors (Saxena et al., 2008): component and the direction each one drifts as the engine degrades.
const CMAPSS_SENSORS: Record<string, { part: string; dir: 1 | -1; name: string }> = {
  s2: { part: 'lpc', dir: 1, name: 'LPC outlet temperature (T24)' },
  s3: { part: 'hpc', dir: 1, name: 'HPC outlet temperature (T30)' },
  s4: { part: 'lpt', dir: 1, name: 'LPT outlet temperature (T50)' },
  s7: { part: 'hpc', dir: -1, name: 'HPC outlet pressure (P30)' },
  s8: { part: 'fan', dir: 1, name: 'Fan speed (Nf)' },
  s9: { part: 'hpc', dir: 1, name: 'Core speed (Nc)' },
  s11: { part: 'hpc', dir: 1, name: 'HPC static pressure (Ps30)' },
  s12: { part: 'combustor', dir: -1, name: 'Fuel flow ratio (phi)' },
  s13: { part: 'fan', dir: 1, name: 'Corrected fan speed (NRf)' },
  s14: { part: 'hpc', dir: 1, name: 'Corrected core speed (NRc)' },
  s15: { part: 'fan', dir: 1, name: 'Bypass ratio (BPR)' },
  s17: { part: 'hpc', dir: 1, name: 'Bleed enthalpy (htBleed)' },
  s20: { part: 'hpt', dir: -1, name: 'HPT coolant bleed (W31)' },
  s21: { part: 'lpt', dir: -1, name: 'LPT coolant bleed (W32)' },
};

const median = (xs: number[]) => {
  const s = [...xs].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
};

/**
 * Turbofan units: the sensor that has drifted furthest, in its degradation direction,
 * from the fleet median points to the suspected module. A heuristic, labelled as such.
 */
export function diagnoseTurbofan(model: MachineModel, features: Record<string, number>, fleet: Record<string, number>[], status: string): Diagnosis {
  if (status === 'Stable' || status === 'Normal') {
    return { severity: 'normal', parts: [], title: 'No degradation flagged', evidence: [] };
  }
  const ranked = Object.entries(CMAPSS_SENSORS)
    .filter(([s]) => typeof features[s] === 'number')
    .map(([s, meta]) => {
      const values = fleet.map(f => f[s]).filter(v => typeof v === 'number');
      const med = values.length ? median(values) : features[s];
      const spread = Math.max(values.length ? median(values.map(v => Math.abs(v - med))) : 0, 0.02);
      return { s, meta, score: (meta.dir * (features[s] - med)) / spread };
    })
    .sort((a, b) => b.score - a.score);
  const top = ranked[0];
  if (!top || top.score <= 0) {
    return { severity: 'warning', parts: [], title: 'Degradation without a clear source', evidence: [], note: 'No sensor stands out from the fleet median.' };
  }
  const part = model.parts.find(p => p.id === top.meta.part);
  return {
    severity: status === 'Critical' ? 'critical' : 'warning',
    parts: [top.meta.part],
    title: 'Suspected',
    evidence: ranked.slice(0, 3).filter(r => r.score > 0).map(r => `${r.meta.name} ${r.score.toFixed(1)}x the fleet spread past the median`),
    action: part?.check,
    note: 'Located from the sensor furthest from the fleet median. Confirm with an inspection before replacing parts.',
  };
}
