import { useEffect, useMemo, useRef, useState } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, Html } from '@react-three/drei';
import * as THREE from 'three';
import { MeshSurfaceSampler } from 'three/examples/jsm/math/MeshSurfaceSampler.js';
import { partNames, type Diagnosis, type MachineModel, type PartDef, type Recognition, type Shape } from '../twin/machineModels';

// DESIGN.md status colours.
const FAULT_COLOR = { warning: '#F59E0B', critical: '#EF4444' } as const;
const CONTEXT_COLOR = '#5A6270';
// Particles per square unit of surface; caps keep the total in the tens of thousands.
const DENSITY = 2600;
const MAX_PER_SHAPE = 9000;
const MIN_PER_SHAPE = 220;
const CAMERA_DIR = new THREE.Vector3(1, 0.7, 1.35).normalize();
const FOV = 40;

function shapeGeometry(sh: Shape): THREE.BufferGeometry {
  let g: THREE.BufferGeometry;
  if (sh.k === 'box') g = new THREE.BoxGeometry(sh.s[0], sh.s[1], sh.s[2]);
  // CylinderGeometry puts radiusTop at +y, which the rotations below carry to the +axis end.
  else if (sh.k === 'cyl') g = new THREE.CylinderGeometry(sh.s[1], sh.s[0], sh.s[2], 48);
  else if (sh.k === 'torus') g = new THREE.TorusGeometry(sh.s[0], sh.s[1], 16, 48);
  else g = new THREE.SphereGeometry(sh.s[0], 32, 16);
  const axis = sh.axis ?? 'y';
  if (sh.k === 'cyl') {
    if (axis === 'x') g.rotateZ(-Math.PI / 2);
    if (axis === 'z') g.rotateX(Math.PI / 2);
  } else if (sh.k === 'torus') {
    // Torus axis starts on z.
    if (axis === 'x') g.rotateY(Math.PI / 2);
    if (axis === 'y') g.rotateX(Math.PI / 2);
  }
  if (sh.p) g.translate(...sh.p);
  return g;
}

function shapeArea(sh: Shape): number {
  const [a, b, c] = sh.s;
  if (sh.k === 'box') return 2 * (a * b + b * c + a * c);
  if (sh.k === 'cyl') return Math.PI * (a + b) * c + Math.PI * (a * a + b * b);
  if (sh.k === 'torus') return 4 * Math.PI * Math.PI * a * b;
  return 4 * Math.PI * a * a;
}

interface Cloud {
  points: THREE.BufferGeometry;
  edges: THREE.BufferGeometry[];
  hits: THREE.BufferGeometry[];
  centroid: THREE.Vector3;
}

function buildCloud(shapes: Shape[]): Cloud {
  const positions: number[] = [];
  const edges: THREE.BufferGeometry[] = [];
  const hits: THREE.BufferGeometry[] = [];
  const v = new THREE.Vector3();
  for (const sh of shapes) {
    const g = shapeGeometry(sh);
    const sampler = new MeshSurfaceSampler(new THREE.Mesh(g)).build();
    const n = Math.min(MAX_PER_SHAPE, Math.max(MIN_PER_SHAPE, Math.round(shapeArea(sh) * DENSITY)));
    for (let i = 0; i < n; i++) {
      sampler.sample(v);
      positions.push(v.x, v.y, v.z);
    }
    edges.push(new THREE.EdgesGeometry(g, 30));
    hits.push(g);
  }
  const points = new THREE.BufferGeometry();
  points.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  points.computeBoundingBox();
  const centroid = points.boundingBox!.getCenter(new THREE.Vector3());
  return { points, edges, hits, centroid };
}

function disposeCloud(c: Cloud) {
  c.points.dispose();
  c.edges.forEach(g => g.dispose());
  c.hits.forEach(g => g.dispose());
}

let dotTexture: THREE.Texture | null = null;
function getDotTexture() {
  if (dotTexture) return dotTexture;
  const size = 64;
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = size;
  const ctx = canvas.getContext('2d')!;
  const grad = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  grad.addColorStop(0, 'rgba(255,255,255,1)');
  grad.addColorStop(0.35, 'rgba(255,255,255,0.55)');
  grad.addColorStop(1, 'rgba(255,255,255,0)');
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, size, size);
  dotTexture = new THREE.CanvasTexture(canvas);
  return dotTexture;
}

function TwinPart({ part, cloud, apart, faultColor, dimmed, selected, showLabel, reducedMotion, onSelect, onHover }: {
  part: PartDef;
  cloud: Cloud;
  apart: boolean;
  faultColor: string | null;
  dimmed: boolean;
  selected: boolean;
  showLabel: boolean;
  reducedMotion: boolean;
  onSelect: (id: string) => void;
  onHover: (id: string | null) => void;
}) {
  const groupRef = useRef<THREE.Group>(null);
  const pointsMat = useRef<THREE.PointsMaterial>(null);
  const color = faultColor ?? part.color;
  const baseOpacity = faultColor || selected ? 1 : dimmed ? 0.55 : 0.85;
  // Label sits outward from the part, along its separation direction where it has one.
  const labelOffset = useMemo(() => {
    const dir = new THREE.Vector3(...part.apart);
    if (dir.lengthSq() < 1e-6) dir.set(0, 1, 0);
    return cloud.centroid.clone().add(dir.normalize().multiplyScalar(0.35)).add(new THREE.Vector3(0, 0.12, 0));
  }, [part.apart, cloud.centroid]);
  const leader = useMemo(
    () => new THREE.BufferGeometry().setFromPoints([cloud.centroid, labelOffset]),
    [cloud.centroid, labelOffset],
  );
  useEffect(() => () => leader.dispose(), [leader]);

  useFrame((state, delta) => {
    const g = groupRef.current;
    if (!g) return;
    const target = new THREE.Vector3(...part.pos);
    if (apart) target.add(new THREE.Vector3(...part.apart));
    if (reducedMotion) g.position.copy(target);
    else g.position.lerp(target, 1 - Math.exp(-7 * delta));
    if (pointsMat.current) {
      const pulse = faultColor && !reducedMotion ? 0.25 * Math.sin(state.clock.elapsedTime * 3.2) : 0;
      pointsMat.current.opacity = Math.min(1, baseOpacity + pulse);
    }
  });

  return (
    <group ref={groupRef} position={part.pos}>
      <points geometry={cloud.points}>
        <pointsMaterial
          ref={pointsMat}
          color={color}
          size={faultColor || selected ? 0.03 : 0.022}
          map={getDotTexture()}
          transparent
          opacity={baseOpacity}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </points>
      {cloud.edges.map((e, i) => (
        <lineSegments key={i} geometry={e}>
          <lineBasicMaterial color={color} transparent opacity={selected ? 0.9 : dimmed ? 0.3 : 0.45} depthWrite={false} blending={THREE.AdditiveBlending} />
        </lineSegments>
      ))}
      {cloud.hits.map((h, i) => (
        <mesh
          key={i}
          geometry={h}
          onClick={(e) => { e.stopPropagation(); onSelect(part.id); }}
          onPointerOver={(e) => { e.stopPropagation(); onHover(part.id); }}
          onPointerOut={() => onHover(null)}
        >
          <meshBasicMaterial transparent opacity={0} depthWrite={false} />
        </mesh>
      ))}
      {showLabel && (
        <>
          <lineSegments geometry={leader}>
            <lineBasicMaterial color={color} transparent opacity={0.6} />
          </lineSegments>
          <Html position={labelOffset} zIndexRange={[20, 0]} style={{ pointerEvents: 'none' }}>
            <div style={{
              transform: 'translate(4px, -50%)', whiteSpace: 'nowrap', padding: '3px 7px',
              borderLeft: `2px solid ${color}`, background: 'rgba(8, 9, 11, 0.78)', fontFamily: 'var(--font-sans)',
            }}>
              <div style={{ fontSize: '11px', fontWeight: 700, color: faultColor ? color : '#E8EAED' }}>
                {faultColor ? `FAULT: ${part.name}` : part.name}
              </div>
              <div style={{ fontSize: '10px', color: '#9AA1AA' }}>{part.detail}</div>
            </div>
          </Html>
        </>
      )}
    </group>
  );
}

function ContextCloud({ cloud }: { cloud: Cloud }) {
  return (
    <points geometry={cloud.points}>
      <pointsMaterial color={CONTEXT_COLOR} size={0.018} map={getDotTexture()} transparent opacity={0.45} depthWrite={false} blending={THREE.AdditiveBlending} />
    </points>
  );
}

// Frames the whole model, including its separated layout, for any panel shape.
function FitCamera({ radius }: { radius: number }) {
  const camera = useThree(state => state.camera);
  const { width, height } = useThree(state => state.size);
  useEffect(() => {
    const aspect = width / Math.max(height, 1);
    const fit = (radius * 0.95) / Math.tan(THREE.MathUtils.degToRad(FOV / 2));
    camera.position.copy(CAMERA_DIR).multiplyScalar(fit / Math.min(1, aspect));
    camera.lookAt(0, 0, 0);
  }, [camera, width, height, radius]);
  return null;
}

interface MachineTwin3DProps {
  recognition: Recognition;
  diagnosis: Diagnosis;
}

function useReducedMotion() {
  const [reduced, setReduced] = useState(() => window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    const listener = (e: MediaQueryListEvent) => setReduced(e.matches);
    mq.addEventListener('change', listener);
    return () => mq.removeEventListener('change', listener);
  }, []);
  return reduced;
}

export interface TwinViewerProps {
  model: MachineModel;
  faultParts?: string[];
  faultColor?: string | null;
  apart: boolean;
  activeId?: string | null;
  height?: number;
  onSelect?: (id: string | null) => void;
}

/** The 3D particle view of one machine model, without the diagnosis panel. */
export function TwinViewer({ model, faultParts = [], faultColor = null, apart, activeId = null, height = 400, onSelect }: TwinViewerProps) {
  const [hovered, setHovered] = useState<string | null>(null);
  const reducedMotion = useReducedMotion();

  const clouds = useMemo(() => model.parts.map(p => buildCloud(p.shapes)), [model]);
  const context = useMemo(() => (model.context ? buildCloud(model.context) : null), [model]);
  useEffect(() => () => {
    clouds.forEach(disposeCloud);
    if (context) disposeCloud(context);
  }, [clouds, context]);

  // Centre the assembled model and size the camera from its extent plus the separation offsets.
  const { center, radius, fitRadius } = useMemo(() => {
    const assembled = new THREE.Box3();
    const separated = new THREE.Box3();
    model.parts.forEach((p, i) => {
      const b = clouds[i].points.boundingBox!.clone().translate(new THREE.Vector3(...p.pos));
      assembled.union(b);
      separated.union(b.clone().translate(new THREE.Vector3(...p.apart)));
    });
    if (context) assembled.union(context.points.boundingBox!);
    separated.union(assembled);
    const a = assembled.getBoundingSphere(new THREE.Sphere());
    const s = separated.getBoundingSphere(new THREE.Sphere());
    // Frame between the assembled and separated extents so both read well without re-zooming.
    return { center: a.center, radius: a.radius, fitRadius: (a.radius + s.radius) / 2 };
  }, [model, clouds, context]);

  return (
    <div style={{ position: 'relative', height: `${height}px`, background: '#08090B', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', overflow: 'hidden', cursor: hovered && onSelect ? 'pointer' : 'grab' }}>
      <Canvas camera={{ fov: FOV, near: 0.05, far: 100 }} dpr={[1, 2]} onPointerMissed={() => onSelect?.(null)}>
        <FitCamera radius={fitRadius} />
        <group position={center.clone().negate()}>
          {context && <ContextCloud cloud={context} />}
          {model.parts.map((part, i) => (
            <TwinPart
              key={part.id}
              part={part}
              cloud={clouds[i]}
              apart={apart}
              faultColor={faultParts.includes(part.id) ? faultColor : null}
              dimmed={faultParts.length > 0 && !faultParts.includes(part.id)}
              selected={part.id === activeId || part.id === hovered}
              showLabel={apart || part.id === faultParts[0]}
              reducedMotion={reducedMotion}
              onSelect={id => onSelect?.(id)}
              onHover={setHovered}
            />
          ))}
        </group>
        <gridHelper args={[radius * 5, 30, '#1B1F24', '#121518']} position={[0, -radius * 0.8, 0]} />
        <OrbitControls enablePan={false} minDistance={radius * 0.8} maxDistance={fitRadius * 8} />
      </Canvas>
      <div style={{ position: 'absolute', left: 10, top: 8, fontSize: '11px', fontFamily: 'var(--font-mono)', color: '#9AA1AA', pointerEvents: 'none' }}>
        {model.label.toUpperCase()}{hovered ? ` / ${model.parts.find(p => p.id === hovered)?.name}` : ''}
      </div>
    </div>
  );
}

export default function MachineTwin3D({ recognition, diagnosis }: MachineTwin3DProps) {
  const { model, reason } = recognition;
  const [apart, setApart] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);

  const faultParts = diagnosis.parts;
  const faultColor = diagnosis.severity === 'normal' ? null : FAULT_COLOR[diagnosis.severity];
  const activeId = selected ?? faultParts[0] ?? null;
  const active = model.parts.find(p => p.id === activeId) ?? null;
  const activeIsFaulty = activeId !== null && faultParts.includes(activeId);
  const statusVar = diagnosis.severity === 'critical' ? 'var(--status-critical)' : diagnosis.severity === 'warning' ? 'var(--status-warning)' : 'var(--status-normal)';

  const label = { fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontWeight: 700, letterSpacing: '0.06em' } as const;
  const button = {
    padding: '6px 10px', fontSize: '11px', fontFamily: 'var(--font-mono)', background: 'var(--bg-secondary)',
    border: '1px solid var(--border-color)', color: 'var(--text-bright)', borderRadius: 'var(--radius-xs)', cursor: 'pointer',
  } as const;

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '16px' }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <TwinViewer model={model} faultParts={faultParts} faultColor={faultColor} apart={apart} activeId={activeId} onSelect={setSelected} />
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
            Drag to turn. Scroll to zoom. Click a part to inspect it.
          </span>
          <button type="button" style={button} onClick={() => setApart(a => !a)} aria-pressed={apart}>
            {apart ? 'Put parts back' : 'Separate parts'}
          </button>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
          <span style={label}>MODEL</span>{' '}
          <span style={{ color: 'var(--text-secondary)' }}>{model.label}. {reason}.</span>
        </div>

        <div>
          <div style={label}>WHERE IS THE PROBLEM</div>
          <div style={{ fontSize: '15px', color: diagnosis.severity === 'normal' ? 'var(--status-normal)' : 'var(--text-bright)', fontWeight: 700, marginTop: '4px' }}>
            {diagnosis.severity === 'normal'
              ? diagnosis.title
              : faultParts.length > 0
                ? <>{partNames(model, faultParts)} <span style={{ fontWeight: 500, color: statusVar }}>({diagnosis.title})</span></>
                : diagnosis.title}
          </div>
          {diagnosis.evidence.length > 0 && (
            <ul style={{ margin: '6px 0 0', paddingLeft: '16px', fontSize: '12px', color: 'var(--text-secondary)' }}>
              {diagnosis.evidence.map(e => <li key={e}>{e}</li>)}
            </ul>
          )}
          {diagnosis.note && <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '6px' }}>{diagnosis.note}</div>}
        </div>

        {(diagnosis.action || diagnosis.steps) && (
          <div>
            <div style={label}>HOW TO FIX IT</div>
            {diagnosis.action && <div style={{ fontSize: '13px', color: 'var(--text-bright)', fontWeight: 600, marginTop: '4px' }}>{diagnosis.action}</div>}
            {diagnosis.steps && (
              <ol style={{ margin: '6px 0 0', paddingLeft: '18px', fontSize: '12px', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '3px' }}>
                {diagnosis.steps.map(step => <li key={step}>{step}</li>)}
              </ol>
            )}
          </div>
        )}

        {active && (
          <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '10px' }}>
            <div style={label}>SELECTED PART</div>
            <div style={{ fontSize: '13px', color: 'var(--text-bright)', fontWeight: 600, marginTop: '4px' }}>{active.name}</div>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>{active.detail}</div>
            <div style={{ fontSize: '12px', marginTop: '4px', fontWeight: 600, color: activeIsFaulty ? statusVar : 'var(--status-normal)' }}>
              {activeIsFaulty ? 'This part is where the fault is.' : 'No fault reported on this part.'}
            </div>
          </div>
        )}

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }} role="group" aria-label="Machine parts">
          {model.parts.map(part => {
            const isFaulty = faultParts.includes(part.id);
            return (
              <button
                key={part.id}
                type="button"
                onClick={() => setSelected(part.id)}
                aria-pressed={part.id === activeId}
                style={{
                  ...button,
                  padding: '4px 8px',
                  fontSize: '10px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  borderColor: part.id === activeId ? 'var(--accent-cyan)' : isFaulty ? statusVar : 'var(--border-color)',
                  color: isFaulty ? statusVar : 'var(--text-secondary)',
                  fontWeight: isFaulty ? 700 : 500,
                }}
              >
                <span aria-hidden="true" style={{ width: 8, height: 8, background: isFaulty && faultColor ? faultColor : part.color }} />
                {part.name}{isFaulty ? ' (fault)' : ''}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
