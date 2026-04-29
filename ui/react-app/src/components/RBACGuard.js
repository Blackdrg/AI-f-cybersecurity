import React from 'react';
import { Box } from '@mui/material';
import { useAuth } from '../contexts/AuthContext';

export const ProtectedRoute = ({ children, requiredPermissions = [] }) => {
  const { user, canAccessRoute, loading } = useAuth();

  if (loading) {
    return <LoadingOverlay message="Verifying access permissions..." />;
  }

  if (!user) {
    return <Box sx={{ p: 3, textAlign: 'center' }}>Please login to continue.</Box>;
  }

  if (!canAccessRoute(requiredPermissions)) {
    return <Box sx={{ p: 3, textAlign: 'center', color: 'error.main' }}>Unauthorized Access</Box>;
  }

  return children;
};

export const PermissionGuard = ({ children, requiredPermission }) => {
  const { hasPermission } = useAuth();

  if (!hasPermission(requiredPermission)) {
    return null;
  }

  return children;
};

export const RoleBadge = ({ role }) => {
  const roleColors = {
    super_admin: { bg: '#7c3aed', color: 'white', label: 'Super Admin' },
    admin: { bg: '#2563eb', color: 'white', label: 'Admin' },
    operator: { bg: '#059669', color: 'white', label: 'Operator' },
    auditor: { bg: '#dc2626', color: 'white', label: 'Auditor' },
    analyst: { bg: '#ea580c', color: 'white', label: 'Analyst' },
    security: { bg: '#1e293b', color: 'white', label: 'Security' },
    hr: { bg: '#ec4899', color: 'white', label: 'HR' },
    viewer: { bg: '#64748b', color: 'white', label: 'Viewer' }
  };

  const config = roleColors[role?.toLowerCase()] || roleColors.viewer;

  return (
    <span
      style={{
        display: 'inline-block',
        padding: '2px 8px',
        borderRadius: '4px',
        fontSize: '11px',
        fontWeight: 600,
        textTransform: 'uppercase',
        letterSpacing: '0.5px',
        backgroundColor: config.bg,
        color: config.color
      }}
    >
      {config.label}
    </span>
  );
};

const LoadingOverlay = ({ message }) => (
  <div style={{
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: '400px',
    color: '#e2e8f0'
  }}>
    <div style={{
      width: '48px',
      height: '48px',
      border: '3px solid rgba(59, 130, 246, 0.2)',
      borderTopColor: '#3b82f6',
      borderRadius: '50%',
      animation: 'spin 1s linear infinite',
      marginBottom: '16px'
    }} />
    <p style={{ fontSize: '14px', color: '#64748b' }}>{message}</p>
    <style>{`
      @keyframes spin {
        to { transform: rotate(360deg); }
      }
    `}</style>
  </div>
);