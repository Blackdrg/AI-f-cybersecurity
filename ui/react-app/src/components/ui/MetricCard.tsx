/**
 * MetricCard — Dashboard metric display card
 *
 * Replaces the 6x duplicated metric card pattern in DashboardHome.
 */
import React from 'react';
import { Box, Typography } from '@mui/material';
import { motion } from 'framer-motion';
import GlassCard from './GlassCard';
import { colors, spacing } from '../../theme/tokens';

interface MetricCardProps {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  change?: string;
  changeType?: 'positive' | 'negative' | 'neutral';
  accentColor?: string;
  onClick?: () => void;
}

const MetricCard: React.FC<MetricCardProps> = ({
  icon,
  label,
  value,
  change,
  changeType = 'neutral',
  accentColor = colors.brand.primary,
  onClick,
}) => {
  const changeColor =
    changeType === 'positive'
      ? colors.semantic.success
      : changeType === 'negative'
        ? colors.semantic.error
        : colors.text.tertiary;

  return (
    <GlassCard
      hoverEffect
      glowColor={accentColor}
      sx={{
        p: spacing.md / 4,
        cursor: onClick ? 'pointer' : 'default',
        position: 'relative',
        overflow: 'hidden',
      }}
      onClick={onClick}
    >
      {/* Accent top border */}
      <Box
        sx={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: 3,
          background: `linear-gradient(90deg, ${accentColor}, ${accentColor}80)`,
          borderRadius: '12px 12px 0 0',
        }}
      />

      <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1.5, pt: 1 }}>
        <Box
          sx={{
            width: 40,
            height: 40,
            borderRadius: 2,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: `${accentColor}18`,
            color: accentColor,
            flexShrink: 0,
          }}
        >
          {icon}
        </Box>

        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography
            variant="caption"
            sx={{
              color: colors.text.tertiary,
              fontWeight: 500,
              fontSize: '0.7rem',
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
            }}
          >
            {label}
          </Typography>

          <motion.div
            key={String(value)}
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
          >
            <Typography
              variant="h5"
              sx={{
                fontWeight: 700,
                color: colors.text.primary,
                lineHeight: 1.2,
                fontSize: '1.3rem',
              }}
            >
              {value}
            </Typography>
          </motion.div>

          {change && (
            <Typography
              variant="caption"
              sx={{ color: changeColor, fontWeight: 600, fontSize: '0.7rem' }}
            >
              {change}
            </Typography>
          )}
        </Box>
      </Box>
    </GlassCard>
  );
};

export default MetricCard;


