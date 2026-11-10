import { test, expect } from '@playwright/test';

test('Airflow outage is visible instead of an empty successful dashboard', async ({ page, request }) => {
  const response = await request.get('/api/v1/dashboard?scope=EXTERNAL&force_refresh=true', { timeout: 45000 });
  expect(response.ok()).toBe(true);
  const data = await response.json();
  expect(data.completeness).toBe('UNAVAILABLE');
  expect(data.inventory.total).toBeNull();
  expect(data.run_metrics.total).toBeNull();
  await page.goto('/');
  await page.getByLabel('Ownership scope').selectOption('EXTERNAL');
  await expect(page.getByRole('status').filter({ hasText: 'Not available' })).toBeVisible({ timeout: 45000 });
  const card = page.getByRole('article').filter({ has: page.getByRole('heading', { name: 'Total DAGs', exact: true }) });
  await expect(card.locator('strong')).toHaveText('Not available');
});
