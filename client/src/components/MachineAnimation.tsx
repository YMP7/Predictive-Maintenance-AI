import { useRef, useState, useEffect } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Environment, Float, Sphere, Cylinder, Box, Torus } from '@react-three/drei';
import * as THREE from 'three';

// A single floating data point representing telemetry streaming
const DataPoint = ({ start, end, speed = 1, delay = 0 }: { start: [number, number, number], end: [number, number, number], speed?: number, delay?: number }) => {
  const meshRef = useRef<THREE.Mesh>(null);
  
  useFrame((state) => {
    if (!meshRef.current) return;
    const t = (state.clock.elapsedTime * speed + delay) % 1;
    meshRef.current.position.set(
      start[0] + (end[0] - start[0]) * t,
      start[1] + (end[1] - start[1]) * t,
      start[2] + (end[2] - start[2]) * t
    );
  });

  return (
    <Sphere ref={meshRef} args={[0.08, 16, 16]}>
      <meshStandardMaterial color="#787774" emissive="#787774" emissiveIntensity={0.5} />
    </Sphere>
  );
};

// 1. Lathe Machine M001
const LatheMachine = ({ prefersReducedMotion }: { prefersReducedMotion: boolean }) => {
  const chuckRef = useRef<THREE.Mesh>(null);
  
  useFrame((state) => {
    if (!prefersReducedMotion && chuckRef.current) {
      // Chuck and workpiece rotate
      chuckRef.current.rotation.x = state.clock.elapsedTime * 4;
    }
  });

  return (
    <group position={[-1.2, -0.2, 0]} rotation={[0, Math.PI / 4, 0]}>
      {/* Lathe Bed */}
      <Box args={[1.4, 0.25, 0.4]}>
        <meshStandardMaterial color="#334155" metalness={0.7} roughness={0.3} />
      </Box>
      {/* Headstock */}
      <Box args={[0.35, 0.6, 0.4]} position={[-0.525, 0.175, 0]}>
        <meshStandardMaterial color="#1e293b" metalness={0.8} roughness={0.4} />
      </Box>
      {/* Rotating Chuck */}
      <Cylinder ref={chuckRef} args={[0.16, 0.16, 0.15, 16]} position={[-0.2, 0.25, 0]} rotation={[0, 0, Math.PI / 2]}>
        <meshStandardMaterial color="#94a3b8" metalness={0.9} roughness={0.1} />
      </Cylinder>
      {/* Spindle Workpiece */}
      <Cylinder args={[0.06, 0.06, 0.6, 16]} position={[0.1, 0.25, 0]} rotation={[0, 0, Math.PI / 2]}>
        <meshStandardMaterial color="#cbd5e1" metalness={0.9} roughness={0.2} />
      </Cylinder>
      {/* Tailstock */}
      <Box args={[0.25, 0.4, 0.3]} position={[0.45, 0.125, 0]}>
        <meshStandardMaterial color="#475569" metalness={0.8} roughness={0.3} />
      </Box>
      {/* Tool Post */}
      <Box args={[0.15, 0.25, 0.15]} position={[0.05, 0.2, 0.12]}>
        <meshStandardMaterial color="#0f172a" metalness={0.8} roughness={0.3} />
      </Box>
      {/* Sensor Node */}
      <Box args={[0.15, 0.15, 0.15]} position={[-0.525, 0.525, 0]}>
        <meshStandardMaterial color="#10b981" emissive="#059669" emissiveIntensity={1} />
      </Box>
    </group>
  );
};

// 2. Pump Motor M002
const PumpMotor = ({ prefersReducedMotion }: { prefersReducedMotion: boolean }) => {
  const shaftRef = useRef<THREE.Mesh>(null);
  
  useFrame((state) => {
    if (!prefersReducedMotion && shaftRef.current) {
      shaftRef.current.rotation.x = state.clock.elapsedTime * 6;
    }
  });

  return (
    <group position={[1.2, -0.1, 0]} rotation={[0, -Math.PI / 4, 0]}>
      {/* Motor Base Mount */}
      <Box args={[0.8, 0.15, 0.6]} position={[0, -0.1, 0]}>
        <meshStandardMaterial color="#475569" metalness={0.6} roughness={0.4} />
      </Box>
      {/* Main Stator Cylinder */}
      <Cylinder args={[0.3, 0.3, 0.7, 16]} position={[0, 0.2, 0]} rotation={[0, 0, Math.PI / 2]}>
        <meshStandardMaterial color="#1e3a8a" metalness={0.7} roughness={0.4} />
      </Cylinder>
      {/* Cooling Fins (Procedural Rings) */}
      <Torus args={[0.31, 0.02, 8, 24]} position={[-0.2, 0.2, 0]} rotation={[0, Math.PI / 2, 0]}>
        <meshStandardMaterial color="#172554" metalness={0.7} />
      </Torus>
      <Torus args={[0.31, 0.02, 8, 24]} position={[0, 0.2, 0]} rotation={[0, Math.PI / 2, 0]}>
        <meshStandardMaterial color="#172554" metalness={0.7} />
      </Torus>
      <Torus args={[0.31, 0.02, 8, 24]} position={[0.2, 0.2, 0]} rotation={[0, Math.PI / 2, 0]}>
        <meshStandardMaterial color="#172554" metalness={0.7} />
      </Torus>
      {/* Rotating Shaft */}
      <Cylinder ref={shaftRef} args={[0.05, 0.05, 1.1, 12]} position={[0.1, 0.2, 0]} rotation={[0, 0, Math.PI / 2]}>
        <meshStandardMaterial color="#94a3b8" metalness={0.9} roughness={0.2} />
      </Cylinder>
      {/* Impeller / Fan Housing */}
      <Cylinder args={[0.35, 0.35, 0.25, 16]} position={[-0.4, 0.2, 0]} rotation={[0, 0, Math.PI / 2]}>
        <meshStandardMaterial color="#0f172a" metalness={0.8} roughness={0.3} />
      </Cylinder>
      {/* Sensor Node */}
      <Box args={[0.15, 0.15, 0.15]} position={[0, 0.525, 0]}>
        <meshStandardMaterial color="#10b981" emissive="#059669" emissiveIntensity={1} />
      </Box>
    </group>
  );
};

// 3. Drill Press M003
const DrillPress = ({ prefersReducedMotion }: { prefersReducedMotion: boolean }) => {
  const spindleRef = useRef<THREE.Mesh>(null);
  
  useFrame((state) => {
    if (!prefersReducedMotion && spindleRef.current) {
      spindleRef.current.rotation.y = state.clock.elapsedTime * 8;
    }
  });

  return (
    <group position={[0, 0.1, -1.2]}>
      {/* Heavy Base */}
      <Box args={[0.6, 0.1, 0.6]} position={[0, -0.4, 0]}>
        <meshStandardMaterial color="#334155" metalness={0.7} roughness={0.4} />
      </Box>
      {/* Vertical Column */}
      <Cylinder args={[0.07, 0.07, 1.2, 16]} position={[0, 0.25, -0.15]}>
        <meshStandardMaterial color="#cbd5e1" metalness={0.9} roughness={0.2} />
      </Cylinder>
      {/* Working Table */}
      <Box args={[0.45, 0.05, 0.45]} position={[0, 0.1, 0.05]}>
        <meshStandardMaterial color="#475569" metalness={0.6} roughness={0.4} />
      </Box>
      {/* Drill Head Housing */}
      <Box args={[0.3, 0.3, 0.6]} position={[0, 0.75, 0.05]}>
        <meshStandardMaterial color="#1e293b" metalness={0.8} roughness={0.3} />
      </Box>
      {/* Rotating Spindle & Drill Bit */}
      <Cylinder ref={spindleRef} args={[0.03, 0.01, 0.25, 12]} position={[0, 0.5, 0.2]}>
        <meshStandardMaterial color="#94a3b8" metalness={1} roughness={0.1} />
      </Cylinder>
      {/* Sensor Node */}
      <Box args={[0.15, 0.15, 0.15]} position={[0, 0.925, 0.05]}>
        <meshStandardMaterial color="#10b981" emissive="#059669" emissiveIntensity={1} />
      </Box>
    </group>
  );
};

// 4. Industrial Furnace M004
const IndustrialFurnace = () => {
  return (
    <group position={[0, 0.1, 1.2]}>
      {/* Main Kiln Body */}
      <Box args={[0.8, 0.8, 0.8]}>
        <meshStandardMaterial color="#475569" metalness={0.5} roughness={0.5} />
      </Box>
      {/* Glowing Chamber Interior View (Front Cavity) */}
      <Box args={[0.6, 0.5, 0.02]} position={[0, 0, 0.401]}>
        <meshBasicMaterial color="#ea580c" toneMapped={false} />
      </Box>
      {/* Exhaust Chimney Stack */}
      <Cylinder args={[0.1, 0.1, 0.4, 16]} position={[0, 0.6, 0]}>
        <meshStandardMaterial color="#1e293b" metalness={0.6} roughness={0.4} />
      </Cylinder>
      {/* Control Module */}
      <Box args={[0.2, 0.4, 0.2]} position={[-0.51, -0.1, 0.1]}>
        <meshStandardMaterial color="#0f172a" />
      </Box>
      {/* Sensor Node */}
      <Box args={[0.15, 0.15, 0.15]} position={[0.3, 0.425, 0]}>
        <meshStandardMaterial color="#10b981" emissive="#059669" emissiveIntensity={1} />
      </Box>
    </group>
  );
};

const MachineParts = ({ prefersReducedMotion }: { prefersReducedMotion: boolean }) => {
  const stageRef = useRef<THREE.Group>(null);
  const mountTime = useRef<number | null>(null);
  const hubRef = useRef<THREE.Mesh>(null);
  const torusRef = useRef<THREE.Mesh>(null);

  // Turntable and Assembly/Breathing Animations
  useFrame((state) => {
    const elapsed = state.clock.getElapsedTime();

    // 1. Turntable rotation
    if (!prefersReducedMotion && stageRef.current) {
      stageRef.current.rotation.y = elapsed * 0.15;
    }

    // 2. Initial mount assembly scaling using ease-out-quart curve (Emil-Design-Eng)
    if (stageRef.current) {
      if (prefersReducedMotion) {
        stageRef.current.scale.set(1, 1, 1);
        stageRef.current.position.y = 0;
      } else {
        if (mountTime.current === null) mountTime.current = elapsed;
        const progress = Math.min(1, (elapsed - mountTime.current) / 1.2);
        const easeOutQuart = 1 - Math.pow(1 - progress, 4);
        
        const currentScale = 0.15 + 0.85 * easeOutQuart; // Starts at 0.15 to avoid scale(0)
        stageRef.current.scale.set(currentScale, currentScale, currentScale);
        stageRef.current.position.y = -0.3 * (1 - easeOutQuart);
      }
    }

    // 3. Central Hub Breathing & Torus Rotation pulse
    if (!prefersReducedMotion) {
      const pulse = Math.sin(elapsed * 1.5) * 0.5 + 0.5; // Slow breathing wave (15 breaths/min)
      
      if (hubRef.current) {
        const scaleVal = 0.97 + pulse * 0.06;
        hubRef.current.scale.set(scaleVal, scaleVal, scaleVal);
        if (hubRef.current.material) {
          (hubRef.current.material as THREE.MeshStandardMaterial).emissiveIntensity = 0.2 + pulse * 0.45;
        }
      }

      if (torusRef.current) {
        torusRef.current.rotation.z = -elapsed * 0.2;
        if (torusRef.current.material) {
          (torusRef.current.material as THREE.MeshStandardMaterial).emissiveIntensity = 0.08 + pulse * 0.22;
        }
      }
    }
  });

  return (
    <group ref={stageRef}>
      {/* Turntable Base Stage */}
      <Cylinder args={[2.2, 2.2, 0.15, 64]} position={[0, -0.4, 0]}>
        <meshStandardMaterial color="#1e293b" metalness={0.8} roughness={0.3} />
      </Cylinder>

      {/* Holographic Digital Twin Hub at the center */}
      <group position={[0, 0.3, 0]}>
        <Sphere ref={hubRef} args={[0.25, 32, 32]}>
          <meshStandardMaterial color="#ffffff" emissive="#eaeaea" emissiveIntensity={0.5} transparent opacity={0.9} />
        </Sphere>
        <Torus ref={torusRef} args={[0.4, 0.02, 8, 32]} rotation={[Math.PI / 2, 0, 0]}>
          <meshStandardMaterial color="#787774" emissive="#787774" emissiveIntensity={0.2} />
        </Torus>
      </group>

      {/* The Four Project Assets */}
      <LatheMachine prefersReducedMotion={prefersReducedMotion} />
      <PumpMotor prefersReducedMotion={prefersReducedMotion} />
      <DrillPress prefersReducedMotion={prefersReducedMotion} />
      <IndustrialFurnace />

      {/* Data Ingestion telemetry streams connecting sensors to center hub */}
      <DataPoint start={[-1.2, 0.325, 0]} end={[0, 0.3, 0]} speed={0.8} delay={0} />
      <DataPoint start={[1.2, 0.425, 0]} end={[0, 0.3, 0]} speed={0.8} delay={0.25} />
      <DataPoint start={[0, 1.025, -1.15]} end={[0, 0.3, 0]} speed={0.8} delay={0.5} />
      <DataPoint start={[0.3, 0.525, 1.2]} end={[0, 0.3, 0]} speed={0.8} delay={0.75} />
    </group>
  );
};

export default function MachineAnimation() {
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    setPrefersReducedMotion(mediaQuery.matches);
    const listener = (e: MediaQueryListEvent) => setPrefersReducedMotion(e.matches);
    mediaQuery.addEventListener('change', listener);
    return () => mediaQuery.removeEventListener('change', listener);
  }, []);

  return (
    <div style={{ width: '100%', height: '100%', minHeight: '400px' }}>
      <Canvas camera={{ position: [3, 3, 4], fov: 45 }}>
        <ambientLight intensity={0.6} />
        <directionalLight position={[10, 10, 5]} intensity={1.5} />
        <directionalLight position={[-10, -10, -5]} intensity={0.5} />
        <Environment preset="city" />
        
        {prefersReducedMotion ? (
           <MachineParts prefersReducedMotion={true} />
        ) : (
          <Float speed={2} rotationIntensity={0.1} floatIntensity={0.2}>
            <MachineParts prefersReducedMotion={false} />
          </Float>
        )}
        <OrbitControls enableZoom={false} enablePan={false} autoRotate={!prefersReducedMotion} autoRotateSpeed={0.8} />
      </Canvas>
    </div>
  );
}
