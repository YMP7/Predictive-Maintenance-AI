// Close-coupled pump set: an IEC 132-frame TEFC motor (shaft height 132 mm) driving an
// end-suction centrifugal pump through a jaw coupling, on a common base plate. Shaft along x,
// pump at +x. Shaft, fan, coupling and impeller turn with the measured shaft speed, shown slowed.
// The cutaway halves the motor frame, the fan cowl and the pump volute.
import * as THREE from 'three';
import { box, cyl, fanRotor, lathe, mat, ribs, Rig, torus } from '../parts';

const Y = 0.132; // shaft height

/** A group on the shaft line, so spinning it about x turns its children about the shaft. */
const axle = (...children: THREE.Object3D[]) => {
  const g = new THREE.Group();
  g.position.y = Y;
  g.add(...children);
  return g;
};

export function buildMotorPump() {
  const r = new Rig();

  r.context(
    box(1.0, 0.03, 0.34, mat('paint'), [-0.15, 0.015, 0]),
    box(0.2, Y - 0.1, 0.2, mat('paint'), [-0.37, 0.03 + (Y - 0.1) / 2, 0]),
    box(0.12, Y - 0.1, 0.16, mat('paint'), [0.17, 0.03 + (Y - 0.1) / 2, 0]));
  r.context(r.spin(axle(cyl(0.021, 0.021, 0.72, mat('steel'), 'x', [-0.24, 0, 0])), 'x'));

  const frame = mat('paint');
  const housing = [cyl(0.12, 0.12, 0.34, frame, 'x', [-0.37, Y, 0]), ribs(20, 0.3, 0.12, 0.018, frame, -0.37)];
  housing[1].position.y = Y;
  r.part('stator', [0, 0.25, 0], ...housing, cyl(0.11, 0.11, 0.33, mat('copper'), 'x', [-0.37, Y, 0]));
  r.clip(...housing);

  const cowl = lathe([[0.15, 0], [0.15, 0.1], [0.13, 0.13], [0.03, 0.14]], mat('paint'), 'x', [-0.68, Y, 0]);
  const fan = fanRotor(9, 0.12, 0.03, 0.04, mat('plastic'), 'x');
  fan.rotor.position.set(-0.6, Y, 0);
  r.part('fan', [-0.35, 0, 0], cowl, fan.rotor);
  r.spin(fan.inner, 'y');
  r.clip(cowl);

  r.part('bearing_nde', [-0.2, 0.15, 0], torus(0.04, 0.014, mat('steel'), 'x', [-0.55, Y, 0]));
  r.part('bearing_de', [0, 0.15, 0.12], torus(0.04, 0.014, mat('steel'), 'x', [-0.19, Y, 0]));
  r.part('terminal', [0, 0.32, 0],
    box(0.13, 0.08, 0.13, frame, [-0.4, Y + 0.16, 0], 0.006),
    cyl(0.012, 0.012, 0.04, mat('plastic'), 'z', [-0.4, Y + 0.15, 0.08]));

  const hub = mat('darkSteel');
  r.part('coupling', [0.06, 0.18, 0], r.spin(axle(
    cyl(0.05, 0.05, 0.045, hub, 'x', [-0.115, 0, 0]),
    cyl(0.05, 0.05, 0.045, hub, 'x', [-0.06, 0, 0]),
    cyl(0.046, 0.046, 0.012, mat('plastic'), 'x', [-0.0875, 0, 0])), 'x'));

  const volute = mat('paint');
  const casing = [
    torus(0.15, 0.07, volute, 'x', [0.15, Y, 0]),
    cyl(0.2, 0.2, 0.03, volute, 'x', [0.1, Y, 0]),
    cyl(0.055, 0.055, 0.17, volute, 'y', [0.15, Y + 0.24, 0]),
    cyl(0.06, 0.06, 0.15, volute, 'x', [0.29, Y, 0]),
  ];
  const impeller = fanRotor(6, 0.14, 0.04, 0.03, mat('copper'), 'x');
  impeller.rotor.position.set(0.15, Y, 0);
  r.part('pump', [0.3, 0, 0], ...casing, impeller.rotor);
  r.spin(impeller.inner, 'y');
  r.clip(casing[0], casing[1]);

  return r.done({ az: 0.75, el: 0.35 });
}
