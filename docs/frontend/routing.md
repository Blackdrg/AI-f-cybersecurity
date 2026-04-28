# Frontend Routing Documentation

## Overview

The AI-f frontend uses client-side routing via React Router (v6) for navigation between pages. The routing configuration is centralized in the `src/router.js` file.

## Router Structure

The router is defined in `src/router.js` and exported as the main `Router` component. It uses `BrowserRouter` for HTML5 history API.

## Routes

### Public Routes
- `/` - Login Page (`LoginPage`)
- `/setup` - Setup Wizard (only shown if user is admin and setup is not complete)

### Protected Routes (require authentication)
- `/dashboard` - Main Dashboard (`Dashboard`)
- `/persons` - Person Management (`PersonManagement`)
- `/persons/:id` - Person Profile (`PersonProfile`)
- `/enroll` - Enroll New Person (`Enroll`)
- `/organizations` - Organization Management (`OrganizationManagement`)
- `/organizations/:id` - Organization Details (`OrganizationDetails`)
- `/cameras` - Camera Management (`CameraManagement`)
- `/analytics` - Analytics Dashboard (`AnalyticsDashboard`)
- `/incidents` - Incident Management (`IncidentManagement`)
- `/audit` - Audit Log Viewer (`AuditLogViewer`)
- `/settings` - User Settings (`Settings`)
- `/admin` - Admin Panel (`AdminPanel`) (only for super_admin and admin roles)
- `/developer` - Developer Platform (`DeveloperPlatform`) (for developers and admins)

### Route Protection
- The `RequireAuth` wrapper component checks if the user is authenticated (has a valid token) and redirects to `/` if not.
- The `RequireRole` wrapper component checks the user's role and redirects to `/dashboard` if the user does not have the required role.

## Implementation Details

### Router Configuration (`src/router.js`)

```javascript
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { RequireAuth, RequireRole } from './components/RBACGuard';
import LoginPage from './pages/Login';
import SetupWizard from './components/SetupWizard';
import Dashboard from './pages/Dashboard';
import PersonManagement from './pages/PersonManagement';
import PersonProfile from './pages/PersonProfile';
import Enroll from './pages/Enroll';
import OrganizationManagement from './pages/OrganizationManagement';
import OrganizationDetails from './pages/OrganizationDetails';
import CameraManagement from './pages/CameraManagement';
import AnalyticsDashboard from './pages/AnalyticsDashboard';
import IncidentManagement from './pages/IncidentManagement';
import AuditLogViewer from './pages/AuditLogViewer';
import Settings from './pages/Settings';
import AdminPanel from './pages/AdminPanel';
import DeveloperPlatform from './pages/DeveloperPlatform';

function Router() {
  const { user } = useAppSelector(selectAuthState);

  return (
    <BrowserRouter>
      <Routes>
        {/* Public routes */}
        <Route path="/" element={<LoginPage />} />
        <Route 
          path="/setup" 
          element={
            user && user.role === 'admin' && !localStorage.getItem('setup_complete') ? 
            <SetupWizard onComplete={() => localStorage.setItem('setup_complete', 'true')} /> : 
            <Navigate to="/" replace />
          }
        />

        {/* Protected routes */}
        <Route 
          element={<RequireAuth />}> 
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/persons" element={<PersonManagement />} />
          <Route path="/persons/:id" element={<PersonProfile />} />
          <Route path="/enroll" element={<Enroll />} />
          <Route path="/organizations" element={<OrganizationManagement />} />
          <Route path="/organizations/:id" element={<OrganizationDetails />} />
          <Route path="/cameras" element={<CameraManagement />} />
          <Route path="/analytics" element={<AnalyticsDashboard />} />
          <Route path="/incidents" element={<IncidentManagement />} />
          <Route path="/audit" element={<AuditLogViewer />} />
          <Route path="/settings" element={<Settings />} />
          <Route 
            path="/admin" 
            element={
              <RequireRole roles={['super_admin', 'admin']}>
                <AdminPanel />
              </RequireRole>
            } 
          />
          <Route 
            path="/developer" 
            element={
              <RequireRole roles={['super_admin', 'admin', 'developer']}>
                <DeveloperPlatform />
              </RequireRole>
            } 
          />
        </Routes>
      </BrowserRouter>
  );
}

export default Router;
```

### RBACGuard Components (`src/components/RBACGuard.js`)

The `RBACGuard.js` file contains the `RequireAuth` and `RequireRole` components used for route protection.

```javascript
import { Navigate } from 'react-router-dom';
import { useAppSelector } from '../store';
import { selectAuthState } from '../features/auth/selectors';

export function RequireAuth({ children }) {
  const { isAuthenticated } = useAppSelector(selectAuthState);
  return isAuthenticated ? children : <Navigate to="/" replace />;
}

export function RequireRole({ roles, children }) {
  const { user } = useAppSelector(selectAuthState);
  const hasRole = user && roles.includes(user.role);
  return hasRole ? children : <Navigate to="/dashboard" replace />;
}
```

## Navigation in Components

Components use the `useNavigate` hook from `react-router-dom` for programmatic navigation or the `Link` component for declarative navigation.

Example:
```javascript
import { useNavigate } from 'react-router-dom';
import { Link } from 'react-router-dom';

function SomeComponent() {
  const navigate = useNavigate();

  const handleClick = () => {
    navigate('/persons/123');
  };

  return (
    <div>
      <Link to="/enroll">Enroll New Person</Link>
      <button onClick={handleClick}>Go to Person Profile</button>
    </div>
  );
}
```

## Lazy Loading

For performance, some routes are lazy-loaded using `React.lazy` and `Suspense`. This is implemented in the router for larger pages like `AdminPanel` and `DeveloperPlatform`.

Example:
```javascript
const AdminPanel = React.lazy(() => import('./pages/AdminPanel'));
const DeveloperPlatform = React.lazy(() => import('./pages/DeveloperPlatform'));

<Route 
  path="/admin" 
  element={
    <Suspense fallback={<div>Loading...</div>}>
      <RequireRole roles={['super_admin', 'admin']}>
        <AdminPanel />
      </RequireRole>
    </Suspense>
  } 
/>
```

## Environment Variables

The router uses the `REACT_APP_API_URL` environment variable for API calls made by components, but the routing itself is client-side and does not depend on environment variables for path configuration.

## Testing

Route testing is done using React Testing Library and `@testing-library/react-hooks` for the guard components, and `@testing-library/react` for the router component.

Example test for `RequireAuth`:
```javascript
test('redirects to login when not authenticated', () => {
  const { result } = renderHook(() => useAppSelector(selectAuthState), {
    wrapper: ({ children }) => <Provider store={mockStore({ auth: { isAuthenticated: false } })}>{children}</Provider>
  });
  // ... render RequireAuth and check for redirect
});
```
