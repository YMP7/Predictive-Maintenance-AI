// Ported from the teardown kit (sims/kit/warm.js), whaleyxbt/claude-motion, MIT licence.
// Compiles every shader program of the scene in parallel before the first frame
// (renderer.compileAsync, KHR_parallel_shader_compile), so the page never freezes on its
// first draw. The kit also warms post-processing passes; the Asset View draws without post.
import type * as THREE from 'three';

export function warmUp(renderer: THREE.WebGLRenderer, scene: THREE.Scene, camera: THREE.Camera) {
  // the stage uses PCFShadowMap from the start: three swaps PCFSoft for it on the first shadow render, after any warm-up
  return renderer.compileAsync(scene, camera);
}
