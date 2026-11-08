import { test, expect } from '@playwright/test';

test('bootstrap shell routes remain usable', async ({ page }) => {
  for (const route of ['/', '/connections', '/tables', '/dag-builder', '/monitoring', '/settings']) {
    await page.goto(route);
    await expect(page.locator('#root')).not.toBeEmpty();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  }
});

test('private runtime prefixes are blocked by nginx', async ({ request }) => {
  for (const path of ['/internal/runtime/bind', '/api/v1/internal/runtime/bind']) {
    for (const method of ['GET', 'POST']) {
      const response = await request.fetch(path, { method });
      expect(response.status()).toBe(404);
      expect(await response.text()).not.toContain('<div id="root">');
    }
  }
});
