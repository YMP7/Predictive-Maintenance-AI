// Android phone (147 x 71 x 8 mm) standing upright, screen toward +z. Explode spreads the stack
// along its thickness: display forward, battery and back glass behind, chips out to the sides.
import { box, cyl, mat, Rig } from '../parts';

export function buildPhone() {
  const r = new Rig();
  const W = 0.071;
  const H = 0.147;

  const frame = mat('aluminium');
  r.context(
    box(0.003, H, 0.008, frame, [-W / 2 + 0.0015, 0, 0], 0.0012),
    box(0.003, H, 0.008, frame, [W / 2 - 0.0015, 0, 0], 0.0012),
    box(W, 0.003, 0.008, frame, [0, H / 2 - 0.0015, 0], 0.0012),
    box(W, 0.003, 0.008, frame, [0, -H / 2 + 0.0015, 0], 0.0012),
    box(0.06, 0.05, 0.0008, mat('pcb'), [0, 0.042, -0.0005]));
  r.cover([0, 0, -0.07],
    box(W, H, 0.0012, mat('glass'), [0, 0, -0.0034], 0.004),
    cyl(0.006, 0.006, 0.0016, mat('darkSteel'), 'z', [-0.02, 0.055, -0.0045]),
    cyl(0.006, 0.006, 0.0016, mat('darkSteel'), 'z', [-0.02, 0.038, -0.0045]));

  r.part('battery', [0, 0, -0.04], box(0.062, 0.088, 0.0042, mat('battery'), [0, -0.024, -0.0005], 0.001));
  r.part('soc', [0, 0.01, 0.025],
    box(0.016, 0.016, 0.0012, mat('steel'), [0.006, 0.045, 0.0006]),
    box(0.012, 0.012, 0.0008, mat('chip'), [0.006, 0.045, 0.0016]));
  r.part('imu', [0.035, 0.015, 0.025], box(0.004, 0.004, 0.001, mat('chip'), [-0.017, 0.03, 0.0004]));
  r.part('compass', [-0.035, 0.015, 0.025], box(0.003, 0.003, 0.001, mat('chip'), [0.024, 0.024, 0.0004]));
  r.part('sensors', [0, 0.04, 0.035],
    box(0.008, 0.003, 0.0012, mat('chip'), [0.012, 0.068, 0.0028]),
    cyl(0.0018, 0.0018, 0.0012, mat('glass'), 'z', [-0.004, 0.068, 0.0028]));
  r.part('display', [0, 0, 0.06],
    box(W - 0.002, H - 0.002, 0.0014, mat('glass'), [0, 0, 0.0036], 0.004),
    box(W - 0.006, H - 0.008, 0.0004, mat('chip'), [0, 0, 0.0027]));

  // seen from the back three-quarter: the back glass (faded on selection) faces the camera, the display explodes away
  return r.done({ az: 2.55, el: 0.3 }, [1, 0, 0]);
}
