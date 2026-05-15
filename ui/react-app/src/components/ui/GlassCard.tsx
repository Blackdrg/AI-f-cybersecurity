/**
 * GlassCard — Reusable glassmorphism card component
 *
 * Replaces inline sx glassmorphism styles used throughout the codebase.
 * Uses motion.div for animations to avoid ref incompatibility with MUI Paper.
 */
import React from 'react';
import { Box, type BoxProps } from '@mui/material';
import { motion } from 'framer-motion';
import { glass } from '../../theme/tokens';

type GlassVariant = 'thin' | 'light' | 'medium' | 'heavy' | 'dark';

interface GlassCardProps extends Omit<BoxProps, 'ref'> {
  variant?: GlassVariant;
  hoverEffect?: boolean;
  glowColor?: string;
  animated?: boolean;
}

const GlassCard: React.FC<GlassCardProps> = ({
  variant = 'light',
  hoverEffect = false,
  glowColor,
  animated = true,
  children,
  sx,
  onClick,
  ...props
}) => {
  const glassStyle = glass[variant];

  return (
    <motion.div
      initial={animated ? { opacity: 0, y: 10 } : undefined}
      animate={animated ? { opacity: 1, y: 0 } : undefined}
      transition={animated ? { duration: 0.3 } : undefined}
      whileHover={
        hoverEffect
          ? {
              y: -2,
              boxShadow: glowColor
                ? `0 0 20px ${glowColor}40`
                : '0 8px 25px rgba(0, 0, 0, 0.3)',
              transition: { duration: 0.2 },
            }
          : undefined
      }
      style={{ cursor: onClick ? 'pointer' : undefined }}
      onClick={onClick as React.MouseEventHandler<HTMLDivElement>}
    >
      <Box
        sx={{
          background: glassStyle.background,
          backdropFilter: glassStyle.backdropFilter,
          border: glassStyle.border,
          borderRadius: 3,
          overflow: 'hidden',
          ...sx,
        }}
        {...props}
      >
        {children}
      </Box>
    </motion.div>
  );
};

export default GlassCard;


