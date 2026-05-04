import React, { useState, useEffect } from 'react';
import { Box, Typography, Button, Paper } from '@mui/material';
import { BugReport, Refresh } from '@mui/icons-material';
import { ErrorState } from '../types';

interface ErrorBoundaryProps {
  children: React.ReactNode;
}

const ErrorBoundary: React.FC<ErrorBoundaryProps> = ({ children }) => {
  const [state, setState] = useState<ErrorState>({ hasError: false, error: null });

  const handleReset = () => {
    setState({ hasError: false, error: null });
    window.location.reload();
  };

  if (state.hasError) {
    return (
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100vh',
          p: 3,
          bgcolor: 'background.default'
        }}
      >
        <Paper sx={{ p: 4, maxWidth: 500, textAlign: 'center' }}>
          <BugReport color="error" sx={{ fontSize: 64, mb: 2 }} />
          <Typography variant="h5" gutterBottom>Something went wrong</Typography>
          <Typography color="text.secondary" sx={{ mb: 3 }}>
            {state.error?.message || "An unexpected frontend error occurred."}
          </Typography>
          <Button
            variant="contained"
            startIcon={<Refresh />}
            onClick={handleReset}
          >
            Reload Application
          </Button>
        </Paper>
      </Box>
    );
  }

  return <>{children}</>;
};

export default ErrorBoundary;

