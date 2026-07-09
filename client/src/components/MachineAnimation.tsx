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
      <meshStandardMaterial color="#3b82f6" emissive="#3b82f6" emissiveIntensity={2} />
    </Sphere>
  );
};

const MachineParts = ({ prefersReducedMotion }: { prefersReducedMotion: boolean }) => {
  const groupRef = useRef<THREE.Group>(null);
  const motorRef = useRef<THREE.Mesh>(null);
  const gearRef = useRef<THREE.Mesh>(null);
  const sensorRef = useRef<THREE.Mesh>(null);

  // Animation values
  const [assembled, setAssembled] = useState(prefersReducedMotion);

  useFrame((state) => {
    if (prefersReducedMotion) return; // static if reduced motion

    const t = state.clock.elapsedTime;

    // Assembly phase
    if (t < 3) {
      // Ease in assembly
      const progress = Math.min(t / 2, 1); // 0 to 1 over 2 seconds
      const ease = 1 - Math.pow(1 - progress, 3); // cubic ease out

      if (motorRef.current) motorRef.current.position.y = (1 - ease) * 5 + 0.5;
      if (gearRef.current) gearRef.current.position.x = (1 - ease) * -5 + 1.2;
      if (sensorRef.current) sensorRef.current.position.z = (1 - ease) * 5;
    } else {
      if (!assembled) setAssembled(true);
      
      // Breathing phase (idling after assembly)
      if (groupRef.current) {
        groupRef.current.position.y = Math.sin(t * 1.5) * 0.05;
        // Subtle gear rotation representing a live machine
        if (gearRef.current) {
          gearRef.current.rotation.x = Math.PI / 2;
          gearRef.current.rotation.z = t * 0.5;
        }
      }
    }
  });

  return (
    <group ref={groupRef}>
      {/* Base Chassis */}
      <Box args={[2.5, 0.4, 1.5]} position={[0, -0.4, 0]}>
        <meshStandardMaterial color="#334155" metalness={0.7} roughness={0.3} />
      </Box>

      {/* Motor Housing */}
      <Cylinder ref={motorRef} args={[0.5, 0.5, 1.8, 32]} position={[0, 0.5, 0]} rotation={[0, 0, Math.PI / 2]}>
        <meshStandardMaterial color="#94a3b8" metalness={0.8} roughness={0.4} />
      </Cylinder>

      {/* Gear / Rotor */}
      <Torus ref={gearRef} args={[0.3, 0.1, 16, 32]} position={[1.2, 0.5, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <meshStandardMaterial color="#cbd5e1" metalness={1} roughness={0.2} />
      </Torus>

      {/* Sensor Node */}
      <Box ref={sensorRef} args={[0.25, 0.25, 0.25]} position={[-0.8, 0.8, 0]}>
        <meshStandardMaterial color="#10b981" emissive="#059669" emissiveIntensity={0.8} />
      </Box>

      {/* Connectivity Lines / PCB board representation */}
      <Box args={[1.5, 0.05, 0.4]} position={[-0.2, 0, 0.4]}>
         <meshStandardMaterial color="#0f172a" />
      </Box>

      {/* Data streams (only visible when assembled or reduced motion is on) */}
      {(assembled || prefersReducedMotion) && (
        <>
          <DataPoint start={[-0.8, 0.8, 0]} end={[-0.2, 0, 0.4]} speed={1} delay={0} />
          <DataPoint start={[1.2, 0.5, 0]} end={[-0.2, 0, 0.4]} speed={1} delay={0.3} />
          <DataPoint start={[0, 0.5, 0]} end={[-0.2, 0, 0.4]} speed={1} delay={0.6} />
        </>
      )}
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
