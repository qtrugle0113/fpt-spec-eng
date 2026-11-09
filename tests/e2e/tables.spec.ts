import { test, expect } from '@playwright/test';
import { mkdir, readFile } from 'node:fs/promises';

test('Workbook upload above the proxy default size reaches the streaming API', async ({ request }) => {
  const buffer = await readFile('/tests/table-fixtures/boundary.xlsx');
  expect(buffer.length).toBeGreaterThan(1024 * 1024);
  const response = await request.post('/api/v1/definition-uploads', { multipart: { kind: 'TABLE', file: { name: 'boundary.xlsx', mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', buffer } } });
  expect(response.status()).toBe(201);
  expect((await response.json()).status).toBe('UPLOADED');
});

test('Table workbook creation and persistent history on real PostgreSQL and MySQL', async ({ page, request }, testInfo) => {
  for (const database of ['POSTGRESQL', 'MYSQL'] as const) {
    const code = database === 'MYSQL' ? 'mysql_etl' : 'pg_etl';
    const connections = await request.get('/api/v1/connections?search=' + code);
    expect(connections.ok()).toBe(true);
    const target = (await connections.json()).items.find((item: { code: string }) => item.code === code);
    expect(target).toBeTruthy();
    const tested = await request.post(`/api/v1/connections/${target.id}/test`);
    expect((await tested.json()).status).toBe('SUCCESS');
    await page.goto('/tables');
    await expect(page.getByRole('heading', { name: 'Table Management', exact: true })).toBeVisible();
    const download = page.waitForEvent('download');
    await page.getByRole('link', { name: 'Download Table Definition template' }).click();
    expect((await download).suggestedFilename()).toBe('Table Definition.xlsx');
    await page.getByLabel('Table Definition workbook', { exact: true }).setInputFiles(`/tests/table-fixtures/${database === 'MYSQL' ? 'mysql' : 'postgres'}.xlsx`);
    await page.getByLabel('Table Definition workbook', { exact: true }).focus();
    await page.keyboard.press('Tab');
    await expect(page.getByRole('button', { name: 'Upload workbook', exact: true })).toBeFocused();
    const uploadedResponse = page.waitForResponse(response => response.url().endsWith('/api/v1/definition-uploads') && response.request().method() === 'POST');
    await page.getByRole('button', { name: 'Upload workbook', exact: true }).click();
    const upload = await (await uploadedResponse).json();
    expect(upload.status).toBe('UPLOADED');
    await page.getByRole('combobox', { name: 'Target connection', exact: true }).selectOption(target.id);
    await page.getByRole('button', { name: 'Validate workbook', exact: true }).click();
    await expect(page.getByRole('heading', { name: 'Review tables', exact: true })).toBeVisible({ timeout: 35000 });
    await expect(page.getByText('Primary key: cust_id', { exact: true }).first()).toBeVisible();
    await page.getByRole('checkbox', { name: 'I reviewed the target tables and generated SQL.' }).check();
    const createdResponse = page.waitForResponse(response => response.url().endsWith('/api/v1/table-creation-jobs') && response.request().method() === 'POST');
    await page.getByRole('button', { name: 'Confirm and create tables', exact: true }).click();
    const operation = await (await createdResponse).json();
    await expect(page.getByText('Operation: SUCCEEDED', { exact: true })).toBeVisible({ timeout: 35000 });
    const operationState = await (await request.get(`/api/v1/operations/${operation.id}`)).json();
    const job = await (await request.get(operationState.result_links[0])).json();
    expect(job.results).toHaveLength(2);
    expect(job.results.every((result: { state: string }) => ['CREATED', 'ALREADY_EXISTS'].includes(result.state))).toBe(true);
    for (const result of job.results) {
      const actual = await (await request.get('/api/v1/table-definitions/' + result.table_id)).json();
      expect(actual.verification_status).toBe('VERIFIED');
      expect(actual.actual_columns).not.toBeNull();
      expect(actual.primary_key).toEqual(['cust_id']);
    }
    await page.reload();
    const row = page.getByRole('row').filter({ has: page.getByText(job.id, { exact: true }) });
    await row.getByRole('button', { name: 'View results', exact: true }).click();
    await expect(page.getByRole('region', { name: 'Job results' })).toBeVisible();
    await page.getByRole('button', { name: 'View table details', exact: true }).first().click();
    await expect(page.getByRole('heading', { name: 'Live database verification: VERIFIED', exact: true })).toBeVisible();
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await mkdir('/tmp/aat-e2e-artifacts', { recursive: true });
  await page.screenshot({ path: `/tmp/aat-e2e-artifacts/tables-${testInfo.project.name}.png`, fullPage: true });
});

test('Invalid workbook exposes safe locations without a creation preview', async ({ page, request }) => {
  const targets = await (await request.get('/api/v1/connections?search=mysql_etl')).json();
  const target = targets.items.find((item: { code: string }) => item.code === 'mysql_etl');
  await request.post(`/api/v1/connections/${target.id}/test`);
  await page.goto('/tables');
  await page.getByLabel('Table Definition workbook', { exact: true }).setInputFiles('/tests/table-fixtures/invalid.xlsx');
  await page.getByRole('button', { name: 'Upload workbook', exact: true }).click();
  await expect(page.getByText(/Selected upload:/)).toBeVisible();
  await page.getByRole('combobox', { name: 'Target connection', exact: true }).selectOption(target.id);
  await page.getByRole('button', { name: 'Validate workbook', exact: true }).click();
  await expect(page.getByRole('region', { name: 'Validation issues' })).toContainText('Instructions, row 1, column 2', { timeout: 35000 });
  await expect(page.getByRole('button', { name: 'Confirm and create tables', exact: true })).toHaveCount(0);
});
