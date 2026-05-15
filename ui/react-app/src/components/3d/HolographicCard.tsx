// src/components/3d/HolographicCard.tsx
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { useRef } from 'react';

// Interface for the holographic card props
interface HolographicCardProps {
  position?: [number, number, number];
  rotation?: [number, number, number];
  scale?: [number, number, number];
  color?: string;
  intensity?: number;
  width?: number;
  height?: number;
  depth?: number;
  content?: React.ReactNode; // For future use with CSS2DRenderer or similar
  onClick?: () => void;
}

// Default props
const defaultProps = {
  position: [0, 0, 0] as [number, number, number],
  rotation: [0, 0, 0] as [number, number, number],
  scale: [1, 1, 1] as [number, number, number],
  color: '#00bcd4', // electric blue
  intensity: 2,
  width: 2,
  height: 1,
  depth: 0.1,
};

const HolographicCard = ({
  position = defaultProps.position,
  rotation = defaultProps.rotation,
  scale = defaultProps.scale,
  color = defaultProps.color,
  intensity = defaultProps.intensity,
  width = defaultProps.width,
  height = defaultProps.height,
  depth = defaultProps.depth,
  onClick,
}: HolographicCardProps) => {
  const meshRef = useRef<THREE.Mesh>(null);
  
  // Animation: slow floating and pulsing
  useFrame((state, delta) => {
    if (!meshRef.current) return;
    
    // Gentle floating motion
    meshRef.current.position.y = position[1] + Math.sin(state.clock.getElapsedTime() * 0.5) * 0.1;
    
    // Pulsing glow effect (we'll modify material emissive intensity)
    const pulse = Math.sin(state.clock.getElapsedTime() * 2) * 0.5 + 0.5; // 0 to 1
    if (meshRef.current.material) {
      // Assuming we have an emissive property
      (meshRef.current.material as THREE.MeshStandardMaterial).emissiveIntensity = intensity * 0.5 + pulse * intensity * 0.5;
    }
  });

  return (
    <mesh
      ref={meshRef}
      position={position}
      rotation={rotation}
      scale={scale}
      onClick={onClick}
      cursor="pointer"
    >
      {/* Card base - using a thin box */}
      <boxGeometry args={[width, height, depth]} />
      {/* Material with glow effect */}
      <meshStandardMaterial
        color={color}
        emissive={color}
        emissiveIntensity={intensity * 0.5}
        transparent
        opacity={0.8}
        // Add some roughness for glass-like appearance
        roughness={0.2}
        metalness={0.8}
      />
      {/* Add a subtle outer glow using a slightly larger mesh with additive blending */}
      <mesh>
        <boxGeometry args={[width * 1.05, height * 1.05, depth * 1.05]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={intensity * 0.3}
          transparent
          opacity={0.3}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </mesh>
    </mesh>
  );
};

export default HolographicCard;