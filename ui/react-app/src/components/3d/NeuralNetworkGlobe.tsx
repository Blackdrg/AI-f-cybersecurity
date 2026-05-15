// src/components/3d/NeuralNetworkGlobe.tsx
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { useMemo, useRef } from 'react';

interface NeuralNetworkGlobeProps {
  position?: [number, number, number];
  rotation?: [number, number, number];
  scale?: [number, number, number];
  radius?: number;
  details?: number; // Number of nodes
  connectionDistance?: number; // Max distance for connections
  nodeColor?: string;
  connectionColor?: string;
  rotationSpeed?: [number, number, number];
}

const defaultProps = {
  position: [0, 0, 0] as [number, number, number],
  rotation: [0, 0, 0] as [number, number, number],
  scale: [1, 1, 1] as [number, number, number],
  radius: 3,
  details: 200,
  connectionDistance: 1.5,
  nodeColor: '#00ffff',
  connectionColor: '#00ffff80', // with transparency
  rotationSpeed: [0, 0.2, 0] as [number, number, number], // [x, y, z] in radians per second
};

const NeuralNetworkGlobe = ({
  position = defaultProps.position,
  rotation = defaultProps.rotation,
  scale = defaultProps.scale,
  radius = defaultProps.radius,
  details = defaultProps.details,
  connectionDistance = defaultProps.connectionDistance,
  nodeColor = defaultProps.nodeColor,
  connectionColor = defaultProps.connectionColor,
  rotationSpeed = defaultProps.rotationSpeed,
}: NeuralNetworkGlobeProps) => {
  const globeRef = useRef<THREE.Group>(null);

  // Precompute node positions and connection positions
  const { nodes, connections } = useMemo(() => {
    // Generate nodes (points) on the sphere surface
    const nodes = new Float32Array(details * 3);
    for (let i = 0; i < details; i++) {
      // Spherical coordinates
      const phi = Math.acos(2 * Math.random() - 1);
      const theta = 2 * Math.PI * Math.random();
      nodes[i * 3] = radius * Math.sin(phi) * Math.cos(theta);
      nodes[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
      nodes[i * 3 + 2] = radius * Math.cos(phi);
    }

    // Generate connections: for each node, connect to nearby nodes
    const connectionsIndices: number[] = [];
    for (let i = 0; i < details; i++) {
      for (let j = i + 1; j < details; j++) {
        const dx = nodes[i * 3] - nodes[j * 3];
        const dy = nodes[i * 3 + 1] - nodes[j * 3 + 1];
        const dz = nodes[i * 3 + 2] - nodes[j * 3 + 2];
        const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);
        if (dist < connectionDistance) {
          connectionsIndices.push(i, j);
        }
      }
    }

    // Convert connections indices to position attributes for lines
    const connections = new Float32Array(connectionsIndices.length * 3);
    for (let k = 0; k < connectionsIndices.length; k += 2) {
      const i = connectionsIndices[k];
      const j = connectionsIndices[k + 1];
      // Position of node i
      connections[k * 3] = nodes[i * 3];
      connections[k * 3 + 1] = nodes[i * 3 + 1];
      connections[k * 3 + 2] = nodes[i * 3 + 2];
      // Position of node j
      connections[(k + 1) * 3] = nodes[j * 3];
      connections[(k + 1) * 3 + 1] = nodes[j * 3 + 1];
      connections[(k + 1) * 3 + 2] = nodes[j * 3 + 2];
    }

    return { nodes, connections };
  }, [details, radius, connectionDistance]);

  // Animation: slow rotation and pulsing
  useFrame((state, delta) => {
    if (!globeRef.current) return;
    
    // Rotate the entire globe
    globeRef.current.rotation.x += rotationSpeed[0] * delta;
    globeRef.current.rotation.y += rotationSpeed[1] * delta;
    globeRef.current.rotation.z += rotationSpeed[2] * delta;
    
    // Pulsing effect: subtle scale pulse
    const pulse = 1 + Math.sin(state.clock.getElapsedTime() * 0.5) * 0.05; // 5% pulse
    globeRef.current.scale.set(pulse, pulse, pulse);
  });

  return (
    <group ref={globeRef} position={position} rotation={rotation} scale={scale}>
      {/* Nodes - as points */}
      <points>
        <bufferGeometry>
          <bufferAttribute
            attach="position"
            count={details}
            itemSize={3}
            array={nodes}
          />
        </bufferGeometry>
        <pointsMaterial
          color={nodeColor}
          size={0.05}
          transparent
          opacity={0.8}
          blending={THREE.AdditiveBlending}
        />
      </points>
      
      {/* Connections - as lines */}
      <line>
        <bufferGeometry>
          <bufferAttribute
            attach="position"
            count={connections.length / 3}
            itemSize={3}
            array={connections}
          />
        </bufferGeometry>
        <lineBasicMaterial
          color={connectionColor}
          transparent
          opacity={0.5}
        />
      </line>
    </group>
  );
};

export default NeuralNetworkGlobe;

