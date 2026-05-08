import { test, expect } from '@playwright/test';

test.describe('Recognition Flow', () => {
  test('should upload image and get match', async ({ page }) => {
    await page.goto('/recognize');

    // Upload image file
    const input = page.locator('input[type="file"]');
    await input.setInputFiles('tests/fixtures/sample_face.jpg');

    // Submit
    await page.click('button[type="submit"]');

    // Wait for results
    const resultLocator = page.locator('.match-result');
    await expect(resultLocator).toBeVisible({ timeout: 15000 });
    await expect(resultLocator).toContainText('Match found');
  });
});
