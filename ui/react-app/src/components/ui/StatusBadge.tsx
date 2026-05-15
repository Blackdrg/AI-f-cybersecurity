/**
 * StatusBadge — System health / status indicator
 *
 * Replaces duplicated status chip logic in Dashboard and DashboardHome.
 */
import React from 'react';
import { Chip, type ChipProps } from '@mui/material';
import { CheckCircle, Warning, Error as ErrorIcon, HourglassEmpty } from '@mui/icons-material';
import { colors } from '../../theme/tokens';

type StatusType = 'healthy' | 'degraded' | 'unhealthy' | 'unconfigured' | 'loading' | 'online' | 'offline';

interface StatusBadgeProps extends Omit<ChipProps, 'color'> {
  status: StatusType;
  showIcon?: boolean;
}

const statusConfig: Record<StatusType, { color: string; bg: string; icon: React.ReactElement; label: string }> = {
  healthy: { color: colors.semantic.success, bg: `${colors.semantic.success}20`, icon: <CheckCircle />, label: 'Healthy' },
  online: { color: colors.semantic.success, bg: `${colors.semantic.success}20`, icon: <CheckCircle />, label: 'Online' },
  degraded: { color: colors.semantic.warning, bg: `${colors.semantic.warning}20`, icon: <Warning />, label: 'Degraded' },
  unhealthy: { color: colors.semantic.error, bg: `${colors.semantic.error}20`, icon: <ErrorIcon />, label: 'Unhealthy' },
  offline: { color: colors.semantic.error, bg: `${colors.semantic.error}20`, icon: <ErrorIcon />, label: 'Offline' },
  unconfigured: { color: colors.text.tertiary, bg: `${colors.text.tertiary}20`, icon: <HourglassEmpty />, label: 'Unconfigured' },
  loading: { color: colors.text.tertiary, bg: `${colors.text.tertiary}20`, icon: <HourglassEmpty />, label: 'Loading' },
};

const StatusBadge: React.FC<StatusBadgeProps> = ({ status, showIcon = true, ...props }) => {
  const config = statusConfig[status] || statusConfig.unconfigured;

  return (
    <Chip
      icon={showIcon ? config.icon : undefined}
      label={props.label || config.label}
      size="small"
      sx={{
        bgcolor: config.bg,
        color: config.color,
        border: `1px solid ${config.color}40`,
        fontWeight: 600,
        fontSize: '0.7rem',
        '& .MuiChip-icon': { color: config.color },
        ...props.sx,
      }}
      {...props}
    />
  );
};

export default StatusBadge;


