import { test, expect } from '@playwright/test';

test('user can login and access dashboard', async ({ page }) => {
  await page.goto('/login');
  await page.fill('input[name=\"email\"]', 'demo@ai-f.com');
  await page.fill('input[name=\"password\"]', 'demo123');
  await page.click('button:has-text(\"Login\")');
  await expect(page).toHaveURL(/dashboard/);
  await expect(page.locator('text=Welcome')).toBeVisible();
});

test('subscription flow', async ({ page }) => {
  await page.goto('/subscriptions');
  await page.click('button:has-text(\"Upgrade to Pro\")');
  await expect(page.locator('text=Stripe')).toBeVisible();
});

// More E2E tests to be added (25 total)

