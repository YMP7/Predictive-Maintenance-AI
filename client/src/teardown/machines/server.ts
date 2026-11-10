// 2U rack server (440 x 87 x 700 mm), front toward +z: twelve 3.5-inch bays, a fan wall,
// two sockets under fin heat sinks with eight DIMMs each, a riser GPU, a NIC and two power
// supplies at the rear. The cutaway takes half the lid off; explode lifts each module.
import { box, fanRotor, mat, Rig, row } from '../parts';

export function buildServer() {
  const r = new Rig();
  const W = 0.44;
  const H = 0.087;
  const D = 0.7;

  const sheet = mat('darkSteel');
  r.context(
    box(W, 0.002, D, sheet, [0, 0.001, 0]),
    box(0.002, H, D, sheet, [-W / 2, H / 2, 0]),
    box(0.002, H, D, sheet, [W / 2, H / 2, 0]),
    box(W - 0.02, 0.0016, 0.36, mat('pcb'), [0, 0.004, -0.15]));
  r.cover([0, 0.45, 0], box(W, 0.002, D, mat('steel'), [0, H, 0]));

  const sled = mat('plastic');
  r.part('storage', [0, 0, 0.22],
    ...[0.016, 0.044, 0.072].map(y => row(4, [0.102, 0.026, 0.15], [0.106, 0, 0], [-0.159, y, 0.27], sled)));

  const fanMat = mat('plastic');
  const fans = r.part('fans', [0, 0.12, 0.08], row(6, [0.068, 0.07, 0.038], [0.07, 0, 0], [-0.175, 0.04, 0.13], mat('darkSteel')));
  for (let i = 0; i < 6; i++) {
    const f = fanRotor(7, 0.03, 0.012, 0.02, fanMat, 'z');
    f.rotor.position.set(-0.175 + i * 0.07, 0.04, 0.152);
    fans.add(f.rotor);
  }

  const fin = mat('aluminium');
  const base = mat('copper');
  r.part('cpu', [0, 0.16, 0],
    ...[-0.09, 0.09].flatMap(x => [
      box(0.09, 0.006, 0.1, base, [x, 0.009, -0.02]),
      row(30, [0.0008, 0.05, 0.1], [0.003, 0, 0], [x - 0.0435, 0.037, -0.02], fin),
    ]));

  const dimm = mat('pcb');
  r.part('memory', [0, 0.1, -0.06],
    ...[-0.17, -0.0145, 0.0305, 0.15].map(x => row(4, [0.004, 0.032, 0.133], [0.009, 0, 0], [x, 0.021, -0.02], dimm)));

  r.part('gpu', [-0.05, 0.2, -0.1],
    box(0.24, 0.018, 0.11, mat('darkSteel'), [-0.09, 0.066, -0.24]),
    box(0.2, 0.004, 0.1, mat('pcb'), [-0.09, 0.055, -0.24]));
  r.part('nic', [0, 0.12, -0.12],
    box(0.068, 0.002, 0.12, mat('pcb'), [0.06, 0.03, -0.28]),
    box(0.03, 0.012, 0.02, mat('steel'), [0.06, 0.038, -0.34]));
  r.part('psu', [0.08, 0.05, -0.2],
    row(2, [0.086, 0.04, 0.22], [0, 0.042, 0], [0.165, 0.022, -0.235], mat('steel')));

  return r.done({ az: 0.7, el: 0.55 }, [1, 0, 0]);
}
