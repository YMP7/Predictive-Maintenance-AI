// Ported from the teardown kit (sims/kit/util.js), whaleyxbt/claude-motion, MIT licence.
// Only the helpers the Asset View uses.

export const clamp01 = (x: number) => Math.min(1, Math.max(0, x));
export const lerp = (a: number, b: number, k: number) => a + (b - a) * k;
export const easeInOutCubic = (x: number) => {
  const k = clamp01(x);
  return k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2;
};
/** Frame-rate independent approach of `current` to `target` (time constant tau seconds). */
export const damp = (current: number, target: number, tau: number, dt: number) =>
  tau <= 0 ? target : lerp(current, target, 1 - Math.exp(-dt / tau));
