import { test, expect } from '@playwright/test';

test('Six pages preserve landmarks, visible main actions and narrow layouts', async ({ page }) => {
  for (const [route, heading] of [['/', 'Dashboard'], ['/connections', 'Connections'], ['/tables', 'Table Management'], ['/dag-builder', 'DAG Builder'], ['/monitoring', 'DAG Monitoring'], ['/settings', 'Settings']]) {
    await page.goto(route);
    await expect(page.getByRole('main')).toBeVisible();
    await expect(page.getByRole('heading', { name: heading, exact: true })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.getByRole('link', { name: 'Skip to content' }).focus();
    await expect(page.getByRole('link', { name: 'Skip to content' })).toBeVisible();
    await page.keyboard.press('Enter');
    await expect(page.getByRole('main')).toBeFocused();
  }
  await page.screenshot({ path: '/tmp/aat-e2e-artifacts/settings-accessibility.png', fullPage: true });
});
