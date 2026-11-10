// 14-inch laptop (313 x 221 x 16 mm), lid open at 105 degrees. x across, z toward the viewer,
// y up. The cutaway takes the right half of the keyboard deck off; explode lifts each layer.
import * as THREE from 'three';
import { box, cyl, fanRotor, mat, Rig, row } from '../parts';

export function buildLaptop() {
  const r = new Rig();
  const W = 0.313;
  const D = 0.221;

  r.context(box(W, 0.004, D, mat('aluminium'), [0, 0.002, 0], 0.0015));
  r.context(box(0.2, 0.0012, 0.09, mat('pcb'), [0.02, 0.0055, -0.06]));
  // keyboard deck: the cover
  const keys = mat('plastic');
  r.cover([0, 0.09, 0],
    box(W, 0.004, D, mat('aluminium'), [0, 0.0135, 0], 0.0015),
    row(14, [0.016, 0.0012, 0.016], [0.019, 0, 0], [-0.123, 0.0162, -0.075], keys),
    row(14, [0.016, 0.0012, 0.016], [0.019, 0, 0], [-0.123, 0.0162, -0.055], keys),
    row(13, [0.016, 0.0012, 0.016], [0.019, 0, 0], [-0.114, 0.0162, -0.035], keys),
    box(0.11, 0.0008, 0.065, mat('glass'), [0, 0.016, 0.055], 0.002));

  r.part('cpu', [0, 0.05, 0],
    box(0.035, 0.0015, 0.035, mat('pcb'), [0, 0.0068, -0.06]),
    box(0.024, 0.0015, 0.024, mat('chip'), [0, 0.0082, -0.06]));

  const pipe = mat('copper');
  const blower = fanRotor(31, 0.028, 0.012, 0.006, mat('plastic'), 'y');
  blower.rotor.position.set(0.105, 0.009, -0.075);
  r.part('cooling', [0.02, 0.07, -0.01],
    box(0.03, 0.0015, 0.03, pipe, [0, 0.0098, -0.06]),
    box(0.085, 0.002, 0.007, pipe, [0.055, 0.0098, -0.066]),
    box(0.085, 0.002, 0.007, pipe, [0.055, 0.0098, -0.054]),
    cyl(0.033, 0.033, 0.0015, mat('darkSteel'), 'y', [0.105, 0.0118, -0.075]),
    blower.rotor);

  r.part('memory', [-0.02, 0.045, -0.03],
    row(2, [0.067, 0.0012, 0.03], [0, 0.0016, 0], [-0.075, 0.0068, -0.07], mat('pcb')),
    row(8, [0.008, 0.0009, 0.006], [0.0075, 0, 0], [-0.101, 0.0089, -0.07], mat('chip')));

  r.part('storage', [0, 0.04, 0.03],
    box(0.08, 0.0012, 0.022, mat('pcb'), [0.06, 0.0068, -0.005]),
    box(0.026, 0.0012, 0.016, mat('chip'), [0.04, 0.008, -0.005]),
    box(0.024, 0.0012, 0.016, mat('chip'), [0.075, 0.008, -0.005]));

  r.part('wifi', [-0.03, 0.04, 0.02],
    box(0.03, 0.0012, 0.022, mat('pcb'), [-0.085, 0.0068, -0.005]),
    box(0.012, 0.0014, 0.012, mat('steel'), [-0.085, 0.0083, -0.005]));

  r.part('battery', [0, 0.02, 0.06], box(0.26, 0.006, 0.075, mat('battery'), [0, 0.0072, 0.065], 0.002));

  const lid = new THREE.Group();
  lid.position.set(0, 0.016, -D / 2);
  lid.rotation.x = -(105 * Math.PI) / 180;
  lid.add(box(W, 0.005, D - 0.006, mat('aluminium'), [0, 0.0025, (D - 0.006) / 2], 0.0015));
  lid.add(box(W - 0.012, 0.0008, D - 0.03, mat('glass'), [0, -0.0004, (D - 0.006) / 2]));
  r.part('display', [0, 0.02, -0.05], lid);

  return r.done({ az: 0.55, el: 0.45 }, [1, 0, 0]);
}
