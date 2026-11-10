// The 3D Asset View: one machine on a light studio stage (the teardown kit's V8 stage, without
// post-processing), driven by the TwinFrame. The page drives it imperatively; React owns its
// lifecycle and calls dispose() on unmount. Orbit, zoom, pick a part, explode, cutaway, isolate,
// part load tints, the "Show why" attribution glow, and a tour that hands control to the visitor.
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { damp, easeInOutCubic } from './kit/util';
import { warmUp } from './kit/warm';
import { BUILDERS } from './machines';
import type { Machine, PartRig } from './parts';

export type PartState = 'normal' | 'elevated' | 'high' | 'nodata' | 'unmonitored';

export interface Colours {
  high: string;
  elevated: string;
  accent: string;
}

export interface ViewOptions {
  canvas: HTMLCanvasElement;
  callout?: HTMLElement | null;
  kind: string;
  dark: boolean;
  colours: Colours;
  reducedMotion: boolean;
  /** Kiosk: the tour starts on its own and resumes after 25 s without input. */
  autoTour: boolean;
  onSelect: (id: string | null) => void;
  onTourChange: (on: boolean) => void;
}

export interface AssetView {
  setStates(states: Record<string, PartState>): void;
  setWhy(shares: Record<string, number> | null): void;
  setSpin(speed: number | null): void;
  setSelected(id: string | null): void;
  setExplode(on: boolean): void;
  setCut(on: boolean): void;
  setIsolate(on: boolean): void;
  setTour(on: boolean): void;
  setTheme(dark: boolean, colours: Colours): void;
  resetView(): void;
  dispose(): void;
}

const FOV = 30;
const TOUR_STEP_S = 6;
const IDLE_RESUME_S = 25;
const TIERS = [
  { pr: 2, shadow: 2048 },
  { pr: 1.25, shadow: 1024 },
  { pr: 0.85, shadow: 512 },
];

// Live view count and last-second frame stats, read by the leak and performance probes.
export const probe = { live: 0, created: 0, fps: 0, calls: 0, triangles: 0, tier: 0 };
(window as unknown as { __atlas3d: typeof probe }).__atlas3d = probe;

const STUDIO = {
  light: { top: '#f3f3f4', low: '#e2e3e6', floor: '#5d636c', floorOpacity: 0.26, env: '#d9dadd', ground: '#cfd0d3' },
  dark: { top: '#24272c', low: '#16181b', floor: '#000000', floorOpacity: 0.45, env: '#6b6f76', ground: '#30343a' },
};

function backdrop(dark: boolean) {
  const s = dark ? STUDIO.dark : STUDIO.light;
  const c = document.createElement('canvas');
  c.width = 4;
  c.height = 256;
  const g = c.getContext('2d')!;
  const gr = g.createLinearGradient(0, 0, 0, 256);
  gr.addColorStop(0, s.top);
  gr.addColorStop(1, s.low);
  g.fillStyle = gr;
  g.fillRect(0, 0, 4, 256);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

// The kit's studio: a big top softbox, two side strips and a front strip for the metal to catch.
function studioEnv(renderer: THREE.WebGLRenderer, dark: boolean) {
  const env = new THREE.Scene();
  env.background = new THREE.Color(dark ? STUDIO.dark.env : STUDIO.light.env);
  const boxes: [number, number, THREE.Vector3, number][] = [
    [12, 12, new THREE.Vector3(0, 14, 2), 2.6],
    [3, 14, new THREE.Vector3(-12, 4, 6), 3.4],
    [3, 14, new THREE.Vector3(12, 4, -4), 2.2],
    [18, 2, new THREE.Vector3(0, 2, 14), 1.6],
  ];
  for (const [w, h, pos, k] of boxes) {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ color: new THREE.Color(1, 1, 1).multiplyScalar(k), side: THREE.DoubleSide }));
    m.position.copy(pos);
    m.lookAt(0, 0, 0);
    env.add(m);
  }
  const pm = new THREE.PMREMGenerator(renderer);
  const tex = pm.fromScene(env, 0.02).texture;
  pm.dispose();
  env.traverse(o => {
    if (o instanceof THREE.Mesh) {
      o.geometry.dispose();
      (o.material as THREE.Material).dispose();
    }
  });
  return tex;
}

const meshesOf = (o: THREE.Object3D) => {
  const out: THREE.Mesh[] = [];
  o.traverse(c => {
    if (c instanceof THREE.Mesh) out.push(c);
  });
  return out;
};
const materialsOf = (o: THREE.Object3D) => [...new Set(meshesOf(o).map(m => m.material as THREE.MeshStandardMaterial))];

function setOpacity(m: THREE.MeshStandardMaterial, o: number) {
  const t = o < 0.999;
  if (m.transparent !== t) {
    m.transparent = t;
    m.depthWrite = !t;
    m.needsUpdate = true;
  }
  m.opacity = o;
}

export function createAssetView(opts: ViewOptions): AssetView {
  const build = BUILDERS[opts.kind];
  if (!build) throw new Error(`No 3D model for asset kind '${opts.kind}'`);
  const { canvas } = opts;

  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
  renderer.toneMapping = THREE.NeutralToneMapping;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFShadowMap;
  renderer.localClippingEnabled = true;
  probe.live += 1;
  probe.created += 1;

  let dark = opts.dark;
  const studio = () => (dark ? STUDIO.dark : STUDIO.light);
  const scene = new THREE.Scene();
  scene.background = backdrop(dark);
  scene.environment = studioEnv(renderer, dark);
  // near-white metal blows out on the pale studio; the light theme gets less fill
  scene.environmentIntensity = dark ? 1 : 0.75;

  const camera = new THREE.PerspectiveCamera(FOV, 16 / 9, 0.01, 100);
  const sun = new THREE.DirectionalLight('#ffffff', 2.2);
  sun.position.set(-1.6, 4.2, 2.2);
  sun.castShadow = true;
  Object.assign(sun.shadow.camera, { left: -2, right: 2, top: 2, bottom: -2, near: 0.5, far: 12 });
  sun.shadow.bias = -0.0004;
  sun.shadow.normalBias = 0.01;
  const hemi = new THREE.HemisphereLight('#ffffff', studio().ground, 0.7);
  scene.add(sun, sun.target, hemi);

  // the floor: shadow only (polygonOffset keeps it from losing the depth test)
  const floorMat = new THREE.ShadowMaterial({ color: studio().floor, opacity: studio().floorOpacity, polygonOffset: true, polygonOffsetFactor: -4, polygonOffsetUnits: -8 });
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(30, 30), floorMat);
  floor.rotation.x = -Math.PI / 2;
  floor.position.y = -0.002;
  floor.receiveShadow = true;
  scene.add(floor);

  // the machine, scaled to a unit bounding sphere, standing on the floor
  const machine: Machine = build();
  const { root } = machine;
  scene.add(root);
  const bounds = new THREE.Box3().setFromObject(root);
  const sphere = bounds.getBoundingSphere(new THREE.Sphere());
  const scale = 1 / sphere.radius;
  root.scale.setScalar(scale);
  root.position.set(-sphere.center.x * scale, -bounds.min.y * scale, -sphere.center.z * scale);
  const home = new THREE.Vector3(0, (sphere.center.y - bounds.min.y) * scale, 0);

  const partList: PartRig[] = [...machine.parts.values()];
  const partMats = new Map(partList.map(p => [p.id, materialsOf(p.group)]));
  const coverMats = machine.covers.flatMap(c => materialsOf(c.group));
  const partOf = new Map<THREE.Object3D, string>();
  for (const p of partList) for (const m of meshesOf(p.group)) partOf.set(m, p.id);
  const pickables = [...partOf.keys()];
  const shellMats = [...new Set(machine.shell.flatMap(o => materialsOf(o)))];
  // removes the half on the positive side of cutNormal
  const cut = new THREE.Plane(machine.cutNormal.clone().negate(), 0);
  for (const m of shellMats) m.clipShadows = true;

  // ---------------------------------------------------------------- state
  const st = {
    explode: 0,
    explodeTo: 0,
    cut: false,
    isolate: false,
    selected: null as string | null,
    states: {} as Record<string, PartState>,
    why: null as Record<string, number> | null,
    speed: null as number | null,
    phase: 0,
    colours: opts.colours,
    tour: false,
    tourAt: 0,
    tourIdx: -1,
    // kiosk starts touring at once; elsewhere only on request
    lastInput: opts.autoTour ? -IDLE_RESUME_S : 0,
    focusTarget: home.clone(),
    focusDist: 1,
    focusing: false,
    fade: new Map<string, number>(),
  };
  // elapsed seconds and frame delta (THREE.Clock is deprecated)
  const clock = {
    elapsedTime: 0,
    last: performance.now(),
    getDelta() {
      const now = performance.now();
      const dt = (now - this.last) / 1000;
      this.last = now;
      this.elapsedTime += dt;
      return dt;
    },
  };

  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = !opts.reducedMotion;
  controls.dampingFactor = 0.08;
  controls.minDistance = 0.25;
  controls.maxDistance = 9;
  controls.maxPolarAngle = Math.PI * 0.495;

  // fit the model's height to the vertical field and its plan extent to the horizontal one (~65% fill)
  const size = bounds.getSize(new THREE.Vector3()).multiplyScalar(scale);
  const baseDist = () => {
    const tv = Math.tan(((FOV / 2) * Math.PI) / 180);
    const across = Math.max(size.x, size.z);
    const fit = Math.max(size.y / 2 / tv, across / 2 / (tv * camera.aspect));
    return (fit / 0.65 + across / 2) * (1 + 0.4 * st.explodeTo);
  };
  const resetView = () => {
    st.focusing = false;
    const { az, el } = machine.view;
    const d = baseDist();
    camera.position.set(home.x + d * Math.cos(el) * Math.sin(az), home.y + d * Math.sin(el), home.z + d * Math.cos(el) * Math.cos(az));
    controls.target.copy(home);
    controls.update();
  };

  // ---------------------------------------------------------------- appearance
  const tint = new THREE.Color();
  const applyLook = () => {
    for (const p of partList) {
      const state = st.states[p.id];
      let colour = '#000000';
      let k = 0;
      if (st.why) {
        const share = st.why[p.id] ?? 0;
        if (share > 0) {
          colour = st.colours.accent;
          k = 0.12 + 0.6 * Math.min(1, share);
        }
      } else if (state === 'high' || state === 'elevated') {
        colour = state === 'high' ? st.colours.high : st.colours.elevated;
        k = state === 'high' ? 0.55 : 0.35;
      }
      tint.set(colour);
      // a selected part keeps its context dimmed, so nothing in front of it hides it; isolate all but removes the rest
      st.fade.set(p.id, st.selected && st.selected !== p.id ? (st.isolate ? 0.12 : 0.45) : 1);
      for (const m of partMats.get(p.id)!) {
        m.emissive.copy(tint);
        m.emissiveIntensity = k;
      }
    }
    for (const m of shellMats) {
      m.clippingPlanes = st.cut ? [cut] : null;
      m.needsUpdate = true;
    }
    // covers step aside for a selected part, and all but vanish when it is isolated
    for (const m of coverMats) setOpacity(m, st.selected ? (st.isolate ? 0.06 : 0.2) : 1);
  };

  // ---------------------------------------------------------------- picking
  const ray = new THREE.Raycaster();
  const ndc = new THREE.Vector2();
  let down: { x: number; y: number } | null = null;
  const pick = (cx: number, cy: number): string | null => {
    const r = canvas.getBoundingClientRect();
    ndc.set(((cx - r.left) / r.width) * 2 - 1, -((cy - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(ndc, camera);
    const hit = ray.intersectObjects(pickables, false).find(h => (st.fade.get(partOf.get(h.object)!) ?? 1) > 0.3); // isolated-away parts (0.12) cannot be picked; dimmed ones (0.45) can
    return hit ? (partOf.get(hit.object) ?? null) : null;
  };
  const userInput = () => {
    st.lastInput = clock.elapsedTime;
    st.focusing = false;
    if (st.tour) {
      st.tour = false;
      opts.onTourChange(false);
    }
  };
  const onDown = (e: PointerEvent) => {
    down = { x: e.clientX, y: e.clientY };
    userInput();
  };
  const onUp = (e: PointerEvent) => {
    if (down && Math.hypot(e.clientX - down.x, e.clientY - down.y) < 5) {
      const id = pick(e.clientX, e.clientY);
      api.setSelected(id);
      opts.onSelect(id);
    }
    down = null;
  };
  let hoverAt = 0;
  const onMove = (e: PointerEvent) => {
    if (down || performance.now() - hoverAt < 60) return;
    hoverAt = performance.now();
    canvas.style.cursor = pick(e.clientX, e.clientY) ? 'pointer' : 'grab';
  };
  canvas.addEventListener('pointerdown', onDown);
  canvas.addEventListener('pointerup', onUp);
  canvas.addEventListener('pointermove', onMove);
  canvas.addEventListener('wheel', userInput, { passive: true });

  // ---------------------------------------------------------------- focus and callout
  const tmpBox = new THREE.Box3();
  const tmpV = new THREE.Vector3();
  const tmpS = new THREE.Vector3();
  const partCentre = (id: string, out: THREE.Vector3) => {
    const p = machine.parts.get(id);
    if (!p) return null;
    tmpBox.setFromObject(p.group).getCenter(out);
    return tmpBox.getSize(tmpS).length() / 2;
  };
  const focusOn = (id: string | null) => {
    if (!id) {
      st.focusTarget.copy(home);
      st.focusDist = baseDist();
    } else {
      const r = partCentre(id, st.focusTarget) ?? 0.3;
      st.focusDist = Math.min(baseDist(), Math.max(0.55 * baseDist(), r * 5));
    }
    st.focusing = true;
    if (opts.reducedMotion) {
      const dir = camera.position.clone().sub(controls.target).normalize();
      controls.target.copy(st.focusTarget);
      camera.position.copy(st.focusTarget).addScaledVector(dir, st.focusDist);
      st.focusing = false;
    }
  };
  const placeCallout = () => {
    const el = opts.callout;
    if (!el) return;
    if (!st.selected || partCentre(st.selected, tmpV) === null) {
      el.dataset.visible = 'false';
      return;
    }
    tmpV.project(camera);
    const w = canvas.clientWidth;
    const x = (tmpV.x * 0.5 + 0.5) * w;
    const y = (-tmpV.y * 0.5 + 0.5) * canvas.clientHeight;
    el.dataset.visible = tmpV.z < 1 ? 'true' : 'false';
    el.dataset.side = x > w * 0.62 ? 'left' : 'right';
    el.style.transform = `translate(${Math.round(x)}px, ${Math.round(y)}px)`;
  };

  // ---------------------------------------------------------------- tour
  const tourStep = () => {
    const order = partList.map(p => p.id).filter(id => st.states[id] !== 'unmonitored');
    if (!order.length) return;
    st.tourIdx = (st.tourIdx + 1) % order.length;
    st.explodeTo = 1;
    api.setSelected(order[st.tourIdx]);
    opts.onSelect(order[st.tourIdx]);
  };

  // ---------------------------------------------------------------- size, tiers, loop
  const resize = () => {
    const w = canvas.clientWidth || 1;
    const h = canvas.clientHeight || 1;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  };
  let tier = matchMedia('(pointer: coarse)').matches || Math.min(innerWidth, innerHeight) < 700 ? 1 : 0;
  const applyTier = () => {
    const t = TIERS[tier];
    renderer.setPixelRatio(Math.min(devicePixelRatio || 1, t.pr));
    sun.shadow.mapSize.set(t.shadow, t.shadow);
    sun.shadow.map?.dispose();
    sun.shadow.map = null;
    probe.tier = tier;
    resize();
  };
  const ro = new ResizeObserver(resize);
  ro.observe(canvas);

  let frames = 0;
  let windowStart = 0;
  let raf = 0;
  let running = true;
  const up = new THREE.Vector3(0, 1, 0);
  const off = new THREE.Vector3();

  const frame = () => {
    if (!running) return;
    raf = requestAnimationFrame(frame);
    if (document.hidden) return;
    const dt = Math.min(0.1, clock.getDelta());
    const t = clock.elapsedTime;

    // explode, eased; parts and covers slide along their apart vectors
    st.explode = opts.reducedMotion ? st.explodeTo : damp(st.explode, st.explodeTo, 0.18, dt);
    const k = easeInOutCubic(st.explode);
    for (const p of partList) p.group.position.copy(p.apart).multiplyScalar(k);
    for (const c of machine.covers) c.group.position.copy(c.apart).multiplyScalar(k);

    // rotation from the measured speed channel; nothing turns without one
    if (st.speed !== null && !opts.reducedMotion) {
      st.phase += dt * Math.PI * 2 * (0.08 + 0.5 * st.speed);
      for (const s of machine.spinners) s.obj.rotation[s.axis] = st.phase * s.ratio;
    }

    for (const p of partList) {
      const target = st.fade.get(p.id) ?? 1;
      for (const m of partMats.get(p.id)!) if (m.opacity !== target) setOpacity(m, opts.reducedMotion ? target : damp(m.opacity, target, 0.12, dt));
    }

    // tour: step through the monitored parts, a slow orbit in between
    if (opts.autoTour && !st.tour && t - st.lastInput > IDLE_RESUME_S) {
      st.tour = true;
      st.tourAt = t - TOUR_STEP_S;
      opts.onTourChange(true);
    }
    if (st.tour) {
      if (t - st.tourAt >= TOUR_STEP_S) {
        st.tourAt = t;
        tourStep();
      }
      if (!opts.reducedMotion) {
        off.copy(camera.position).sub(controls.target).applyAxisAngle(up, dt * 0.12);
        camera.position.copy(controls.target).add(off);
      }
    }

    if (st.focusing) {
      controls.target.x = damp(controls.target.x, st.focusTarget.x, 0.25, dt);
      controls.target.y = damp(controls.target.y, st.focusTarget.y, 0.25, dt);
      controls.target.z = damp(controls.target.z, st.focusTarget.z, 0.25, dt);
      off.copy(camera.position).sub(controls.target);
      off.setLength(damp(off.length(), st.focusDist, 0.25, dt));
      camera.position.copy(controls.target).add(off);
      if (controls.target.distanceTo(st.focusTarget) < 1e-3 && Math.abs(off.length() - st.focusDist) < 1e-3) st.focusing = false;
    }
    controls.update();
    renderer.render(scene, camera);
    placeCallout();

    // performance probe; one step down a tier when the GPU cannot keep up
    frames += 1;
    if (t - windowStart >= 1) {
      probe.fps = Math.round(frames / (t - windowStart));
      probe.calls = renderer.info.render.calls;
      probe.triangles = renderer.info.render.triangles;
      // below 25 fps only: browsers and 30 Hz displays that cap rAF at 30 are not a slow GPU
      if (probe.fps < 25 && tier < TIERS.length - 1 && t > 3) {
        tier += 1;
        applyTier();
      }
      frames = 0;
      windowStart = t;
    }
  };

  // ---------------------------------------------------------------- api
  const api: AssetView = {
    setStates(states) {
      st.states = states;
      applyLook();
    },
    setWhy(shares) {
      st.why = shares;
      applyLook();
    },
    setSpin(speed) {
      st.speed = speed;
    },
    setSelected(id) {
      st.selected = id && machine.parts.has(id) ? id : null;
      applyLook();
      focusOn(st.selected);
    },
    setExplode(on) {
      st.explodeTo = on ? 1 : 0;
      if (!st.selected) focusOn(null);
    },
    setCut(on) {
      st.cut = on;
      applyLook();
    },
    setIsolate(on) {
      st.isolate = on;
      applyLook();
    },
    setTour(on) {
      if (on === st.tour) return; // the page echoes the view's own changes back; keep the idle clock
      st.tour = on;
      st.lastInput = clock.elapsedTime;
      if (on) {
        st.tourAt = clock.elapsedTime - TOUR_STEP_S;
        st.tourIdx = -1;
      }
    },
    setTheme(isDark, colours) {
      st.colours = colours;
      if (isDark !== dark) {
        dark = isDark;
        (scene.background as THREE.Texture).dispose();
        scene.background = backdrop(dark);
        scene.environment?.dispose();
        scene.environment = studioEnv(renderer, dark);
        scene.environmentIntensity = dark ? 1 : 0.75;
        hemi.groundColor.set(studio().ground);
        floorMat.color.set(studio().floor);
        floorMat.opacity = studio().floorOpacity;
      }
      applyLook();
    },
    resetView,
    dispose() {
      running = false;
      cancelAnimationFrame(raf);
      ro.disconnect();
      canvas.removeEventListener('pointerdown', onDown);
      canvas.removeEventListener('pointerup', onUp);
      canvas.removeEventListener('pointermove', onMove);
      canvas.removeEventListener('wheel', userInput);
      controls.dispose();
      probe.live -= 1;
      // compileAsync polls the programs on a timer: free GPU resources only once it has settled
      warming.finally(() => {
        scene.traverse(o => {
          if (o instanceof THREE.Mesh) {
            o.geometry.dispose();
            (Array.isArray(o.material) ? o.material : [o.material]).forEach(m => m.dispose());
          }
        });
        (scene.background as THREE.Texture | null)?.dispose();
        scene.environment?.dispose();
        sun.shadow.map?.dispose();
        renderer.dispose();
        renderer.forceContextLoss();
      });
    },
  };

  applyTier();
  resetView();
  applyLook();
  const warming = warmUp(renderer, scene, camera)
    .catch(() => undefined)
    .finally(() => {
      if (running) raf = requestAnimationFrame(frame);
    });
  return api;
}
