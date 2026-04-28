# Frontend State Management & Data Fetching

## Architecture Overview

AI-f frontend uses **React 18** with **Context API** for global state and **Axios** for data fetching. No Redux is used — the architecture favors simplicity and built-in React patterns.

---

## State Management Strategy

### Global State: Context API

Global application state (auth, organization, user session) is managed via `AuthContext`:

**File:** `ui/react-app/src/contexts/AuthContext.js`

**Provides:**
- `user`: Current authenticated user object
- `organization`: Current active organization
- `organizations`: List of organizations user belongs to
- `hasPermission(permission)`: RBAC check
- `canAccessRoute(permissions)`: Route guard helper
- `login(userData, orgsData)`: Auth state update
- `logout()`: Clear auth state

**Usage:**
```jsx
import { useAuth } from '../contexts/AuthContext';

function Dashboard() {
  const { user, organization, hasPermission } = useAuth();
  
  if (hasPermission('VIEW_ANALYTICS')) {
    return <AnalyticsDashboard />;
  }
}
```

**Why Context over Redux?**
- Simpler mental model (no reducers, actions, dispatchers)
- Only 3-4 global values (user, org, token, loading state)
- No need for complex state normalization
- Easier to test and maintain

---

## Data Fetching: Axios Interceptors

API calls made via **Axios** with interceptors for:
- Automatic JWT token injection
- Standardized response format handling
- Error normalization
- Request/response logging

**File:** `ui/react-app/src/services/api.js`

**Key exports:**
- `login(email, password)`
- `recognize(file, options)`
- `enroll(files, name, consent, options)`
- `getAnalytics(timeframe)`
- `getBiasReport(params)`
- `getDecisionExplanation(id)`
- ... etc

**Response envelope:** `{ success: boolean, data: any, error?: string }`

**Error handling:**
```js
try {
  const result = await recognize(imageFile, { top_k: 1 });
  console.log(result.data.faces);
} catch (error) {
  alert(`Recognition failed: ${error.message}`);
}
```

---

## Component State: React Hooks

Component-local state uses standard React hooks:

```jsx
import React, { useState, useEffect, useCallback } from 'react';

function EnrollPage() {
  const [images, setImages] = useState([]);
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState(1); // multi-step form
  
  const handleSubmit = async () => {
    setLoading(true);
    try {
      await enroll(images, name, true);
      setStep(2); // success
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <form onSubmit={handleSubmit}>
      {/* ... */}
    </form>
  );
}
```

---

## Authentication Flow

1. User submits credentials → `/api/auth/login`
2. Server returns `{ access_token, user, mfa_required? }`
3. Token stored in `localStorage` (survives refresh)
4. User object stored in `localStorage`
5. `AuthContext` updates state
6. Axios interceptor adds token to all subsequent requests

**Token refresh:** Manual via `/api/auth/refresh` endpoint (stored refresh token)

**Logout:** Clear localStorage + context state + redirect to `/login`

---

## RBAC (Role-Based Access Control)

Permission checks via `hasPermission()` from `AuthContext`:

```jsx
import { useAuth } from '../contexts/AuthContext';

function AdminPanel() {
  const { hasPermission } = useAuth();
  
  if (!hasPermission('MANAGE_USERS')) {
    return <div>Access denied</div>;
  }
  
  return <UserManagement />;
}
```

Alternatively, route-level guard via `RBACGuard` component:

```jsx
import RBACGuard from '../components/RBACGuard';

<Route path="/admin" element={
  <RBACGuard requiredPermission="MANAGE_USERS">
    <AdminDashboard />
  </RBACGuard>
} />
```

---

## WebSocket Connection Management

Live recognition streams managed via `WebSocketContext` or `useRecognitionStream` hook:

```jsx
import { useRecognitionStream } from '../hooks/useRecognitionStream';

function LiveFeed() {
  const { connect, disconnect, latestResults, streaming } = useRecognitionStream();
  
  const start = () => connect({ camera_id: 'cam_01', top_k: 1 });
  const stop = () => disconnect();
  
  return (
    <div>
      <button onClick={startring}>Start</button>
      <button onClick={stop}>Stop</button>
      {latestResults.map(result => (
        <FaceResult key={result.id} result={result} />
      ))}
    </div>
  );
}
```

---

## File Structure

```
ui/react-app/src/
├── components/          # Reusable presentational components (15)
│   ├── Sidebar.js
│   ├── UploadBox.js
│   ├── WebcamCapture.js
│   ├── ResultCard.js
│   └── ...
├── pages/              # Route-level pages (15 JS + 3 TSX)
│   ├── Dashboard.js
│   ├── Enroll.js
│   ├── Recognize.js
│   ├── AdminPanel.js
│   └── ...
├── contexts/           # React Context providers
│   └── AuthContext.js
├── services/           # API layer
│   ├── api.js           # Standard axios wrapper
│   └── apiEnhanced.js   # Enhanced with error classes
├── hooks/              # Custom React hooks
│   ├── useRecognitionStream.js
│   └── useWebSocket.js
└── utils/              # Utilities
    └── formatters.js
```

**Total source files:** 41 JavaScript + 3 TypeScript (`.tsx`)
**Total frontend LOC:** ~10,000

---

## TypeScript Migration

Partial migration in progress:
- **JavaScript:** 97% of codebase (`.js` files)
- **TypeScript:** 3% (`.tsx` files: `ConsentModal.tsx`, `EnrichResultsPage.tsx`, `index.tsx`)

New components should be written in TypeScript. Existing JS components will be converted incrementally.

---

## State Persistence

**Persisted to localStorage:**
- `token` — JWT access token
- `user` — Current user object
- `organization` — Current org selection
- `organizations` — List of user's orgs

**Not persisted:**
- Temporary UI state (form drafts, modals open/closed)
- WebSocket connection state
- Load spinner states

---

## Performance Optimizations

1. **Memoization:** `useMemo` for computed values, `useCallback` for event handlers
2. **List virtualization:** Planned for large tables (react-window)
3. **Code splitting:** React.lazy for route-based splitting
4. **Image optimization:** WebP format, lazy loading
5. **API caching:** Not implemented (would benefit from React Query)

---

## Future Improvements

- [ ] Move from Context → Redux Toolkit RTK Query for data fetching (optional)
- [ ] Add React Query for server-state caching
- [ ] Implement optimistic updates for enroll/delete
- [ ] Add end-to-end TypeScript (convert all .js → .tsx)
- [ ] Add state persistence library (redux-persist alternative)
- [ ] Implement request cancellation on component unmount
- [ ] Add offline queue for actions (retry on reconnect)

---

**Note:** The earlier Redux Toolkit architecture described in `state_management.md` was a planned design that was not implemented. The actual production frontend uses Context API + Axios as documented here.