import React from 'react';
import { ThemeProvider, CssBaseline, Box } from '@mui/material';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import ErrorBoundary from './components/ErrorBoundary';
import LoginPage from './pages/Login';
import Dashboard from './pages/Dashboard';
import SetupWizard from './components/SetupWizard';
import Dashboard3D from './pages/Dashboard3D';
import AIFloatingAssistant from './components/AIFloatingAssistant';
import theme from './theme/theme';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';

interface AppContentProps {
  // No additional props required
}

function AppContent(): JSX.Element {
  const { user } = useAuth();

  return (
    <Box sx={{ minHeight: '100vh' }}>
      {!user ? (
        <LoginPage />
      ) : (
        user.role === 'admin' && !localStorage.getItem('setup_complete') ? (
          <SetupWizard onComplete={() => localStorage.setItem('setup_complete', 'true')} />
        ) : (
          <BrowserRouter>
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/setup" element={<SetupWizard onComplete={() => localStorage.setItem('setup_complete', 'true')} />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/dashboard-3d" element={<Dashboard3D />} />
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
            </Routes>
          </BrowserRouter>
        )
      )}
      <AIFloatingAssistant />
    </Box>
  );
}

function App(): JSX.Element {
  return (
    <ErrorBoundary>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <AuthProvider>
          <AppContent />
        </AuthProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export default App;
