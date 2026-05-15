// src/components/3d/SceneManager.tsx
import * as THREE from 'three';
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { PropsWithChildren } from 'react';
import ParticleSystem from './ParticleSystem';

// We'll create a wrapper that sets up the scene with default camera, lights, etc.
const SceneManager = ({ children }: PropsWithChildren<{ children: React.ReactNode }>) => {
  return (
    <Canvas
      // Configure the canvas
      camera={{ position: [0, 5, 10], fov: 60 }}
      // Enable shadows
      shadowMap
      // Adjust the rendering performance
      gl={{ antialias: true, preserveDrawingBuffer: true }}
    >
      {/* Lights */}
      <ambientLight intensity={0.5} />
      <directionalLight position={[10, 20, 10]} intensity={1} castShadow>
        {/* Configure shadow map for the directional light */}
        <directionalLight.shadow
          mapSize={new THREE.Vector2(2048, 2048)}
        />
      </directionalLight>

      {/* Particle System */}
      <ParticleSystem count={8000} size={0.15} color={0x00ffff} opacity={0.6} rotationSpeed={[0, 0.05, 0]} />

      {/* Controls - for development, we can enable OrbitControls */}
      <OrbitControls enablePan={false} enableZoom={true} enableRotate={true} />

      {/* The children (our 3D components) */}
      {children}
    </Canvas>
  );
};

export default SceneManager;