# Frontend State Management Architecture

## Store Structure (Redux Toolkit + RTK Query)

AI-f uses **Redux Toolkit** for predictable state container with RTK Query for data fetching.

### Store Configuration

```javascript
// ui/react-app/src/store/index.js
import { configureStore } from '@reduxjs/toolkit';
import { setupListeners } from '@reduxjs/toolkit/query';
import authReducer from '../features/auth/authSlice';
import recognitionReducer from '../features/recognition/recognitionSlice';
import organizationsReducer from '../features/organizations/orgSlice';
import camerasReducer from '../features/cameras/cameraSlice';
import incidentsReducer from '../features/incidents/incidentSlice';
import { apiSlice } from '../services/apiSlice';

export const store = configureStore({
  reducer: {
    [apiSlice.reducerPath]: apiSlice.reducer,
    auth: authReducer,
    recognition: recognitionReducer,
    organizations: organizationsReducer,
    cameras: camerasReducer,
    incidents: incidentsReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: false, // RTK Query non-serializable values
    }).concat(apiSlice.middleware),
});

setupListeners(store.dispatch);

export const useAppDispatch = () => useDispatch();
export const useAppSelector = useSelector;
```

## Feature Slices

### 1. Authentication Slice

```javascript
// features/auth/authSlice.js
import { createSlice } from '@reduxjs/toolkit';
import { login, logout, refreshToken, verifyMFA } from '../../services/authApi';

const initialState = {
  user: null,
  token: localStorage.getItem('token'),
  isAuthenticated: false,
  isMFARequired: false,
  mfaEnrolled: false,
  loading: false,
  error: null,
  organizations: [],
  currentOrg: null,
};

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    setCredentials: (state, action) => {
      const { user, token, mfaRequired } = action.payload;
      state.user = user;
      state.token = token;
      state.isAuthenticated = true;
      state.isMFARequired = mfaRequired || false;
      localStorage.setItem('token', token);
    },
    clearCredentials: (state) => {
      state.user = null;
      state.token = null;
      state.isAuthenticated = false;
      state.isMFARequired = false;
      localStorage.removeItem('token');
    },
    setCurrentOrg: (state, action) => {
      state.currentOrg = action.payload;
    },
    setOrgs: (state, action) => {
      state.organizations = action.payload;
    },
  },
  extraReducers: (builder) => {
    builder
      .addMatcher(
        apiSlice.endpoints.login.matchPending,
        (state) => {
          state.loading = true;
          state.error = null;
        }
      )
      .addMatcher(
        apiSlice.endpoints.login.matchFulfilled,
        (state, action) => {
          state.loading = false;
          state.user = action.payload.user;
          state.token = action.payload.token;
          state.isAuthenticated = true;
          state.isMFARequired = action.payload.mfa_required || false;
        }
      )
      .addMatcher(
        apiSlice.endpoints.login.matchRejected,
        (state, action) => {
          state.loading = false;
          state.error = action.payload?.detail || 'Login failed';
        }
      );
  },
});

export const { setCredentials, clearCredentials, setCurrentOrg, setOrgs } = authSlice.actions;
export default authSlice.reducer;
```

### 2. Recognition Slice

```javascript
// features/recognition/recognitionSlice.js
import { createSlice } from '@reduxjs/toolkit';
import { initializeWebSocket } from '../../services/websocketService';

const initialState = {
  latestResults: [],
  streaming: false,
  currentCamera: null,
  selectedMode: 'single', // 'single' | 'multi' | 'video'
  processingLatency: 0,
  spoofDetected: false,
  emotionStats: {},
};

const recognitionSlice = createSlice({
  name: 'recognition',
  initialState,
  reducers: {
    setStreaming: (state, action) => {
      state.streaming = action.payload;
      if (action.payload) {
        initializeWebSocket();
      }
    },
    addRecognitionResult: (state, action) => {
      state.latestResults.unshift(action.payload);
      if (state.latestResults.length > 100) {
        state.latestResults.pop();
      }
    },
    clearResults: (state) => {
      state.latestResults = [];
    },
    setCurrentCamera: (state, action) => {
      state.currentCamera = action.payload;
    },
    setSpoofDetected: (state, action) => {
      state.spoofDetected = action.payload;
    },
  },
});

export const { setStreaming, addRecognitionResult, clearResults, setCurrentCamera, setSpoofDetected } = recognitionSlice.actions;
export default recognitionSlice.reducer;
```

### 3. Organizations Slice

```javascript
// features/organizations/orgSlice.js
import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  list: [],
  current: null,
  members: [],
  loading: false,
};

const orgSlice = createSlice({
  name: 'organizations',
  initialState,
  reducers: {
    setCurrentOrg: (state, action) => {
      state.current = action.payload;
    },
    setOrgs: (state, action) => {
      state.list = action.payload;
    },
  },
});

export const { setCurrentOrg, setOrgs } = orgSlice.actions;
export default orgSlice.reducer;
```

## RTK Query API Layer

```javascript
// services/apiSlice.js
import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';

export const apiSlice = createApi({
  reducerPath: 'api',
  baseQuery: fetchBaseQuery({
    baseUrl: process.env.REACT_APP_API_URL || '/api',
    prepareHeaders: (headers, { getState }) => {
      const token = getState().auth.token;
      if (token) {
        headers.set('Authorization', `Bearer ${token}`);
      }
      return headers;
    },
  }),
  tagTypes: [
    'Person',
    'Organization',
    'Camera',
    'Recognition',
    'Incident',
    'Model',
  ],
  endpoints: (builder) => ({
    // Auth
    login: builder.mutation({
      query: (credentials) => ({
        url: '/auth/login',
        method: 'POST',
        body: credentials,
      }),
      invalidatesTags: ['Auth'],
    }),
    logout: builder.mutation({
      query: () => ({
        url: '/auth/logout',
        method: 'POST',
      }),
      invalidatesTags: ['Auth'],
    }),
    
    // Persons (Identity)
    getPersons: builder.query({
      query: (params = {}) => ({
        url: '/persons',
        params,
      }),
      providesTags: ['Person'],
    }),
    enrollPerson: builder.mutation({
      query: (formData) => ({
        url: '/enroll',
        method: 'POST',
        body: formData,
      }),
      invalidatesTags: ['Person'],
    }),
    deletePerson: builder.mutation({
      query: (personId) => ({
        url: `/persons/${personId}`,
        method: 'DELETE',
      }),
      invalidatesTags: ['Person'],
    }),
    
    // Organizations
    getOrganizations: builder.query({
      query: () => '/organizations',
      providesTags: ['Organization'],
    }),
    
    // Cameras
    getCameras: builder.query({
      query: (orgId) => ({
        url: `/orgs/${orgId}/cameras`,
      }),
    }),
    
    // Recognition Events
    getRecognitionEvents: builder.query({
      query: (params) => ({
        url: '/orgs/events',
        params,
      }),
      keepUnusedDataFor: 30, // seconds
    }),
  }),
});

export const {
  useLoginMutation,
  useLogoutMutation,
  useGetPersonsQuery,
  useEnrollPersonMutation,
  useDeletePersonMutation,
  useGetOrganizationsQuery,
  useGetCamerasQuery,
  useGetRecognitionEventsQuery,
} = apiSlice;
```

## Selector Hooks

```javascript
// features/auth/selectors.js
import { createSelector } from '@reduxjs/toolkit';

const selectAuthState = (state) => state.auth;

export const selectCurrentUser = createSelector(
  [selectAuthState],
  (auth) => auth.user
);

export const selectIsAuthenticated = createSelector(
  [selectAuthState],
  (auth) => auth.isAuthenticated
);

export const selectIsMFARequired = createSelector(
  [selectAuthState],
  (auth) => auth.isMFARequired
);
```

## Persistence with Redux Persist

```javascript
// store/persistConfig.js
import { persistStore, persistReducer } from 'redux-persist';
import storage from 'redux-persist/lib/storage';
import { combineReducers } from '@reduxjs/toolkit';
import authReducer from '../features/auth/authSlice';
import orgReducer from '../features/organizations/orgSlice';

const rootReducer = combineReducers({
  auth: authReducer,
  organizations: orgReducer,
});

const persistConfig = {
  key: 'root',
  storage,
  whitelist: ['auth', 'organizations'], // Only persist these reducers
};

const persistedReducer = persistReducer(persistConfig, rootReducer);

export const persistor = persistStore(persistedReducer);
export { persistedReducer as rootReducer };
```

## Component Usage Example

```jsx
// pages/Dashboard.jsx
import { useGetPersonsQuery } from '../services/apiSlice';
import { useRecognitionStream } from '../hooks/useRecognitionStream';
import { useAppDispatch, useAppSelector } from '../store';

export default function Dashboard() {
  const dispatch = useAppDispatch();
  const { user, organizations } = useAppSelector(selectCurrentUser);
  const { data: persons, isLoading } = useGetPersonsQuery({
    org_id: user?.org_id,
    limit: 50,
    page: 1,
  });
  
  // WebSocket stream hook
  const { latestResults, setStreaming } = useRecognitionStream({
    cameraId: 'cam_lobby',
  });
  
  return (
    <div>
      <h1>Dashboard</h1>
      <PersonList persons={persons?.data?.items || []} loading={isLoading} />
      <LiveRecognitionFeed results={latestResults} />
    </div>
  );
}
```

## Environment Variables

```bash
# ui/react-app/.env
REACT_APP_API_URL=http://localhost:8000/api
REACT_APP_WS_URL=ws://localhost:8000/ws
REACT_APP_ENV=development
REACT_APP_SENTRY_DSN=
REACT_APP_GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
REACT_APP_AZURE_TENANT_ID=xxx
```

---

**Files:**
- Store: `ui/react-app/src/store/index.js`
- Auth Slice: `ui/react-app/src/features/auth/authSlice.js`
- API Slice: `ui/react-app/src/services/apiSlice.js`
- Selectors: `ui/react-app/src/features/auth/selectors.js`
