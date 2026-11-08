// High-bypass two-spool turbofan, CFM56-class proportions (fan tip radius 0.86 m, ~3 m long),
// the engine type C-MAPSS simulates. Axis along x, intake at -x. The low spool (fan, LPC, LPT)
// turns with the fan speed channel; the high spool (HPC, HPT) at 1.6x. Shown slowed.
import { bladeRing, cyl, lathe, mat, Rig } from '../parts';

export function buildTurbofan() {
  const r = new Rig();

  // nacelle and core casing: the covers the cutaway opens
  r.cover([0, 1.5, 0],
    lathe([[0.9, -1.35], [0.88, -1.25], [0.88, 0.55], [0.9, 0.55], [0.97, 0.35], [1.03, -0.2], [1.04, -1.05], [1.0, -1.3], [0.93, -1.35], [0.9, -1.35]], mat('aluminium'), 'x'));
  r.cover([0, 0.75, 0],
    lathe([[0.44, -0.85], [0.43, 0.3], [0.42, 0.75], [0.36, 1.2], [0.38, 1.2], [0.44, 0.75], [0.45, 0.3], [0.47, -0.4], [0.46, -0.85], [0.44, -0.85]], mat('steel'), 'x'));
  r.context(cyl(0.045, 0.045, 2.5, mat('darkSteel'), 'x', [0.15, 0, 0]));

  const fanMat = mat('titanium');
  const fan = r.part('fan', [-0.9, 0, 0],
    lathe([[0.001, -1.32], [0.12, -1.22], [0.24, -1.05], [0.3, -0.95], [0.3, -0.88]], fanMat, 'x'),
    bladeRing(24, 0.3, 0.86, 0.26, 0.55, fanMat, -1.0, 0.012));
  r.spin(fan, 'x');

  const lpcMat = mat('steel');
  const lpc = r.part('lpc', [-0.55, 0, 0],
    lathe([[0.27, -0.8], [0.29, -0.45]], lpcMat, 'x'),
    ...[-0.75, -0.65, -0.55].map((x, i) => bladeRing(32, 0.28, 0.42 - i * 0.02, 0.06, 0.4, lpcMat, x)));
  r.spin(lpc, 'x');

  const hpcMat = mat('steel');
  const hpc = r.part('hpc', [-0.2, 0, 0],
    lathe([[0.2, -0.4], [0.2, 0.25]], hpcMat, 'x'),
    ...Array.from({ length: 9 }, (_, i) => bladeRing(40, 0.2, 0.33 - i * 0.012, 0.04, 0.35, hpcMat, -0.36 + i * 0.075, 0.004)));
  r.spin(hpc, 'x', 1.6);

  const hot = mat('hot');
  const nozzles = mat('copper');
  r.part('combustor', [0.15, 0.55, 0],
    lathe([[0.3, 0.28], [0.34, 0.32], [0.36, 0.5], [0.34, 0.58], [0.22, 0.58], [0.18, 0.55], [0.17, 0.35], [0.2, 0.28]], hot, 'x'),
    ...Array.from({ length: 20 }, (_, i) => {
      const a = (i / 20) * Math.PI * 2;
      return cyl(0.012, 0.012, 0.08, nozzles, 'x', [0.27, Math.cos(a) * 0.26, Math.sin(a) * 0.26], 12);
    }));

  const hptMat = mat('hot');
  const hpt = r.part('hpt', [0.45, 0, 0],
    lathe([[0.17, 0.6], [0.17, 0.72]], hptMat, 'x'),
    bladeRing(48, 0.17, 0.31, 0.04, -0.45, hptMat, 0.63, 0.005),
    bladeRing(48, 0.17, 0.32, 0.04, -0.45, hptMat, 0.69, 0.005));
  r.spin(hpt, 'x', 1.6);

  const lptMat = mat('titanium');
  const lpt = r.part('lpt', [0.8, 0, 0],
    lathe([[0.18, 0.75], [0.2, 1.15]], lptMat, 'x'),
    ...[0.8, 0.9, 1.0, 1.1].map((x, i) => bladeRing(56, 0.19, 0.33 + i * 0.025, 0.05, -0.4, lptMat, x, 0.004)));
  r.spin(lpt, 'x');

  r.part('nozzle', [1.15, 0, 0],
    lathe([[0.2, 1.18], [0.17, 1.4], [0.09, 1.62], [0.001, 1.7]], mat('darkSteel'), 'x'));

  return r.done({ az: -0.95, el: 0.28 });
}
