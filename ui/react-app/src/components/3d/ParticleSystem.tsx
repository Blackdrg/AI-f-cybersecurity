// src/components/3d/ParticleSystem.tsx
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { useRef, useMemo } from 'react';

interface ParticleSystemProps {
  count?: number;
  size?: number;
  color?: number;
  opacity?: number;
  rotationSpeed?: [number, number, number];
}

const defaultProps = {
  count: 5000,
  size: 0.1,
  color: 0xffffff,
  opacity: 0.5,
  rotationSpeed: [0, 0.1, 0] as [number, number, number], // [x, y, z] rotation speed per second
};

const ParticleSystem = ({
  count = defaultProps.count,
  size = defaultProps.size,
  color = defaultProps.color,
  opacity = defaultProps.opacity,
  rotationSpeed = defaultProps.rotationSpeed,
}: ParticleSystemProps) => {
  const pointsRef = useRef<THREE.Points>(null);
  
  // Generate particle positions once
  // Generate particle positions once
  const positions = useMemo(() => {
    const pos = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      // Distribute points in a sphere
      const phi = Math.acos(2 * Math.random() - 1);
      const theta = 2 * Math.PI * Math.random();
      const radius = 10 + Math.random() * 5; // Slightly varied radius
      pos[i * 3] = radius * Math.sin(phi) * Math.cos(theta);
      pos[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
      pos[i * 3 + 2] = radius * Math.cos(phi);
    }
    return pos;
  }, [count]);
  
  // Animation: slow rotation and twinkling
  useFrame((state, delta) => {
    if (!pointsRef.current) return;
    
    // Rotate the particle system
    pointsRef.current.rotation.x += rotationSpeed[0] * delta;
    pointsRef.current.rotation.y += rotationSpeed[1] * delta;
    pointsRef.current.rotation.z += rotationSpeed[2] * delta;
    
    // Twinkling effect: animate size and opacity
    const time = state.clock.getElapsedTime();
    const material = pointsRef.current.material as THREE.PointsMaterial;
    material.size = size * (1 + Math.sin(time * 2) * 0.5);
    material.opacity = opacity * (0.5 + Math.sin(time * 1.7) * 0.5);
  });

  return (
    <points
      ref={pointsRef}
    >
      <bufferGeometry>
        <bufferAttribute
          attach="position"
          count={count}
          itemSize={3}
          array={positions}
        />
      </bufferGeometry>
      <pointsMaterial
        color={color}
        size={size}
        transparent
        opacity={opacity}
        // Add some blending for glow effect
        blending={THREE.AdditiveBlending}
        depthWrite={false}
      />
    </points>
  );
};

export default ParticleSystem;

