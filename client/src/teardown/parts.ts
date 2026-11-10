// Geometry and material helpers shared by the five machines. Parts are built from code
// (lathed shells, rounded boxes, instanced blades) in metres, like the teardown kit's machines.
import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';

export type Axis = 'x' | 'y' | 'z';
type V3 = [number, number, number];

export interface PartRig {
  id: string;
  group: THREE.Group;
  /** Offset applied at full explode. */
  apart: THREE.Vector3;
}

export interface Spinner {
  obj: THREE.Object3D;
  axis: Axis;
  /** Turns per turn of the driving shaft (a spool or gear ratio). */
  ratio: number;
}

export interface Machine {
  root: THREE.Group;
  parts: Map<string, PartRig>;
  covers: PartRig[];
  spinners: Spinner[];
  /** Objects the cutaway clips in half. */
  shell: THREE.Object3D[];
  /** Plane normal for the cutaway (the half on the positive side is removed). */
  cutNormal: THREE.Vector3;
  /** Default camera: azimuth and elevation in radians. */
  view: { az: number; el: number };
}

// Matte enough (roughness >= 0.45 on big surfaces) not to streak under the studio lights.
const FINISH = {
  steel: { color: '#9aa0a6', metalness: 0.85, roughness: 0.45 },
  darkSteel: { color: '#4b5057', metalness: 0.8, roughness: 0.5 },
  titanium: { color: '#8f8b83', metalness: 0.9, roughness: 0.45 },
  hot: { color: '#8a6a4f', metalness: 0.7, roughness: 0.55 },
  aluminium: { color: '#aeb2b7', metalness: 0.7, roughness: 0.5 },
  paint: { color: '#5d7488', metalness: 0.2, roughness: 0.6 },
  plastic: { color: '#2b2e33', metalness: 0.0, roughness: 0.65 },
  plasticLight: { color: '#d9dadc', metalness: 0.0, roughness: 0.6 },
  pcb: { color: '#2f4a3c', metalness: 0.1, roughness: 0.7 },
  chip: { color: '#1d1f22', metalness: 0.2, roughness: 0.5 },
  copper: { color: '#b4734a', metalness: 0.9, roughness: 0.45 },
  glass: { color: '#11161c', metalness: 0.0, roughness: 0.15 },
  battery: { color: '#3a3f46', metalness: 0.3, roughness: 0.6 },
} as const;
export type Finish = keyof typeof FINISH;

/** A fresh material per call, so each part can be tinted and faded on its own. */
export const mat = (f: Finish) => new THREE.MeshStandardMaterial({ ...FINISH[f], envMapIntensity: 0.6 });

const AXIS_ROT: Record<Axis, V3> = { x: [0, 0, -Math.PI / 2], y: [0, 0, 0], z: [Math.PI / 2, 0, 0] };

function place<T extends THREE.Object3D>(m: T, p: V3 = [0, 0, 0], axis: Axis = 'y') {
  m.position.set(...p);
  m.rotation.set(...AXIS_ROT[axis]);
  m.castShadow = true;
  m.receiveShadow = true;
  return m;
}

/** Turned shell from [radius, height] points; its axis runs along `axis`. Heights grow toward +axis. */
export function lathe(profile: [number, number][], material: THREE.Material, axis: Axis = 'x', p?: V3, seg = 64) {
  // LatheGeometry turns about +y; the -90 deg z turn in place() maps +y onto +x
  const g = new THREE.LatheGeometry(profile.map(([r, h]) => new THREE.Vector2(r, h)), seg);
  material.side = THREE.DoubleSide; // open shells are seen from inside once cut
  return place(new THREE.Mesh(g, material), p, axis);
}

export function cyl(r0: number, r1: number, h: number, material: THREE.Material, axis: Axis = 'y', p?: V3, seg = 40) {
  return place(new THREE.Mesh(new THREE.CylinderGeometry(r0, r1, h, seg), material), p, axis);
}

export function box(w: number, h: number, d: number, material: THREE.Material, p?: V3, radius = 0) {
  const g = radius > 0 ? new RoundedBoxGeometry(w, h, d, 2, radius) : new THREE.BoxGeometry(w, h, d);
  return place(new THREE.Mesh(g, material), p);
}

export function torus(r: number, tube: number, material: THREE.Material, axis: Axis = 'x', p?: V3) {
  const m = new THREE.Mesh(new THREE.TorusGeometry(r, tube, 16, 48), material);
  m.position.set(...(p ?? [0, 0, 0]));
  if (axis === 'x') m.rotation.y = Math.PI / 2;
  if (axis === 'y') m.rotation.x = Math.PI / 2;
  m.castShadow = true;
  return m;
}

/** n blades around the x axis at station x, one draw call. Twist in radians about the blade's span. */
export function bladeRing(n: number, rIn: number, rOut: number, chord: number, twist: number, material: THREE.Material, x = 0, thick = 0.006) {
  const g = new THREE.BoxGeometry(thick, rOut - rIn, chord);
  g.rotateY(twist);
  g.translate(0, (rIn + rOut) / 2, 0);
  const ring = new THREE.InstancedMesh(g, material, n);
  const m4 = new THREE.Matrix4();
  const q = new THREE.Quaternion();
  const s = new THREE.Vector3(1, 1, 1);
  for (let i = 0; i < n; i++) {
    q.setFromAxisAngle(new THREE.Vector3(1, 0, 0), (i / n) * Math.PI * 2);
    m4.compose(new THREE.Vector3(x, 0, 0), q, s);
    ring.setMatrixAt(i, m4);
  }
  ring.castShadow = true;
  return ring;
}

/** n copies of a box along a step, one draw call (fins, DIMMs, drive sleds). */
export function row(n: number, size: V3, step: V3, start: V3, material: THREE.Material) {
  const im = new THREE.InstancedMesh(new THREE.BoxGeometry(...size), material, n);
  const m4 = new THREE.Matrix4();
  for (let i = 0; i < n; i++) {
    m4.makeTranslation(start[0] + step[0] * i, start[1] + step[1] * i, start[2] + step[2] * i);
    im.setMatrixAt(i, m4);
  }
  im.castShadow = true;
  im.receiveShadow = true;
  return im;
}

/** n cooling ribs running along the x axis at radius r (a cast motor frame), one draw call. */
export function ribs(n: number, length: number, r: number, height: number, material: THREE.Material, x = 0) {
  const g = new THREE.BoxGeometry(length, height, 0.006);
  g.translate(0, r + height / 2, 0);
  const im = new THREE.InstancedMesh(g, material, n);
  const m4 = new THREE.Matrix4();
  for (let i = 0; i < n; i++) {
    m4.makeRotationX((i / n) * Math.PI * 2).setPosition(x, 0, 0);
    im.setMatrixAt(i, m4);
  }
  im.castShadow = true;
  return im;
}

/** A fan rotor (hub + n flat blades) about `axis`, one group. */
export function fanRotor(n: number, r: number, hubR: number, depth: number, material: THREE.Material, axis: Axis) {
  const g = new THREE.Group();
  g.add(cyl(hubR, hubR, depth, material, 'y'));
  const blade = new THREE.BoxGeometry(r - hubR, depth * 0.8, 0.004);
  blade.translate((r + hubR) / 2, 0, 0);
  blade.rotateX(0.5);
  const im = new THREE.InstancedMesh(blade, material, n);
  const m4 = new THREE.Matrix4();
  for (let i = 0; i < n; i++) {
    m4.makeRotationY((i / n) * Math.PI * 2);
    im.setMatrixAt(i, m4);
  }
  g.add(im);
  const outer = new THREE.Group();
  outer.add(g);
  outer.rotation.set(...AXIS_ROT[axis]);
  return { rotor: outer, spinAxis: 'y' as Axis, inner: g };
}

export class Rig {
  root = new THREE.Group();
  parts = new Map<string, PartRig>();
  spinners: Spinner[] = [];
  shell: THREE.Object3D[] = [];

  part(id: string, apart: V3, ...children: THREE.Object3D[]) {
    const group = new THREE.Group();
    group.name = id;
    group.add(...children);
    this.root.add(group);
    this.parts.set(id, { id, group, apart: new THREE.Vector3(...apart) });
    return group;
  }

  context(...children: THREE.Object3D[]) {
    this.root.add(...children);
  }

  covers: PartRig[] = [];

  /** Outer covers: not selectable, cut in half by the cutaway, moved by `apart` on explode. */
  cover(apart: V3, ...children: THREE.Object3D[]) {
    const group = new THREE.Group();
    group.add(...children);
    this.root.add(group);
    this.covers.push({ id: 'cover', group, apart: new THREE.Vector3(...apart) });
    this.shell.push(...children);
  }

  /** Mark objects inside a part as cut by the cutaway (a pump casing around its impeller). */
  clip(...objs: THREE.Object3D[]) {
    this.shell.push(...objs);
  }

  spin(obj: THREE.Object3D, axis: Axis, ratio = 1) {
    this.spinners.push({ obj, axis, ratio });
    return obj;
  }

  done(view: Machine['view'], cutNormal: V3 = [0, 0, 1]): Machine {
    return { root: this.root, parts: this.parts, covers: this.covers, spinners: this.spinners, shell: this.shell, cutNormal: new THREE.Vector3(...cutNormal), view };
  }
}
