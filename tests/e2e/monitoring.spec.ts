import { test, expect } from '@playwright/test';
import type { APIRequestContext } from '@playwright/test';
import { mkdir, readFile } from 'node:fs/promises';
test.use({ actionTimeout: 15000 });

async function completed(request: APIRequestContext, identity: string) {
  let result: { state: string } = { state: 'UNKNOWN' };
  await expect.poll(async () => { const response = await request.get('/api/v1/operations/' + identity); expect(response.ok()).toBe(true); result = await response.json(); return result.state; }, { timeout: 130000, intervals: [1000, 2000] }).toBe('SUCCEEDED');
  return result;
}

test('Monitoring queues a paused DAG then executes after explicit unpause with actual logs and metrics', async ({ page, request }, testInfo) => {
  test.setTimeout(240000);
  const references = JSON.parse(await readFile('/tests/dag-fixtures/index.json', 'utf8'));
  const fixture = 'append-' + testInfo.project.name; const dag = references[fixture];
  const connections = await (await request.get('/api/v1/connections?search=pg_etl')).json();
  const connection = connections.items.find((item: { code: string }) => item.code === 'pg_etl');
  expect((await (await request.post(`/api/v1/connections/${connection.id}/test`)).json()).status).toBe('SUCCESS');
  const uploaded = await (await request.post('/api/v1/definition-uploads', { multipart: { kind: 'ETL', file: { name: fixture + '.xlsx', mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', buffer: await readFile(`/tests/dag-fixtures/${fixture}.xlsx`) } } })).json();
  const validation = await request.post(`/api/v1/definition-uploads/${uploaded.id}/validate`, { headers: { 'Idempotency-Key': crypto.randomUUID() }, data: { expected_sha256: uploaded.sha256 } });
  expect(validation.status()).toBe(202); await completed(request, (await validation.json()).id);
  const review = await (await request.get(`/api/v1/definition-uploads/${uploaded.id}/etl-preview`)).json();
  const deployment = await request.post('/api/v1/dag-deployments', { headers: { 'Idempotency-Key': crypto.randomUUID() }, data: { upload_id: uploaded.id, dag_ids: [dag], confirmation_token: review.confirmation_token, support_objects_acknowledged: true } });
  expect(deployment.status()).toBe(202); await completed(request, (await deployment.json()).id);
  expect((await (await request.get('/api/v1/dags/' + dag)).json()).is_paused).toBe(true);
  await page.goto('/monitoring?dag=' + dag);
  await expect(page.getByRole('heading', { name: 'DAG Monitoring', exact: true })).toBeVisible();
  const details = page.getByRole('region', { name: 'Workflow details', exact: true });
  await details.getByRole('button', { name: 'Review workflow command', exact: true }).click();
  await details.getByRole('checkbox', { name: /I confirm this new manual run/ }).check();
  const submitted = page.waitForResponse(response => response.url().endsWith('/trigger') && response.request().method() === 'POST');
  await details.getByRole('button', { name: 'Confirm workflow command', exact: true }).click();
  const accepted = await submitted; expect(accepted.status()).toBe(202);
  const operation = await accepted.json(); const run = 'manual__aat_' + operation.id;
  await completed(request, operation.id);
  const row = details.getByRole('row').filter({ hasText: run });
  await expect(row.getByRole('cell', { name: 'queued', exact: true })).toBeVisible({ timeout: 30000 });
  expect((await (await request.get('/api/v1/dags/' + dag)).json()).is_paused).toBe(true);
  const controls = details.getByRole('region', { name: 'Workflow controls', exact: true });
  await controls.getByRole('combobox', { name: /^Command/ }).selectOption('activate');
  await controls.getByRole('button', { name: 'Review workflow command', exact: true }).click();
  await controls.getByRole('checkbox', { name: /I confirm this schedule activation/ }).check();
  const activation = page.waitForResponse(response => response.url().endsWith('/state') && response.request().method() === 'PATCH');
  await controls.getByRole('button', { name: 'Confirm workflow command', exact: true }).click();
  const activated = await activation; expect(activated.status()).toBe(202); await completed(request, (await activated.json()).id);
  await expect(row.getByRole('cell', { name: 'success', exact: true })).toBeVisible({ timeout: 130000 });
  await row.getByRole('button', { name: 'View run details', exact: true }).click();
  const runDetails = page.getByRole('region', { name: 'Run details', exact: true });
  await expect(runDetails.getByRole('heading', { name: 'ETL evidence' })).toBeVisible();
  await expect(runDetails.locator('dt').filter({ hasText: /^Loaded rows$/ }).locator('xpath=following-sibling::dd[1]')).toHaveText('3');
  await runDetails.getByRole('button', { name: 'View attempt logs' }).click();
  await expect(runDetails.getByRole('region', { name: 'Attempt logs', exact: true }).locator('pre')).not.toBeEmpty({ timeout: 30000 });
  await controls.getByRole('combobox', { name: /^Command/ }).selectOption('pause');
  await controls.getByRole('button', { name: 'Review workflow command', exact: true }).click();
  await controls.getByRole('checkbox', { name: /I confirm this pause command/ }).check();
  const pause = page.waitForResponse(response => response.url().endsWith('/state') && response.request().method() === 'PATCH');
  await controls.getByRole('button', { name: 'Confirm workflow command', exact: true }).click();
  const paused = await pause; expect(paused.status()).toBe(202); await completed(request, (await paused.json()).id);
  expect((await (await request.get('/api/v1/dags/' + dag)).json()).is_paused).toBe(true);
  expect((await (await request.get(`/api/v1/dags/${dag}/runs/${run}`)).json()).state).toBe('success');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await mkdir('/tmp/aat-e2e-artifacts', { recursive: true });
  await page.screenshot({ path: `/tmp/aat-e2e-artifacts/monitoring-${testInfo.project.name}.png`, fullPage: true });
});

test('An external DAG stays read-only even with an aat tag', async ({ page, request }) => {
  await expect.poll(async () => (await request.get('/api/v1/dags/external_monitoring_fixture')).status(), { timeout: 120000 }).toBe(200);
  await page.goto('/monitoring?dag=external_monitoring_fixture');
  const details = page.getByRole('region', { name: 'Workflow details', exact: true });
  await expect(details.getByText(/This external workflow is read-only/)).toBeVisible();
  await expect(details.getByRole('region', { name: 'Workflow controls', exact: true })).toHaveCount(0);
  await expect(details.getByRole('link', { name: 'Open workflow in Airflow', exact: true })).toHaveAttribute('href', /\/dags\/external_monitoring_fixture$/);
});
