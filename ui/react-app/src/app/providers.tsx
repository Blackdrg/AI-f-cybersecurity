/**
 * App Providers — Wraps the app with all required providers
 *
 * Centralizes: Theme, React Query, Auth initialization, WebSocket
 */
import React, { useEffect, type ReactNode } from 'react';
import { ThemeProvider, CssBaseline } from '@mui/material';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import theme from '../theme/theme';
import { initializeAuth } from '../stores/authStore';
import { useWSConnection } from '../services/websocket/hooks';

// ─── React Query Client ─────────────────────────────────────────

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,        // 30s before refetch
      retry: 2,
      refetchOnWindowFocus: true,
      refetchOnReconnect: true,
    },
    mutations: {
      retry: 1,
    },
  },
});

// ─── Auth + WS Initializer ──────────────────────────────────────

const AppInitializer: React.FC<{ children: ReactNode }> = ({ children }) => {
  // Initialize auth on mount (checks httpOnly cookie)
  useEffect(() => {
    initializeAuth();
  }, []);

  // Connect WebSocket
  useWSConnection(true);

  return <>{children}</>;
};

// ─── Combined Provider ──────────────────────────────────────────

interface AppProvidersProps {
  children: ReactNode;
}

const AppProviders: React.FC<AppProvidersProps> = ({ children }) => {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <AppInitializer>{children}</AppInitializer>
      </ThemeProvider>
    </QueryClientProvider>
  );
};

export default AppProviders;
export { queryClient };


