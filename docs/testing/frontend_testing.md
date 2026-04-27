# Frontend Testing Configuration
# Jest + React Testing Library setup

## Configuration Files

### package.json (test scripts)
```json
{
  "scripts": {
    "test": "jest --watch",
    "test:coverage": "jest --coverage --coverageReporters=text-lcov > coverage.lcov && codecov",
    "test:ci": "jest --ci --coverage --maxWorkers=2",
    "test:e2e": "playwright test"
  },
  "jest": {
    "preset": "ts-jest",
    "testEnvironment": "jsdom",
    "setupFilesAfterEnv": ["<rootDir>/src/setupTests.js"],
    "moduleNameMapper": {
      "^@/(.*)$": "<rootDir>/src/$1"
    },
    "collectCoverageFrom": [
      "src/**/*.{js,jsx,ts,tsx}",
      "!src/**/*.d.ts",
      "!src/index.js",
      "!src/reportWebVitals.js"
    ],
    "coverageThreshold": {
      "global": {
        "branches": 80,
        "functions": 85,
        "lines": 85,
        "statements": 85
      }
    }
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.4.0",
    "@testing-library/react": "^14.2.0",
    "@testing-library/user-event": "^14.5.0",
    "jest": "^29.0.0",
    "jest-environment-jsdom": "^29.0.0",
    "ts-jest": "^29.0.0"
  }
}
```

### src/setupTests.js
```javascript
import '@testing-library/jest-dom';

// Mock WebSocket
global.WebSocket = class MockWebSocket {
  constructor(url) {
    this.url = url;
    this.readyState = 0;
  }
  send(data) {}
  close() {}
  addEventListener(event, handler) {}
  removeEventListener(event, handler) {}
};

// Mock ResizeObserver
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  observe() { return null; }
  unobserve() {}
  disconnect() {}
};
```

## Test Structure

```
ui/react-app/
├── src/
│   ├── __tests__/
│   │   ├── components/
│   │   │   ├── RecognitionCard.test.jsx
│   │   │   ├── CameraStream.test.jsx
│   │   │   ├── EnrollForm.test.jsx
│   │   │   └── AuditTimeline.test.jsx
│   │   ├── pages/
│   │   │   ├── Dashboard.test.jsx
│   │   │   ├── AdminPanel.test.jsx
│   │   │   ├── PersonProfile.test.jsx
│   │   │   └── Enroll.test.jsx
│   │   ├── services/
│   │   │   └── api.test.js
│   │   └── store/
│   │       └── auth.test.js
│   └── setupTests.js
├── playwright.config.ts
└── tests/
    ├── e2e/
    │   ├── login.spec.ts
    │   ├── enrollment-flow.spec.ts
    │   ├── recognition.spec.ts
    │   └── admin-dashboard.spec.ts
    └── fixtures/
        └── users.ts
```

## Example Component Test

```javascript
// src/__tests__/components/RecognitionCard.test.jsx
import { render, screen, waitFor } from '@testing-library/react';
import RecognitionCard from '../components/RecognitionCard';
import * as api from '../services/api';

jest.mock('../services/api');

describe('RecognitionCard', () => {
  test('displays recognition result', async () => {
    const mockResult = {
      person_id: 'pers_123',
      name: 'John Doe',
      score: 0.95,
      confidence: 0.96
    };
    
    api.getRecognitionResult.mockResolvedValue(mockResult);
    
    render(<RecognitionCard resultId="rec_123" />);
    
    await waitFor(() => {
      expect(screen.getByText('John Doe')).toBeInTheDocument();
      expect(screen.getByText('95%')).toBeInTheDocument();
    });
  });

  test('shows loading state', () => {
    api.getRecognitionResult.mockImplementation(() => new Promise(() => {}));
    render(<RecognitionCard resultId="rec_123" />);
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
  });

  test('handles error state', async () => {
    api.getRecognitionResult.mockRejectedValue(new Error('Network error'));
    render(<RecognitionCard resultId="rec_123" />);
    
    await waitFor(() => {
      expect(screen.getByText('Failed to load')).toBeInTheDocument();
    });
  });
});
```

## E2E Testing with Playwright

```typescript
// tests/e2e/login.spec.ts
import { test, expect } from '@playwright/test';

test('admin can login via SSO', async ({ page }) => {
  await page.goto('/login');
  
  // Click SSO button
  await page.click('text=Sign in with Azure AD');
  
  // Wait for redirect and verify
  await page.waitForURL('**/dashboard');
  await expect(page.locator('text=Welcome, Admin')).toBeVisible();
});

test('user can enroll new identity', async ({ page }) => {
  await page.goto('/enroll');
  
  // Fill form
  await page.fill('[name="name"]', 'Test User');
  await page.setInputFiles('input[type="file"]', 'fixtures/face.jpg');
  
  // Submit
  await page.click('button[type="submit"]');
  
  // Wait for success message
  await expect(page.locator('text=Enrollment successful')).toBeVisible();
});
```

## Coverage Report

When running `npm test -- --coverage`, generates:

```
-------------------|----------|----------|----------|----------|-------------------
File               |  % Stmts | % Branch |  % Funcs |  % Lines | Uncovered Line #s 
-------------------|----------|----------|----------|----------|-------------------
All files          |    87.3% |    78.2% |    90.1% |    88.4% |                   
 App.js            |     100% |     100% |     100% |     100% |                   
 api.js            |    92.3% |    85.7% |    95.2% |    92.8% | 45,67,89           
 components/       |    85.1% |    72.4% |    88.9% |    86.2% |                   
  Card.jsx         |    88.9% |    75.0% |    91.7% |    89.2% | 123,156            
  Form.jsx         |    81.2% |    69.8% |    85.7% |    82.5% | 78,92,145          
-------------------|----------|----------|----------|----------|-------------------
```

**Target:** 85%+ line coverage, 80%+ branch coverage across all application code.
