# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: login.spec.ts >> user can login and access dashboard
- Location: tests\e2e\login.spec.ts:3:5

# Error details

```
Error: page.goto: net::ERR_CONNECTION_REFUSED at http://localhost:3000/login
Call log:
  - navigating to "http://localhost:3000/login", waiting until "load"

```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test';
  2  | 
  3  | test('user can login and access dashboard', async ({ page }) => {
> 4  |   await page.goto('/login');
     |              ^ Error: page.goto: net::ERR_CONNECTION_REFUSED at http://localhost:3000/login
  5  |   await page.fill('input[name=\"email\"]', 'demo@ai-f.com');
  6  |   await page.fill('input[name=\"password\"]', 'demo123');
  7  |   await page.click('button:has-text(\"Login\")');
  8  |   await expect(page).toHaveURL(/dashboard/);
  9  |   await expect(page.locator('text=Welcome')).toBeVisible();
  10 | });
  11 | 
  12 | test('subscription flow', async ({ page }) => {
  13 |   await page.goto('/subscriptions');
  14 |   await page.click('button:has-text(\"Upgrade to Pro\")');
  15 |   await expect(page.locator('text=Stripe')).toBeVisible();
  16 | });
  17 | 
  18 | // More E2E tests to be added (25 total)
  19 | 
  20 | 
```