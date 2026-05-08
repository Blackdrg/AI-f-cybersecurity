import { test, expect } from '@playwright/test';

test.describe('Enrollment Flow', () => {
  test('should navigate to enrollment page and submit form', async ({ page }) => {
    // Go to the enrollment page (assuming baseURL configured)
    await page.goto('/enroll');

    // Check page title
    await expect(page).toHaveTitle(/Enroll/i);

    // Fill out the form
    await page.fill('input[name="name"]', 'John Doe');
    // Depending on form fields, fill others
    // Submit
    await page.click('button[type="submit"]');

    // Expect success message or redirect
    await expect(page.locator('text=Enrollment successful')).toBeVisible({ timeout: 10000 });
  });
});
