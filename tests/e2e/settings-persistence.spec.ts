import { test, expect } from '@playwright/test';

test('Settings survive backend container recreation', async ({ page, request }) => {
  const result = await request.get('/api/v1/settings');
  expect(result.ok()).toBe(true);
  expect((await result.json()).default_batch_size).toBe(4096);
  await page.goto('/settings');
  await expect(page.getByLabel('Default Batch Size (rows)')).toHaveValue('4096');
});
