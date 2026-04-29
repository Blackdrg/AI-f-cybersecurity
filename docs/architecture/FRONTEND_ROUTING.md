# Frontend Routing & Navigation Architecture

## Overview
The AI-f Sovereign OS frontend uses a **State-Driven Routing** pattern rather than a path-based router (like `react-router-dom` in its typical usage). This is a security-by-design choice to ensure that the UI state is tightly coupled to the `AuthContext` and session state.

## Core Navigation Loop
The primary navigation is managed in `src/pages/Dashboard.js` via the `activePage` state.

### Available Routes
| Page ID | Required Permissions | Description |
|:---|:---|:---|
| `dashboard` | `VIEW_DASHBOARD` | System overview, health, and key metrics. |
| `enroll` | `ENROLL_IDENTITY` | Multi-modal identity enrollment wizard. |
| `recognize` | `VIEW_RECOGNITIONS` | Single-frame and stream recognition interface. |
| `admin` | `MANAGE_USERS` | User management, organization settings, and policy config. |
| `cameras` | `MANAGE_CAMERAS` | RTSP stream management and camera health. |
| `person-profile`| `VIEW_IDENTITIES` | Detailed forensic profile for a specific person_id. |
| `analytics` | `VIEW_ANALYTICS` | Intelligence hub, bias reports, and historical trends. |
| `compliance` | `VIEW_COMPLIANCE` | GDPR erasure, audit logs, and forensic verification. |
| `developer` | `VIEW_DASHBOARD` | API keys, documentation, and SDK downloads. |
| `audit` | `VIEW_AUDIT_LOGS` | Hash-chained forensic timeline. |
| `incidents` | `MANAGE_INCIDENTS` | Active alert monitoring and incident response. |

## Guarding Mechanisms
### 1. Sidebar Filtering
The `Sidebar.js` component filters menu items based on the user's role and permission set. If a user lacks the required permission, the navigation option is not rendered.

### 2. RBACGuard
All pages are wrapped in an `<RBACGuard>` component which performs a secondary check on the client side.
```javascript
<RBACGuard requiredPermissions={[PERMISSIONS.ENROLL_IDENTITY]}>
  <EnrollPage />
</RBACGuard>
```

### 3. API Interceptor
Even if a user bypasses UI guards, the `api.js` interceptor and Backend middleware will reject unauthorized requests with a `403 Forbidden` and the corresponding `ErrorDetail` code.

## Navigation Actions
Navigation is triggered via the `setActivePage` function passed to the `Sidebar` and other child components. 
```javascript
const handlePageChange = (newPage) => {
  setActivePage(newPage);
  window.scrollTo(0, 0); // Reset scroll position
};
```
