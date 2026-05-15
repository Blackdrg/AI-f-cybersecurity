/**
 * App — Root application component
 *
 * Uses the new architecture:
 * - AppProviders (Theme, React Query, Auth, WebSocket)
 * - AppRoutes (lazy-loaded, error-bounded routes)
 * - Zustand stores (replaces Context)
 *
 * Backward compatibility:
 * - AuthProvider still exported from contexts/AuthContext.tsx
 * - Old components still work via existing imports
 */
import React from 'react';
import AppProviders from './app/providers';
import AppRoutes from './app/routes';
import ErrorBoundary from './components/feedback/ErrorBoundary';
import { AuthProvider } from './contexts/AuthContext';

function App(): JSX.Element {
  return (
    <ErrorBoundary boundaryName="root">
      <AppProviders>
        {/* Keep AuthProvider for backward compat with components using useAuth() */}
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </AppProviders>
    </ErrorBoundary>
  );
}

export default App;


