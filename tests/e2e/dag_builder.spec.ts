import { test, expect } from '@playwright/test';
import { mkdir, readFile } from 'node:fs/promises';
import type { Page } from '@playwright/test';
test.use({ actionTimeout: 15000 });

async function reviewWorkbook(page: Page, fixture: string) {
  await page.goto('/dag-builder');
  await page.getByLabel('ETL Definition workbook', { exact: true }).setInputFiles(`/tests/dag-fixtures/${fixture}.xlsx`);
  await page.getByRole('button', { name: 'Upload ETL workbook', exact: true }).click();
  await page.getByRole('button', { name: 'Validate ETL workbook', exact: true }).click();
  await expect.poll(async () => {
    if (await page.getByRole('button', { name: 'Review schedules and load policies' }).count()) return true;
    if (await page.getByText('TARGET_BUSY', { exact: true }).count()) {
      const retry = page.getByRole('button', { name: 'Validate ETL workbook', exact: true });
      if (await retry.isEnabled()) await retry.click();
    }
    return false;
  }, { timeout: 60000, intervals: [1000, 2000] }).toBe(true);
  await page.getByRole('button', { name: 'Review schedules and load policies' }).click();
}

async function deployReviewed(page: Page, dag: string) {
  const support = page.getByRole('checkbox', { name: 'I reviewed and authorize creating the displayed support objects in the target database.' });
  if (await support.count()) await support.check();
  await page.getByRole('checkbox', { name: 'I reviewed every selected source, target, mapping, schedule and load policy. Deploy these exact revisions.' }).check();
  await page.getByRole('button', { name: 'Confirm and deploy workflows', exact: true }).click();
  const result = page.getByRole('article', { name: 'Deployment result for ' + dag });
  await expect(result.getByText('DEPLOYED', { exact: true })).toBeVisible({ timeout: 150000 });
  return result;
}

test('ETL wizard validates, deploys and submits a real Airflow run', async ({ page, request }, testInfo) => {
  test.setTimeout(240000);
  const connectionPage = await request.get('/api/v1/connections?search=pg_etl');
  expect(connectionPage.ok()).toBe(true);
  const connection = (await connectionPage.json()).items.find((item: { code: string }) => item.code === 'pg_etl');
  expect(connection).toBeTruthy();
  expect((await (await request.post(`/api/v1/connections/${connection.id}/test`)).json()).status).toBe('SUCCESS');
  await page.goto('/dag-builder');
  const download = page.waitForEvent('download');
  await page.getByRole('link', { name: 'Download ETL Definition template' }).click();
  expect((await download).suggestedFilename()).toBe('ETL Definition.xlsx');
  const fixture = 'append-' + testInfo.project.name;
  const fixtures = JSON.parse(await readFile('/tests/dag-fixtures/index.json', 'utf8'));
  await page.getByLabel('ETL Definition workbook', { exact: true }).setInputFiles(`/tests/dag-fixtures/${fixture}.xlsx`);
  await page.getByRole('button', { name: 'Upload ETL workbook', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Validate ETL workbook', exact: true })).toBeEnabled();
  await page.getByRole('button', { name: 'Validate ETL workbook', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Review schedules and load policies' })).toBeVisible({ timeout: 45000 });
  await page.getByRole('button', { name: 'Review schedules and load policies' }).click();
  const support = page.getByRole('checkbox', { name: 'I reviewed and authorize creating the displayed support objects in the target database.' });
  if (await support.count()) await support.check();
  await page.getByRole('checkbox', { name: 'I reviewed every selected source, target, mapping, schedule and load policy. Deploy these exact revisions.' }).check();
  await page.getByRole('button', { name: 'Confirm and deploy workflows', exact: true }).click();
  const result = page.getByRole('article', { name: 'Deployment result for ' + fixtures[fixture] });
  await expect(result.getByText('DEPLOYED', { exact: true })).toBeVisible({ timeout: 150000 });
  await expect(result.getByRole('link', { name: 'Open Airflow', exact: true })).toHaveAttribute('href', new RegExp('/dags/' + fixtures[fixture] + '$'));
  await result.getByRole('checkbox', { name: /I confirm the schedule state change/ }).check();
  await result.getByRole('button', { name: 'Enable manual execution', exact: true }).click();
  await expect(page.getByText(/State command succeeded/)).toBeVisible({ timeout: 30000 });
  await result.getByRole('checkbox', { name: /I confirm a new manual run/ }).check();
  const triggered = page.waitForResponse(response => response.url().endsWith('/trigger') && response.request().method() === 'POST');
  await result.getByRole('button', { name: 'Run workflow now', exact: true }).click();
  const command = await (await triggered).json();
  expect(command.id).toBeTruthy();
  await expect(page.getByText(/Manual trigger succeeded/)).toBeVisible({ timeout: 30000 });
  await mkdir('/tmp/aat-e2e-artifacts', { recursive: true });
  await page.screenshot({ path: `/tmp/aat-e2e-artifacts/dag-builder-${testInfo.project.name}.png`, fullPage: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test('Replacement authority persists across a fresh browser and revokes explicitly', async ({ page, browser }, testInfo) => {
  test.setTimeout(120000);
  const fixture = 'refresh-' + testInfo.project.name;
  const fixtures = JSON.parse(await readFile('/tests/dag-fixtures/index.json', 'utf8'));
  await page.goto('/dag-builder');
  await page.getByLabel('ETL Definition workbook', { exact: true }).setInputFiles(`/tests/dag-fixtures/${fixture}.xlsx`);
  const uploaded = page.waitForResponse(response => response.url().endsWith('/definition-uploads') && response.request().method() === 'POST');
  await page.getByRole('button', { name: 'Upload ETL workbook', exact: true }).click();
  const upload = await (await uploaded).json();
  await page.getByRole('button', { name: 'Validate ETL workbook', exact: true }).click();
  await expect.poll(async () => {
    if (await page.getByRole('button', { name: 'Review schedules and load policies' }).count()) return 'READY';
    if (await page.getByText('TARGET_BUSY', { exact: true }).count()) {
      const retry = page.getByRole('button', { name: 'Validate ETL workbook', exact: true });
      if (await retry.isEnabled()) await retry.click();
    }
    return 'WAITING';
  }, { timeout: 60000, intervals: [1000, 2000, 3000] }).toBe('READY');
  await page.getByRole('button', { name: 'Review schedules and load policies' }).click();
  const authority = page.getByRole('region', { name: 'Replacement authorization for ' + fixtures[fixture] });
  await expect(authority.getByRole('option', { name: /SCHEDULED/ })).toBeDisabled();
  const empty = authority.getByRole('checkbox', { name: 'Allow a valid empty dataset to empty the target', exact: true });
  await expect(empty).not.toBeChecked();
  await empty.check();
  await authority.getByRole('checkbox', { name: /I authorize replacing all rows/ }).check();
  await expect(authority.getByRole('button', { name: 'Grant ONCE authority' })).toBeDisabled();
  await authority.getByRole('checkbox', { name: /I separately authorize emptying every row/ }).check();
  await expect(authority.getByRole('button', { name: 'Grant ONCE authority' })).toBeEnabled();
  await empty.uncheck();
  await authority.getByRole('checkbox', { name: /I authorize replacing all rows/ }).check();
  await authority.getByRole('button', { name: 'Grant ONCE authority' }).click();
  await expect(authority.getByText(/Authority saved: GRANTED/)).toBeVisible();
  const context = await browser.newContext({ viewport: page.viewportSize() ?? undefined });
  try {
    const fresh = await context.newPage();
    await fresh.goto(new URL('/dag-builder', page.url()).href);
    const history = fresh.getByRole('region', { name: 'ETL workbook history' });
    await expect(history.getByRole('table')).toBeVisible();
    const row = history.getByRole('row').filter({ hasText: upload.id });
    // The retained demo has multiple history pages. A fresh browser must find
    // the server record through pagination, without relying on local state.
    for (let pageIndex = 0; pageIndex < 100 && await row.count() === 0; pageIndex++) {
      const first = history.locator('tbody tr').first();
      const previous = await first.innerText();
      const next = history.getByRole('button', { name: 'Next ETL workbooks', exact: true });
      await expect(next).toBeEnabled();
      await next.click();
      await expect(first).not.toHaveText(previous);
    }
    await row.getByRole('button', { name: 'Open ETL workbook' }).click();
    await fresh.getByRole('button', { name: 'Review validated workbook', exact: true }).click();
    await fresh.getByRole('button', { name: 'Review schedules and load policies' }).click();
    const saved = fresh.getByRole('region', { name: 'Replacement authorization for ' + fixtures[fixture] });
    await expect(saved.getByRole('cell', { name: 'GRANTED', exact: true })).toBeVisible();
    await saved.getByRole('button', { name: 'View authority details' }).click();
    await expect(saved.getByText('Authority details', { exact: true })).toBeVisible();
    await saved.getByRole('checkbox', { name: 'I understand revocation does not cancel an admitted transaction.' }).check();
    await saved.getByRole('button', { name: 'Revoke authority', exact: true }).click();
    await expect(saved.getByRole('cell', { name: 'REVOKED', exact: true })).toBeVisible();
  } finally { await context.close(); }
});

test('Invalid workbook shows actionable errors without deployment', async ({ page }) => {
  await page.goto('/dag-builder');
  await page.getByLabel('ETL Definition workbook', { exact: true }).setInputFiles('/tests/dag-fixtures/invalid.xlsx');
  await page.getByRole('button', { name: 'Upload ETL workbook', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Validate ETL workbook', exact: true })).toBeEnabled();
  const first = page.waitForResponse(response => response.url().endsWith('/validate') && response.request().method() === 'POST');
  await page.getByRole('button', { name: 'Validate ETL workbook', exact: true }).click();
  const initial = await (await first).json();
  await expect(page.getByText(/Validation failed/)).toBeVisible({ timeout: 45000 });
  await expect(page.getByRole('button', { name: 'Confirm and deploy workflows', exact: true })).toHaveCount(0);
  const second = page.waitForResponse(response => response.url().endsWith('/validate') && response.request().method() === 'POST');
  await page.getByRole('button', { name: 'Validate ETL workbook', exact: true }).click();
  expect((await (await second).json()).id).not.toBe(initial.id);
  await expect(page.getByText(/Validation failed/)).toBeVisible({ timeout: 45000 });
});

test('ONCE permits a manual replacement and SCHEDULED is required for activation', async ({ page }, testInfo) => {
  test.setTimeout(300000);
  const fixtures = JSON.parse(await readFile('/tests/dag-fixtures/index.json', 'utf8'));
  const manual = 'runrefresh-' + testInfo.project.name;
  await reviewWorkbook(page, manual);
  const result = await deployReviewed(page, fixtures[manual]);
  const authority = page.getByRole('region', { name: 'Replacement authorization for ' + fixtures[manual] });
  await authority.getByRole('checkbox', { name: /I authorize replacing all rows/ }).check();
  await authority.getByRole('button', { name: 'Grant ONCE authority' }).click();
  await expect(authority.getByText(/Authority saved: GRANTED/)).toBeVisible();
  await result.getByRole('checkbox', { name: /I confirm the schedule state change/ }).check();
  await result.getByRole('button', { name: 'Enable manual execution', exact: true }).click();
  await expect(page.getByText(/State command succeeded/)).toBeVisible({ timeout: 30000 });
  await result.getByRole('checkbox', { name: /I confirm a new manual run/ }).check();
  await result.getByRole('button', { name: 'Run workflow now', exact: true }).click();
  await expect(authority.getByRole('cell', { name: 'CONSUMED', exact: true })).toBeVisible({ timeout: 60000 });
  await expect(result.getByRole('button', { name: 'Run workflow now', exact: true })).toBeDisabled();

  const scheduled = 'scheduled-' + testInfo.project.name;
  await reviewWorkbook(page, scheduled);
  const scheduleResult = await deployReviewed(page, fixtures[scheduled]);
  const scheduleAuthority = page.getByRole('region', { name: 'Replacement authorization for ' + fixtures[scheduled] });
  await scheduleAuthority.getByRole('checkbox', { name: /I authorize replacing all rows/ }).check();
  await scheduleAuthority.getByRole('button', { name: 'Grant ONCE authority' }).click();
  await expect(scheduleAuthority.getByText(/Authority saved: GRANTED/)).toBeVisible();
  await scheduleResult.getByRole('checkbox', { name: /I confirm the schedule state change/ }).check();
  await expect(scheduleResult.getByRole('button', { name: 'Activate schedule', exact: true })).toBeDisabled();
  await scheduleAuthority.getByRole('combobox', { name: /Authority scope/ }).selectOption('SCHEDULED');
  await scheduleAuthority.getByRole('checkbox', { name: /I authorize replacing all rows/ }).check();
  await scheduleAuthority.getByRole('button', { name: 'Grant SCHEDULED authority' }).click();
  await expect(scheduleResult.getByRole('button', { name: 'Activate schedule', exact: true })).toBeEnabled();
  await scheduleResult.getByRole('button', { name: 'Activate schedule', exact: true }).click();
  await expect(page.getByText(/State command succeeded/)).toBeVisible({ timeout: 30000 });
  await scheduleResult.getByRole('checkbox', { name: /I confirm the schedule state change/ }).check();
  const paused = page.waitForResponse(response => response.url().endsWith('/state') && response.request().method() === 'PATCH');
  await scheduleResult.getByRole('button', { name: 'Pause future scheduling', exact: true }).click();
  const response = await paused;
  const command = await response.json();
  expect(response.status(), JSON.stringify(command)).toBe(202);
  await expect.poll(async () => {
    const current = await (await page.request.get('/api/v1/operations/' + command.id)).json();
    return { state: current.state, error: current.error?.error?.code ?? null };
  }, { timeout: 30000 }).toEqual({ state: 'SUCCEEDED', error: null });
  await expect(page.getByText(/State command succeeded/)).toBeVisible({ timeout: 30000 });
});
