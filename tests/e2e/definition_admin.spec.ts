import { test, expect } from '@playwright/test';
import { mkdir } from 'node:fs/promises';

test('Definition names remain consistent on the real UI and ETL validation', async ({ page, request }, info) => {
  await mkdir('/tmp/aat-e2e-artifacts', { recursive: true });
  for (const [route, name] of [['/tables', 'Table Definition'], ['/dag-builder', 'ETL Definition']]) {
    await page.goto(route);
    await expect(page.getByLabel(`${name} file (.xlsx)`, { exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: `Upload ${name}`, exact: true })).toBeVisible();
    expect(await page.locator('main').innerText()).not.toMatch(/\bworkbooks?\b/i);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: `/tmp/aat-e2e-artifacts/${info.project.name}-${name.replaceAll(' ', '-')}.png`, fullPage: true });
  }
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('link', { name: 'Download ETL Definition template', exact: true }).click();
  const download = await downloadPromise;
  const filename = `/tmp/aat-etl-${info.project.name}.xlsx`; await download.saveAs(filename);
  await page.getByLabel('ETL Definition file (.xlsx)', { exact: true }).setInputFiles(filename);
  const uploaded = page.waitForResponse(response => response.url().endsWith('/api/v1/definition-uploads') && response.request().method() === 'POST');
  await page.getByRole('button', { name: 'Upload ETL Definition', exact: true }).click();
  const upload = await (await uploaded).json();
  await page.getByRole('button', { name: 'Validate ETL Definition', exact: true }).click();
  await expect.poll(async () => (await (await request.get(`/api/v1/definition-uploads/${upload.id}`)).json()).status, { timeout: 60000 }).toMatch(/^(VALIDATED|INVALID)$/);
  expect(await page.locator('main').innerText()).not.toMatch(/\bworkbooks?\b/i);
});

test('admin signs into real Airflow with administrator permissions and authentication stays enabled', async ({ browser, request }, info) => {
  const base = process.env.AAT_ADMIN_AIRFLOW_URL ?? 'http://airflow-apiserver:8080';
  const bad = await request.post(base + '/auth/token', { data: { username: 'admin', password: 'invalid-test-password' } });
  expect(bad.status()).toBe(401);
  const unauthenticated = await request.get(base + '/api/v2/variables?limit=1');
  expect([401, 403]).toContain(unauthenticated.status());
  const apiLogin = await request.post(base + '/auth/token', { data: { username: 'admin', password: 'admin' } });
  expect(apiLogin.ok()).toBe(true);
  const token = (await apiLogin.json()).access_token;
  const claims = JSON.parse(Buffer.from(token.split('.')[1], 'base64url').toString());
  expect(claims.sub).toBe('admin'); expect(claims.role).toBe('admin');
  const config = await request.get(base + '/api/v2/variables?limit=1', { headers: { Authorization: `Bearer ${token}` } });
  expect(config.ok()).toBe(true);
  const context = await browser.newContext({ viewport: info.project.use.viewport ?? { width: 1366, height: 768 } });
  try {
    const page = await context.newPage(); await page.goto(base);
    await page.getByRole('textbox', { name: 'Username', exact: true }).fill('admin');
    await page.getByLabel('Password', { exact: true }).fill('admin');
    const authenticated = page.waitForResponse(response => response.url().includes('/auth/token') && response.request().method() === 'POST');
    await page.getByRole('button', { name: 'Sign in', exact: true }).click();
    const response = await authenticated; expect(response.ok()).toBe(true);
    await page.waitForURL(url => !url.pathname.startsWith('/auth/login'));
    await expect(page.getByRole('button', { name: 'Sign in', exact: true })).toHaveCount(0);
    await mkdir('/tmp/aat-e2e-artifacts', { recursive: true });
    await page.screenshot({ path: `/tmp/aat-e2e-artifacts/${info.project.name}-airflow-admin.png`, fullPage: true });
  } finally { await context.close(); }
});
