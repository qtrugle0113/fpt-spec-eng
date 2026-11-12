import { test, expect } from '@playwright/test';

test('Public navigation and page headings use English on every workspace route', async ({ page, request }) => {
  for (const [route, title] of [['/', 'Dashboard'], ['/connections', 'Connections'],
    ['/tables', 'Table Management'], ['/dag-builder', 'DAG Builder'],
    ['/monitoring', 'DAG Monitoring'], ['/settings', 'Settings']]) {
    await page.goto(route);
    await expect(page.locator('html')).toHaveAttribute('lang', 'en');
    await expect(page.getByRole('heading', { name: title, exact: true, level: 1 })).toBeVisible();
    await expect(page.locator('nav[aria-label="Main navigation"]')).toContainText('Connections');
    expect(await page.locator('body').innerText()).not.toContain('Traceback');
  }
  const missing = await request.get('/api/v1/connections/00000000-0000-4000-8000-000000000001');
  expect(missing.status()).toBe(404);
  const error = (await missing.json()).error;
  expect(error.message).toMatch(/[A-Za-z]/);
  expect(error.message).not.toMatch(/[\u00c0-\u024f\u1e00-\u1eff]/);
  expect(error.message).not.toContain('postgresql://');
});
