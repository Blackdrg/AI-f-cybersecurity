/**
 * Enhanced Error Boundary — Enterprise AI Platform
 *
 * Features:
 * - Error reporting to monitoring service
 * - Retry without full page reload
 * - Per-feature error boundaries
 * - Graceful degradation
 */
import React, { Component, type ErrorInfo, type ReactNode } from 'react';
import { Box, Typography, Button, Paper, Collapse } from '@mui/material';
import { BugReport, Refresh, ExpandMore } from '@mui/icons-material';
import { colors, glass } from '../../theme/tokens';

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  showDetails: boolean;
}

interface ErrorBoundaryProps {
  children: ReactNode;
  /** Fallback UI to show instead of the default error display */
  fallback?: ReactNode | ((error: Error, reset: () => void) => ReactNode);
  /** Optional label for identifying which boundary caught the error */
  boundaryName?: string;
  /** Called when an error is caught */
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  /** If true, show a compact inline error instead of full-page */
  inline?: boolean;
}

class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null, showDetails: false };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({ errorInfo });

    // Report to external service
    this.props.onError?.(error, errorInfo);

    // Report to window.trackError if available (Sentry, etc.)
    if (typeof window !== 'undefined' && window.trackError) {
      window.trackError({
        type: 'react_error_boundary',
        boundary: this.props.boundaryName || 'unknown',
        error: error.message,
        stack: error.stack,
        componentStack: errorInfo.componentStack,
        timestamp: new Date().toISOString(),
      });
    }

    console.error(`[ErrorBoundary:${this.props.boundaryName || 'root'}]`, error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null, showDetails: false });
  };

  handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError && this.state.error) {
      // Custom fallback
      if (this.props.fallback) {
        if (typeof this.props.fallback === 'function') {
          return this.props.fallback(this.state.error, this.handleReset);
        }
        return this.props.fallback;
      }

      // Inline error (compact)
      if (this.props.inline) {
        return (
          <Paper
            sx={{
              p: 2,
              m: 1,
              ...glass.light,
              borderLeft: `3px solid ${colors.semantic.error}`,
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <BugReport sx={{ color: colors.semantic.error, fontSize: 20 }} />
              <Box sx={{ flex: 1 }}>
                <Typography variant="body2" sx={{ fontWeight: 600, color: colors.text.primary }}>
                  Component Error
                </Typography>
                <Typography variant="caption" sx={{ color: colors.text.tertiary }}>
                  {this.state.error.message}
                </Typography>
              </Box>
              <Button size="small" startIcon={<Refresh />} onClick={this.handleReset}>
                Retry
              </Button>
            </Box>
          </Paper>
        );
      }

      // Full page error (default)
      return (
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100vh',
            p: 3,
            bgcolor: colors.surface.base,
          }}
        >
          <Paper
            sx={{
              p: 4,
              maxWidth: 500,
              textAlign: 'center',
              ...glass.medium,
            }}
          >
            <BugReport sx={{ color: colors.semantic.error, fontSize: 64, mb: 2 }} />
            <Typography variant="h5" gutterBottom sx={{ color: colors.text.primary }}>
              Something went wrong
            </Typography>
            <Typography sx={{ color: colors.text.secondary, mb: 3 }}>
              {this.state.error.message || 'An unexpected error occurred.'}
            </Typography>

            <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center', mb: 2 }}>
              <Button variant="contained" startIcon={<Refresh />} onClick={this.handleReset}>
                Try Again
              </Button>
              <Button variant="outlined" onClick={this.handleReload}>
                Reload Page
              </Button>
            </Box>

            {/* Expandable error details for devs */}
            {process.env.NODE_ENV === 'development' && (
              <>
                <Button
                  size="small"
                  endIcon={<ExpandMore />}
                  onClick={() => this.setState((s) => ({ showDetails: !s.showDetails }))}
                  sx={{ color: colors.text.tertiary }}
                >
                  {this.state.showDetails ? 'Hide' : 'Show'} Details
                </Button>
                <Collapse in={this.state.showDetails}>
                  <Box
                    component="pre"
                    sx={{
                      mt: 2,
                      p: 2,
                      borderRadius: 2,
                      bgcolor: 'rgba(0,0,0,0.4)',
                      color: colors.semantic.error,
                      fontSize: '0.7rem',
                      textAlign: 'left',
                      overflow: 'auto',
                      maxHeight: 200,
                    }}
                  >
                    {this.state.error.stack}
                  </Box>
                </Collapse>
              </>
            )}
          </Paper>
        </Box>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;


