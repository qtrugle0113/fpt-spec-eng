// Kiểm chứng file static thật trên production dist; API bị tắt để thử tải độc lập.
const { chromium } = require('@playwright/test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { createHash } = require('node:crypto');
const { pathToFileURL } = require('node:url');

const root = path.resolve(__dirname, '../..');
const evidence = path.join(root, '.tools/user-guide-download');
const filename = 'Airflow-Automation-Tool-Huong-dan-su-dung.html';
const source = path.join(root, 'outputs/user-guide', filename);
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const routes = ['/', '/connections', '/tables', '/dag-builder', '/monitoring', '/settings'];

(async () => {
  fs.mkdirSync(evidence, { recursive: true });
  const expected = fs.readFileSync(source);
  for (const directory of ['frontend/public/user-guide', 'frontend/dist/user-guide']) {
    assert.equal(hash(fs.readFileSync(path.join(root, directory, filename))), hash(expected), directory);
  }
  const dockerfile = fs.readFileSync(path.join(root, 'frontend/Dockerfile'), 'utf8');
  assert.ok(dockerfile.indexOf('COPY frontend/public ./public') >= 0);
  assert.ok(dockerfile.indexOf('COPY frontend/public ./public') < dockerfile.indexOf('RUN npm run build'));
  const { preview } = await import('vite');
  const server = await preview({ root: path.join(root, 'frontend'), configFile: false, preview: { host: '127.0.0.1', port: 0 } });
  let browser;
  const results = [];
  try {
    const origin = `http://127.0.0.1:${server.httpServer.address().port}`;
    const response = await fetch(`${origin}/user-guide/${filename}`);
    assert.equal(response.status, 200);
    assert.match(response.headers.get('content-type'), /text\/html/);
    assert.equal(hash(Buffer.from(await response.arrayBuffer())), hash(expected), 'HTTP serves guide, not SPA fallback');
    browser = await chromium.launch();
    let savedGuide;
    for (const width of [1366, 390, 320]) {
      const context = await browser.newContext({ viewport: { width, height: width === 1366 ? 768 : 844 } });
      const page = await context.newPage();
      const errors = [], writes = [];
      page.on('pageerror', error => errors.push(error.message));
      page.on('request', request => { if (!['GET', 'HEAD'].includes(request.method())) writes.push(request.method() + ' ' + request.url()); });
      await page.route('**/api/v1/**', route => route.abort('failed'));
      for (const route of width === 320 ? ['/settings'] : routes) {
        await page.goto(origin + route);
        await page.getByText('Backend unavailable', { exact: true }).waitFor();
        const link = page.getByRole('link', { name: 'Download User Guide', exact: true });
        assert.equal(await link.count(), 1);
        assert.ok(await link.evaluate(element => element.classList.contains('action-link')));
        const bounds = await link.boundingBox();
        assert.ok(bounds && bounds.y >= 0 && bounds.y + bounds.height <= page.viewportSize().height);
        assert.ok(bounds.height >= 36 && bounds.x >= 0 && bounds.x + bounds.width <= width);
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'No page overflow');
        if (route === '/connections') await page.getByPlaceholder('Code, name or host').fill('guide-state-check');
        const before = page.url();
        await link.focus();
        assert.ok(await link.evaluate(element => element === document.activeElement && getComputedStyle(element).outlineStyle !== 'none'));
        const pending = page.waitForEvent('download');
        if (route === '/settings') await page.keyboard.press('Enter');
        else await link.click();
        const download = await pending;
        assert.equal(download.suggestedFilename(), filename);
        savedGuide = path.join(evidence, `download-${width}-${route.slice(1) || 'dashboard'}.html`);
        await download.saveAs(savedGuide);
        assert.equal(hash(fs.readFileSync(savedGuide)), hash(expected));
        assert.equal(page.url(), before, 'Download preserves current screen');
        if (route === '/connections') assert.equal(await page.getByPlaceholder('Code, name or host').inputValue(), 'guide-state-check');
        if (route === '/settings') {
          if (width < 720) await page.getByRole('button', { name: 'Open menu', exact: true }).click();
          assert.equal(await page.getByRole('navigation', { name: 'Main navigation' }).getByRole('link').count(), 6);
          if (width < 720) await page.getByRole('button', { name: 'Close menu', exact: true }).click();
          await page.screenshot({ path: path.join(evidence, `ui-${width}.png`) });
        }
        results.push({ width, route, download: 'PASS', unchangedPage: true, backendUnavailable: true, keyboard: route === '/settings' });
      }
      assert.deepEqual(errors, []);
      assert.deepEqual(writes, []);
      await context.close();
    }
    const offline = await browser.newContext({ offline: true });
    const guide = await offline.newPage();
    const requests = [], errors = [];
    guide.on('request', request => { if (/^https?:/.test(request.url())) requests.push(request.url()); });
    guide.on('pageerror', error => errors.push(error.message));
    await guide.goto(pathToFileURL(savedGuide).href);
    assert.equal(await guide.locator('html').getAttribute('lang'), 'vi');
    assert.equal(await guide.locator('.chapter').count(), 16);
    assert.equal(await guide.locator('.screen img').count(), 12);
    await guide.evaluate(async () => {
      const images = [...document.querySelectorAll('.screen img')];
      images.forEach(image => { image.loading = 'eager'; });
      await Promise.all(images.map(image => image.decode()));
    });
    await guide.locator('.screen').first().click();
    assert.ok(await guide.locator('#viewer').isVisible());
    await guide.keyboard.press('Escape');
    assert.equal(await guide.locator('#viewer').isVisible(), false);
    assert.deepEqual(requests, []); assert.deepEqual(errors, []);
    await offline.close();
    const report = { status: 'PASS', sha256: hash(expected), bytes: expected.length, http: 'PASS', dockerCopy: 'PASS (static check only)', downloads: results, offline: { sections: 16, images: 12, zoom: true, networkRequests: 0 }, writes: 0 };
    fs.writeFileSync(path.join(evidence, 'validation.json'), JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report));
  } finally {
    await browser?.close();
    await new Promise(resolve => server.httpServer.close(resolve));
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
