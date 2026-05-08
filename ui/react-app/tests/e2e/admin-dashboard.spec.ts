import { test, expect } from '@playwright/test';

test.describe('Admin Dashboard', () => {
  test('should display analytics and bias reports', async ({ page }) => {
    // Login as admin (assuming auth)
    await page.goto('/login');
    await page.fill('input[name="email"]', 'admin@example.com');
    await page.fill('input[name="password"]', 'password123');
    await page.click('button[type="submit"]');

    await page.goto('/admin');

    // Check sections
    await expect(page.locator('h2')).toContainText('Admin Dashboard');
    await expect(page.locator('.bias-report')).toBeVisible();
    await expect(page.locator('.active-alerts')).toBeVisible();
  });
});
