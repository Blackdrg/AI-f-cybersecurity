// src/components/3d/BiometricScanner.tsx
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { useRef } from 'react';

interface BiometricScannerProps {
  position?: [number, number, number];
  rotation?: [number, number, number];
  scale?: [number, number, number];
  color?: string;
  scanSpeed?: number;
  width?: number;
  height?: number;
  depth?: number;
}

const defaultProps = {
  position: [0, 0, 0] as [number, number, number],
  rotation: [0, 0, 0] as [number, number, number],
  scale: [1, 1, 1] as [number, number, number],
  color: '#00ff00', // emerald for success/scan
  scanSpeed: 2, // units per second
  width: 1,
  height: 0.1,
  depth: 0.5,
};

const BiometricScanner = ({
  position = defaultProps.position,
  rotation = defaultProps.rotation,
  scale = defaultProps.scale,
  color = defaultProps.color,
  scanSpeed = defaultProps.scanSpeed,
  width = defaultProps.width,
  height = defaultProps.height,
  depth = defaultProps.depth,
}: BiometricScannerProps) => {
  const baseRef = useRef<THREE.Mesh>(null);
  const scanLineRef = useRef<THREE.Mesh>(null);

  // Animation: move the scan line from bottom to top and reset
  useFrame((state, delta) => {
    if (!scanLineRef.current) return;
    
    // We'll animate the y position of the scan line within the scanner's height
    const elapsedTime = state.clock.getElapsedTime() * scanSpeed; // Time in seconds multiplied by speed
    const normalizedTime = (elapsedTime % (height * 2)) / (height * 2); // 0 to 1, then reset
    let scanY = -height/2 + normalizedTime * height; // From -height/2 to +height/2
    
    // If we are in the return journey (from top to bottom), we can make it invisible or faster return
    // For simplicity, we'll just reset when it hits the top and make it jump back (or we can do a smooth return)
    // Let's do a sawtooth: go from bottom to top, then instantly reset to bottom.
    if (normalizedTime > 0.5) {
      // In the second half, we can make the scan line invisible or just reset immediately
      // For now, we'll reset to bottom when it reaches the top (at normalizedTime=0.5) but we are using modulo so it's continuous.
      // Actually, we want: from 0 to 0.5: bottom to top, then 0.5 to 1: top to bottom (or invisible)
      // Let's change: we'll make the scan line only visible in the first half of the cycle.
      if (normalizedTime > 0.5) {
        scanLineRef.current.visible = false;
      } else {
        scanLineRef.current.visible = true;
        scanY = -height/2 + normalizedTime * 2 * height; // Adjust for first half only: 0 to 0.5 -> 0 to height
      }
    } else {
      scanLineRef.current.visible = true;
      scanY = -height/2 + normalizedTime * 2 * height;
    }
    
    // Update the scan line position
    scanLineRef.current.position.setY(scanY);
  });

  return (
    <group position={position} rotation={rotation} scale={scale}>
      {/* Scanner base - a flat box */}
      <mesh ref={baseRef}>
        <boxGeometry args={[width, height, depth]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={0.5}
          transparent
          opacity={0.3}
          roughness={0.2}
          metalness={0.8}
        />
      </mesh>
      
      {/* Scan line - a thin rectangle that moves */}
      <mesh ref={scanLineRef}>
        {/* The scan line is a thin box on the surface of the scanner */}
        <boxGeometry args={[width * 0.9, height * 0.02, depth * 0.9]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={2}
          transparent
          opacity={0.8}
          blending={THREE.AdditiveBlending}
        />
      </mesh>
    </group>
  );
};

export default BiometricScanner;