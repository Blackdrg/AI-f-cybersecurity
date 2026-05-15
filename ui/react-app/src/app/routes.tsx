/**
 * App Routes — Lazy-loaded route definitions
 *
 * Every feature module is code-split via React.lazy.
 */
import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Box, LinearProgress } from '@mui/material';
import ErrorBoundary from '../components/feedback/ErrorBoundary';

// ─── Lazy-loaded pages ──────────────────────────────────────────

const Dashboard = lazy(() => import('../features/dashboard/Dashboard'));
const Dashboard3D = lazy(() => import('../features/dashboard-3d/Dashboard3D'));
const LoginPage = lazy(() => import('../features/auth/Login'));

// ─── Route Loading Fallback ─────────────────────────────────────

const RouteLoader: React.FC = () => (
  <Box
    sx={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      height: '100vh',
      gap: 2,
    }}
  >
    <LinearProgress sx={{ width: 200 }} />
  </Box>
);

// ─── Route Wrapper with Error Boundary ──────────────────────────

const RouteWithBoundary: React.FC<{ children: React.ReactNode; name: string }> = ({
  children,
  name,
}) => (
  <ErrorBoundary boundaryName={name} inline={false}>
    <Suspense fallback={<RouteLoader />}>{children}</Suspense>
  </ErrorBoundary>
);

// ─── App Routes ─────────────────────────────────────────────────

const AppRoutes: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/login"
          element={
            <RouteWithBoundary name="login">
              <LoginPage />
            </RouteWithBoundary>
          }
        />
        <Route
          path="/dashboard/*"
          element={
            <RouteWithBoundary name="dashboard">
              <Dashboard />
            </RouteWithBoundary>
          }
        />
        <Route
          path="/dashboard-3d"
          element={
            <RouteWithBoundary name="dashboard-3d">
              <Dashboard3D />
            </RouteWithBoundary>
          }
        />
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  );
};

export default AppRoutes;


