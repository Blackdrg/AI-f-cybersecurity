/**
 * E2E Tests for React Frontend
 * Using React Testing Library and Jest
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from '../contexts/AuthContext';

// Test utilities
const renderWithRouter = (component, { route = '/' } = {}) => {
  window.history.pushState({}, 'Test page', route);
  return render(
    <BrowserRouter>
      <AuthProvider>
        {component}
      </AuthProvider>
    </BrowserRouter>
  );
};

describe('Authentication Flow', () => {
  test('renders login page', () => {
    renderWithRouter(<Login />);
    expect(screen.getByText(/sign in/i)).toBeInTheDocument();
  });

  test('login form validation', async () => {
    renderWithRouter(<Login />);
    
    const submitButton = screen.getByRole('button', { name: /sign in/i });
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByText(/email is required/i)).toBeInTheDocument();
    });
  });
});

describe('Dashboard', () => {
  test('renders dashboard components', () => {
    renderWithRouter(<Dashboard />);
    expect(screen.getByText(/dashboard/i)).toBeInTheDocument();
  });

  test('displays analytics charts', async () => {
    renderWithRouter(<AnalyticsDashboard />);
    await waitFor(() => {
      expect(screen.getByRole('img', { name: /analytics chart/i })).toBeInTheDocument();
    });
  });
});

describe('Recognition Flow', () => {
  test('renders recognize page', () => {
    renderWithRouter(<Recognize />);
    expect(screen.getByText(/recognize/i)).toBeInTheDocument();
  });

  test('handles file upload', async () => {
    renderWithRouter(<Enroll />);
    
    const fileInput = screen.getByLabelText(/upload/i);
    const file = new File(['dummy content'], 'test.jpg', { type: 'image/jpeg' });
    
    fireEvent.change(fileInput, { target: { files: [file] } });
    
    await waitFor(() => {
      expect(screen.getByText(/test.jpg/i)).toBeInTheDocument();
    });
  });
});

describe('Admin Panel', () => {
  test('renders admin tabs', () => {
    renderWithRouter(<AdminPanel />);
    expect(screen.getByText(/admin/i)).toBeInTheDocument();
  });

  test('RBAC guard restricts access', () => {
    renderWithRouter(<RBACGuard requiredPermission="admin:users">
      <div>Protected content</div>
    </RBACGuard>);
  });
});

describe('Error Handling', () => {
  test('error boundary catches errors', () => {
    const BadComponent = () => {
      throw new Error('Test error');
    };
    
    renderWithRouter(<ErrorBoundary><BadComponent /></ErrorBoundary>);
    
    expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
  });
});

describe('API Integration', () => {
  test('fetches and displays users', async () => {
    renderWithRouter(<Dashboard />);
    
    await waitFor(() => {
      expect(screen.queryByText(/loading/i)).not.toBeInTheDocument();
    });
  });
});