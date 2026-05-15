// src/components/FloatingPanel.tsx
import React from 'react';
import { Box, Paper, Button, Typography, IconButton } from '@mui/material';
import { motion } from 'framer-motion';
import { KeyboardArrowUp as ChevronUp, KeyboardArrowDown as ChevronDown } from '@mui/icons-material';

interface FloatingPanelProps {
  children: React.ReactNode;
  title?: string;
  open?: boolean;
  onToggle?: () => void;
}

const FloatingPanel = ({ 
  children, 
  title = 'Floating Panel', 
  open = false, 
  onToggle 
}: FloatingPanelProps) => {
  return (
    <motion.div
      initial={{ y: 100 }} // Start off screen below
      animate={{ y: open ? 0 : 100 }} // When open, y:0 (visible), when closed, y:100 (hidden)
      exit={{ y: 100 }}
      transition={{ duration: 0.3, ease: [0.25, 0.1, 0.25, 1] }}
      style={{ 
        position: 'fixed', 
        bottom: 0, 
        left: 0, 
        right: 0, 
        display: 'flex', 
        flexDirection: 'column', 
        alignItems: 'stretch'
      }}
    >
      <Paper
        sx={{ 
          margin: '16px', 
          borderRadius: '16px', 
          background: 'rgba(10, 10, 10, 0.7)', 
          backdropFilter: 'blur(10px)', 
          border: '1px solid rgba(255, 255, 255, 0.1)',
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5)'
        }}
      >
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', p: 3 }}>
          <Typography variant="h6" color="text.primary" sx={{ fontWeight: 600 }}>
            {title}
          </Typography>
          <IconButton onClick={onToggle} size="small">
            {open ? <ChevronUp /> : <ChevronDown />}
          </IconButton>
        </Box>
        <Box sx={{ p: 3, pt: 0 }}>
          {children}
        </Box>
      </Paper>
    </motion.div>
  );
};

export default FloatingPanel;

