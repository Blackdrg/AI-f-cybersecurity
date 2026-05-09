import React from 'react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { CssBaseline, Box } from '@mui/material';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import ErrorBoundary from './components/ErrorBoundary';
import LoginPage from './pages/Login';
import Dashboard from './pages/Dashboard';
import SetupWizard from './components/SetupWizard';

const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: { main: '#00bcd4' },
    secondary: { main: '#ff4081' },
    background: { default: '#0a0a0a', paper: '#1a1a1a' },
  },
  typography: { fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif' },
  components: {
    MuiButton: { styleOverrides: { root: { borderRadius: 8, textTransform: 'none', fontWeight: 600 } } },
    MuiPaper: { styleOverrides: { root: { borderRadius: 12 } } },
  },
});

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
          <Dashboard />
        )
      )}
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
