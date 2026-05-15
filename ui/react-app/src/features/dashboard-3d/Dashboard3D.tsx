// src/pages/Dashboard3D.tsx
import React, { useState, useEffect } from 'react';
import * as THREE from 'three';
import { Box, Typography, Container, Button, Chip, Tooltip } from '@mui/material';
import { People, CameraAlt, Security, Timeline, ShowChart, Radar, Shield, Insights, BugReport, NetworkCheck, AccountCircle, History, ViewInAr, Refresh } from '@mui/icons-material';
import SceneManager from '../../components/3d/SceneManager';
import HolographicCard from '../../components/3d/HolographicCard';
import BiometricScanner from '../../components/3d/BiometricScanner';
import NeuralNetworkGlobe from '../../components/3d/NeuralNetworkGlobe';
import ParticleSystem from '../../components/3d/ParticleSystem';
import './Dashboard3D.css';

const Dashboard3D: React.FC = () => {
  const [metrics, setMetrics] = useState({
    totalRecognitions: 12847,
    totalEnrollments: 2156,
    activeSessions: 47,
    accuracy: 0.998,
    avgConfidence: 0.94,
    deepfakeDetected: 12,
  });

  // Simulate loading metrics (in a real app, this would come from API)
  useEffect(() => {
    // Simulate fetching data
    const timer = setTimeout(() => {
      // Update with some random variation to simulate live data
      setMetrics(prev => ({
        ...prev,
        totalRecognitions: prev.totalRecognitions + Math.floor(Math.random() * 10),
        activeSessions: Math.max(1, prev.activeSessions + Math.floor(Math.random() * 5) - 2),
        avgConfidence: Math.min(0.99, Math.max(0.85, prev.avgConfidence + (Math.random() - 0.5) * 0.02)),
      }));
    }, 5000);
    
    return () => clearTimeout(timer);
  }, []);

  return (
    <Box sx={{ minHeight: '100vh', position: 'relative' }}>
      {/* 3D Scene */}
      <SceneManager>
        {/* Neural Network Globe - central feature */}
        <NeuralNetworkGlobe
          position={[0, 0, 0]}
          rotation={[0, 0, 0]}
          scale={[1, 1, 1]}
          radius={4}
          details={150}
          connectionDistance={2.2}
          nodeColor="#00ffff"
          connectionColor="#00ffff40"
          rotationSpeed={[0, 0.3, 0]}
        />
        
        {/* Floating holographic cards for metrics */}
        <HolographicCard 
          position={[-5, 2, -3]} 
          rotation={[0, Math.PI/3, 0]}
          color="#00bcd4"
          intensity={2}
          width={2.5}
          height={1.5}
          depth={0.2}
        >
        </HolographicCard>
        
        <HolographicCard 
          position={[0, 2, -3]} 
          rotation={[0, -Math.PI/3, 0]}
          color="#00ff00"
          intensity={1.5}
          width={2}
          height={1}
          depth={0.2}
        >
        </HolographicCard>
        
        <HolographicCard 
          position={[5, 2, -3]} 
          rotation={[0, 0, 0]}
          color="#ff00ff"
          intensity={2.2}
          width={2.2}
          height={1.2}
          depth={0.2}
        >
        </HolographicCard>
        
        {/* Additional metric cards */}
        <HolographicCard 
          position={[-3, 0.5, -4]} 
          rotation={[0, Math.PI/4, 0]}
          color="#ffff00"
          intensity={1.2}
          width={1.8}
          height={0.8}
          depth={0.15}
        >
        </HolographicCard>
        
        <HolographicCard 
          position={[3, 0.5, -4]} 
          rotation={[0, -Math.PI/4, 0]}
          color="#ff0000"
          intensity={1.8}
          width={1.8}
          height={0.8}
          depth={0.15}
        >
        </HolographicCard>
        
        {/* Biometric scanner */}
        <BiometricScanner 
          position={[0, -1, 3.5]} 
          rotation={[0, Math.PI, 0]}
          color="#00ff00"
          scanSpeed={2}
          width={2}
          height={0.1}
          depth={0.8}
        />
        
        {/* Floating notification spheres */}
        {/* We'll add some small floating spheres as notifications */}
        <group position={[0, 3, 0]}>
          {/* We'll create a pulsing sphere */}
          <mesh>
            <sphereGeometry args={[0.3, 16, 16]} />
            <meshStandardMaterial
              color="#00ffff"
              emissive="#00ffff"
              emissiveIntensity={2}
              transparent
              opacity={0.7}
              blending={THREE.AdditiveBlending}
            />
          </mesh>
        </group>
        
        {/* Particle system is already in SceneManager */}
      </SceneManager>
      
      {/* UI Overlay */}
      <Box sx={{ 
        position: 'absolute', 
        top: 0, 
        left: 0, 
        right: 0, 
        bottom: 0, 
        display: 'flex', 
        flexDirection: 'column', 
        padding: '20px',
        pointerEvents: 'none' /* Allow clicks to go through to 3D scene */
      }}>
        <Box sx={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'flex-start',
          width: '100%'
        }}>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <Typography 
              variant="h3" 
              color="text.primary"
              sx={{ 
                fontWeight: 700,
                textShadow: '0 0 15px rgba(0, 188, 212, 0.6)',
                letterSpacing: '1.5px'
              }}
            >
              Enterprise Identity Intelligence Platform
            </Typography>
            <Typography 
              variant="h5" 
              color="text.secondary"
              sx={{ 
                fontSize: '1.25rem',
                opacity: 0.85,
                fontWeight: 400
              }}
            >
              Zero-Knowledge Biometric Recognition System v2.0 - Neural Command Center
            </Typography>
          </Box>
          
          <Box sx={{ display: 'flex', gap: '20px', alignItems: 'flex-start' }}>
            <Tooltip title="System Health">
              <Box sx={{ 
                display: 'flex', 
                flexDirection: 'column', 
                alignItems: 'center',
                background: 'rgba(10, 10, 10, 0.7)',
                backdropFilter: 'blur(10px)',
                borderRadius: '16px',
                padding: '16px 20px',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                boxShadow: '0 4px 16px rgba(0, 0, 0, 0.3)'
              }}>
                <Chip 
                  label="OPTIMAL" 
                  color="success"
                  sx={{ 
                    fontSize: '1rem',
                    fontWeight: 600,
                    height: '32px'
                  }}
                />
                <Typography variant="body2" color="text.secondary">
                  All Systems Nominal
                </Typography>
              </Box>
            </Tooltip>
            
            <Tooltip title="Active Sessions">
              <Box sx={{ 
                display: 'flex', 
                flexDirection: 'column', 
                alignItems: 'center',
                background: 'rgba(10, 10, 10, 0.7)',
                backdropFilter: 'blur(10px)',
                borderRadius: '16px',
                padding: '16px 20px',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                boxShadow: '0 4px 16px rgba(0, 0, 0, 0.3)'
              }}>
                <Chip 
                  label={metrics.activeSessions.toString()} 
                  color="info"
                  sx={{ 
                    fontSize: '1rem',
                    fontWeight: 600,
                    height: '32px'
                  }}
                />
                <Typography variant="body2" color="text.secondary">
                  Active Sessions
                </Typography>
              </Box>
            </Tooltip>
            
            <Tooltip title="Recognition Rate">
              <Box sx={{ 
                display: 'flex', 
                flexDirection: 'column', 
                alignItems: 'center',
                background: 'rgba(10, 10, 10, 0.7)',
                backdropFilter: 'blur(10px)',
                borderRadius: '16px',
                padding: '16px 20px',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                boxShadow: '0 4px 16px rgba(0, 0, 0, 0.3)'
              }}>
                <Chip 
                  label={(metrics.avgConfidence * 100).toFixed(1) + '%'} 
                  color="warning"
                  sx={{ 
                    fontSize: '1rem',
                    fontWeight: 600,
                    height: '32px'
                  }}
                />
                <Typography variant="body2" color="text.secondary">
                  Avg Confidence
                </Typography>
              </Box>
            </Tooltip>
            
            <Tooltip title="Threats Blocked">
              <Box sx={{ 
                display: 'flex', 
                flexDirection: 'column', 
                alignItems: 'center',
                background: 'rgba(10, 10, 10, 0.7)',
                backdropFilter: 'blur(10px)',
                borderRadius: '16px',
                padding: '16px 20px',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                boxShadow: '0 4px 16px rgba(0, 0, 0, 0.3)'
              }}>
                <Chip 
                  label={metrics.deepfakeDetected.toString()} 
                  color="error"
                  sx={{ 
                    fontSize: '1rem',
                    fontWeight: 600,
                    height: '32px'
                  }}
                />
                <Typography variant="body2" color="text.secondary">
                  Threats Blocked
                </Typography>
              </Box>
            </Tooltip>
          </Box>
        </Box>
        
        {/* Bottom controls */}
        <Box sx={{ 
          position: 'absolute', 
          bottom: '24px', 
          left: '50%', 
          transform: 'translateX(-50%)',
          display: 'flex',
          gap: '24px'
        }}>
          <Button 
            variant="contained"
            size="large"
            sx={{ 
              background: 'linear-gradient(45deg, #00bcd4 30%, #0097a7 90%)',
              color: 'white',
              textTransform: 'none',
              fontWeight: 600,
              padding: '14px 28px',
              borderRadius: '12px',
              boxShadow: '0 6px 24px rgba(0, 188, 212, 0.4)',
              fontSize: '1.1rem'
            }}
            startIcon={<People />}
          >
            Enroll New Identity
          </Button>
          
          <Button 
            variant="outlined"
            size="large"
            sx={{ 
              borderColor: 'rgba(0, 188, 212, 0.6)',
              color: '#00bcd4',
              textTransform: 'none',
              fontWeight: 600,
              padding: '14px 28px',
              borderRadius: '12px',
              fontSize: '1.1rem'
            }}
            startIcon={<Refresh />}
          >
            Refresh Data
          </Button>
          
          <Button 
            variant="contained"
            size="large"
            sx={{ 
              background: 'linear-gradient(45deg, #ff00ff 30%, #c2185b 90%)',
              color: 'white',
              textTransform: 'none',
              fontWeight: 600,
              padding: '14px 28px',
              borderRadius: '12px',
              boxShadow: '0 6px 24px rgba(255, 0, 255, 0.4)',
              fontSize: '1.1rem'
            }}
            startIcon={<Timeline />}
          >
            View Analytics
          </Button>
          
          <Button 
            variant="contained"
            size="large"
            sx={{ 
              background: 'linear-gradient(45deg, #00ff00 30%, #00c200 90%)',
              color: 'white',
              textTransform: 'none',
              fontWeight: 600,
              padding: '14px 28px',
              borderRadius: '12px',
              boxShadow: '0 6px 24px rgba(0, 255, 0, 0.4)',
              fontSize: '1.1rem'
            }}
            startIcon={<Security />}
          >
            Security Overview
          </Button>
        </Box>
      </Box>
    </Box>
  );
};

export default Dashboard3D;




