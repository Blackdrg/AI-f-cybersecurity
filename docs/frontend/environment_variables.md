# Frontend Environment Configuration

## Overview

AI-f React app uses environment variables for configuration. All variables must be prefixed with `REACT_APP_` to be embedded at build time.

## Development `.env.development`

```bash
# API Configuration
REACT_APP_API_URL=http://localhost:8000/api
REACT_APP_WS_URL=ws://localhost:8000/ws
REACT_APP_API_VERSION=v1

# Authentication
REACT_APP_AUTH_MODE=jwt  # 'jwt' | 'oauth'
REACT_APP_OAUTH_AZURE_TENANT_ID=xxx
REACT_APP_OAUTH_AZURE_CLIENT_ID=xxx
REACT_APP_OAUTH_GOOGLE_CLIENT_ID=xxx

# Feature Flags
REACT_APP_ENABLE_MFA=true
REACT_APP_ENABLE_OAUTH=true
REACT_APP_ENABLE_BILLING=true
REACT_APP_ENABLE_FEDERATED_LEARNING=false  # Dev only

# UI Configuration
REACT_APP_APP_NAME="AI-f Identity Platform"
REACT_APP_COMPANY_NAME="AI-f Security"
REACT_APP_SUPPORT_EMAIL=support@ai-f.security
REACT_APP_DEFAULT_THEME=light

# Third-party Integrations
REACT_APP_SENTRY_DSN=
REACT_APP_GOOGLE_ANALYTICS_ID=
REACT_APP_STRIPE_PUBLIC_KEY=pk_test_xxx

# Development
REACT_APP_DEBUG=true
REACT_APP_MOCK_ML=true  # Use mock ML models in dev
REACT_APP_ENABLE_WELCOME_TOUR=true
```

## Production `.env.production`

```bash
# API
REACT_APP_API_URL=https://api.example.com/api
REACT_APP_WS_URL=wss://api.example.com/ws
REACT_APP_API_VERSION=v1

# Auth
REACT_APP_AUTH_MODE=jwt
REACT_APP_OAUTH_AZURE_TENANT_ID=${AZURE_TENANT_ID}
REACT_APP_OAUTH_AZURE_CLIENT_ID=${AZURE_CLIENT_ID}
REACT_APP_OAUTH_GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}

# Features
REACT_APP_ENABLE_MFA=true
REACT_APP_ENABLE_OAUTH=true
REACT_APP_ENABLE_BILLING=true
REACT_APP_ENABLE_FEDERATED_LEARNING=true

# UI
REACT_APP_APP_NAME="AI-f"
REACT_APP_COMPANY_NAME="AI-f Security Inc."
REACT_APP_SUPPORT_EMAIL=support@ai-f.security
REACT_APP_DEFAULT_THEME=light

# Third-party
REACT_APP_SENTRY_DSN=${SENTRY_DSN}
REACT_APP_GOOGLE_ANALYTICS_ID=${GA_ID}
REACT_APP_STRIPE_PUBLIC_KEY=${STRIPE_PK}

# Production
REACT_APP_DEBUG=false
REACT_APP_MOCK_ML=false
REACT_APP_ENABLE_WELCOME_TOUR=false
```

## Build-Time Configuration

**Important:** Environment variables are embedded at **build time**, not runtime. For dynamic configuration in production, use an endpoint or config file fetched at startup.

### Alternative: Runtime Configuration

For Kubernetes deployments where config may change per environment without rebuilding:

```javascript
// src/config/runtimeConfig.js
export async function loadRuntimeConfig() {
  const response = await fetch('/config/config.json');
  const config = await response.json();
  return config;
}

// Usage in app
const config = await loadRuntimeConfig();
console.log('API URL:', config.apiUrl);
```

Deploy a ConfigMap with `config.json` that the app fetches on startup.

## Usage in Code

```javascript
// Accessing env vars
const apiUrl = process.env.REACT_APP_API_URL;
const wsUrl = process.env.REACT_APP_WS_URL;
const isDebug = process.env.REACT_APP_DEBUG === 'true';

// Feature flags
const ENABLE_MFA = process.env.REACT_APP_ENABLE_MFA === 'true';
const ENABLE_BILLING = process.env.REACT_APP_ENABLE_BILLING === 'true';

// Helper hook
export function useConfig() {
  return {
    apiUrl: process.env.REACT_APP_API_URL,
    wsUrl: process.env.REACT_APP_WS_URL,
    isProduction: process.env.NODE_ENV === 'production',
    features: {
      mfa: process.env.REACT_APP_ENABLE_MFA === 'true',
      billing: process.env.REACT_APP_ENABLE_BILLING === 'true',
      federatedLearning: process.env.REACT_APP_ENABLE_FEDERATED_LEARNING === 'true',
    },
  };
}
```

## Validation (TypeScript)

```typescript
// src/types/config.ts
interface AppConfig {
  REACT_APP_API_URL: string;
  REACT_APP_WS_URL: string;
  REACT_APP_ENABLE_MFA: boolean;
  REACT_APP_ENABLE_BILLING: boolean;
}

declare global {
  namespace NodeJS {
    interface ProcessEnv extends AppConfig {}
  }
}
```

## Security Notes

- Never store secrets (API keys, tokens) in frontend env vars - they are public.
- Use backend-proxied calls for any sensitive operations.
- `REACT_APP_` prefix is mandatory; variables without it are stripped by Create React App.
- `.env` files should be in `.gitignore` and only `.env.example` committed.
