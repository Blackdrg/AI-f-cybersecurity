/**
 * SkeletonLoader — Content-aware skeleton loading states
 *
 * Provides skeleton variants for different UI patterns.
 */
import React from 'react';
import { Box, Skeleton } from '@mui/material';
import { glass } from '../../theme/tokens';

interface SkeletonCardProps {
  count?: number;
}

/** Skeleton for MetricCard */
export const MetricCardSkeleton: React.FC = () => (
  <Box
    sx={{
      p: 2,
      borderRadius: 3,
      ...glass.light,
    }}
  >
    <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1.5 }}>
      <Skeleton variant="rounded" width={40} height={40} sx={{ bgcolor: 'rgba(255,255,255,0.06)' }} />
      <Box sx={{ flex: 1 }}>
        <Skeleton width="60%" height={14} sx={{ bgcolor: 'rgba(255,255,255,0.06)', mb: 0.5 }} />
        <Skeleton width="40%" height={28} sx={{ bgcolor: 'rgba(255,255,255,0.08)' }} />
        <Skeleton width="30%" height={12} sx={{ bgcolor: 'rgba(255,255,255,0.04)', mt: 0.5 }} />
      </Box>
    </Box>
  </Box>
);

/** Skeleton for a chart/panel area */
export const ChartSkeleton: React.FC = () => (
  <Box sx={{ p: 3, borderRadius: 3, ...glass.light }}>
    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
      <Skeleton width="30%" height={20} sx={{ bgcolor: 'rgba(255,255,255,0.06)' }} />
      <Skeleton width={60} height={20} sx={{ bgcolor: 'rgba(255,255,255,0.04)' }} />
    </Box>
    <Skeleton variant="rounded" height={200} sx={{ bgcolor: 'rgba(255,255,255,0.04)' }} />
  </Box>
);

/** Skeleton for a data table */
export const TableSkeleton: React.FC<SkeletonCardProps> = ({ count = 5 }) => (
  <Box sx={{ p: 2, borderRadius: 3, ...glass.light }}>
    <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
      {[1, 2, 3, 4].map((i) => (
        <Skeleton key={i} width={`${25}%`} height={16} sx={{ bgcolor: 'rgba(255,255,255,0.08)' }} />
      ))}
    </Box>
    {Array.from({ length: count }).map((_, i) => (
      <Box key={i} sx={{ display: 'flex', gap: 2, mb: 1.5 }}>
        {[1, 2, 3, 4].map((j) => (
          <Skeleton key={j} width={`${25}%`} height={14} sx={{ bgcolor: 'rgba(255,255,255,0.04)' }} />
        ))}
      </Box>
    ))}
  </Box>
);

/** Skeleton for the full dashboard (6 metrics + 4 charts + table) */
export const DashboardSkeleton: React.FC = () => (
  <Box>
    <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 2, mb: 3 }}>
      {Array.from({ length: 6 }).map((_, i) => (
        <MetricCardSkeleton key={i} />
      ))}
    </Box>
    <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: '1fr 1fr' }, gap: 2, mb: 3 }}>
      <ChartSkeleton />
      <ChartSkeleton />
    </Box>
    <TableSkeleton count={8} />
  </Box>
);

export default DashboardSkeleton;


