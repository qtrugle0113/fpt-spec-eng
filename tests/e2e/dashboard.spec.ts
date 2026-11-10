import { test, expect } from '@playwright/test';

test('Dashboard renders actual aggregates, lifetime scope and explicit refresh', async ({ page, request }) => {
  const response = await request.get('/api/v1/dashboard?force_refresh=true');
  expect(response.ok()).toBe(true);
  const actual = await response.json();
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Dashboard', exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Lifetime history' })).toBeVisible();
  const card = page.getByRole('article').filter({ has: page.getByRole('heading', { name: 'Total DAGs', exact: true }) });
  await expect(card.locator('strong')).toHaveText(actual.inventory.total == null ? 'Not available' : actual.inventory.total.toLocaleString());
  await page.getByRole('button', { name: 'Refresh dashboard' }).click();
  await expect(page.getByRole('button', { name: 'Refresh dashboard' })).toBeEnabled();
  await page.getByLabel('From date').fill('2001-01-01');
  await page.getByLabel('To date').fill('2001-01-01');
  await page.getByLabel('Timezone', { exact: true }).fill('Asia/Seoul');
  await expect(page.getByText('No runs in this period.')).toBeVisible();
  await page.getByLabel('Auto Refresh', { exact: true }).check();
  await expect(page.getByLabel('Auto Refresh', { exact: true })).toBeChecked();
  await expect(page.getByRole('heading', { name: 'Next scheduled runs' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

