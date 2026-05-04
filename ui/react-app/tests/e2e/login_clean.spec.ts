import { test, expect, Page } from '@playwright/test';

test('user login and dashboard', async ({ page }: { page: Page }) => {
  await page.goto('/login');
  await page.fill('input[name=\\"email\\"]', 'demo@ai-f.com');
  await page.fill('input[name=\\"password\\"]', 'demo123');
  await page.click('button:has-text(\\"Login\\")');
  await expect(page).toHaveURL(/dashboard/);
  await expect(page.locator('text=Welcome')).toBeVisible();
});

test('subscription upgrade', async ({ page }: { page: Page }) => {
  await page.goto('/subscriptions');
  await page.click('button:has-text(\\"Upgrade to Pro\\")');
  await expect(page.locator('text=Stripe')).toBeVisible();
});

