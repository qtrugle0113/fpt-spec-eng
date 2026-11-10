import { test, expect } from '@playwright/test';

test('Settings persist real changes and require a new review after a stale revision', async ({ page, request }, info) => {
  await page.goto('/settings');
  const batch = page.getByLabel('Default Batch Size (rows)');
  await expect(batch).toBeVisible();
  await batch.fill(info.project.name === 'desktop' ? '2048' : '3072');
  await page.getByRole('button', { name: 'Save settings' }).click();
  await expect(page.getByRole('status')).toContainText('Settings saved.');
  await page.reload();
  await expect(batch).toHaveValue(info.project.name === 'desktop' ? '2048' : '3072');
  const current = await request.get('/api/v1/settings');
  const changed = await request.patch('/api/v1/settings', { headers: { 'If-Match': current.headers()['etag'] }, data: { default_batch_size: 4096 } });
  expect(changed.ok()).toBe(true);
  await batch.fill('5000');
  await page.getByRole('button', { name: 'Save settings' }).click();
  await expect(page.getByRole('alert')).toContainText('Settings changed in another session');
  await expect(page.getByRole('button', { name: 'Save settings' })).toBeDisabled();
  await page.getByRole('button', { name: 'Reload settings' }).click();
  await expect(batch).toHaveValue('4096');
  await page.getByLabel('Default Timezone', { exact: true }).fill('Invalid/Timezone');
  await page.getByRole('button', { name: 'Save settings' }).click();
  await expect(page.getByRole('alert')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Application information', exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
