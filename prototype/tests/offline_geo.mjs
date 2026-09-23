// Focused checks for offline queueing and geofenced check-in, opened straight from file://
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { pathToFileURL, fileURLToPath } from 'node:url';
import { existsSync } from 'node:fs';
import assert from 'node:assert/strict';

const modulePath = process.env.PLAYWRIGHT_MODULE || join(tmpdir(), 'visiontech-native-checks/playwright-core/index.mjs');
if (!existsSync(modulePath)) throw Error('Set PLAYWRIGHT_MODULE to an existing Playwright index.mjs');
const { chromium } = await import(pathToFileURL(modulePath).href);
const chrome = process.env.CHROME_PATH || 'C:/Users/ageng/.cache/puppeteer/chrome/win64-153.0.8010.36/chrome-win64/chrome.exe';
const url = 'file:///' + fileURLToPath(new URL('../index.html', import.meta.url)).replace(/\\/g, '/');

const browser = await chromium.launch({ headless: true, ...(existsSync(chrome) ? { executablePath: chrome } : {}) });
const context = await browser.newContext();
const page = await context.newPage();
const errors = [];
page.on('pageerror', e => errors.push(e.message));
page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
page.on('dialog', d => { errors.push('native dialog: ' + d.message()); d.dismiss(); });

const stored = () => page.evaluate(() => JSON.parse(localStorage.getItem(VTStorage.key)));
const ready = () => page.waitForFunction(() => typeof VT?.run === 'function' && typeof VT?.offline === 'object');
const go = async hash => { await page.evaluate(h => { location.hash = h; }, hash); await page.waitForTimeout(250); };

await page.goto(url);
await ready();
await page.evaluate(async () => { VT.state = await VTStorage.reset(); });

// 1. Offline: a checklist toggle is applied locally and queued, then cleared once back online.
await go('#/desktop/leader/plan/wp-001/days');
await context.setOffline(true);
await page.waitForTimeout(150);
const taskId = await page.evaluate(() => VT.state.plans.find(p => p.id === 'wp-001').days[0].tasks[1].id);
await page.click(`[data-task="${taskId}"]`);
await page.waitForTimeout(300);

assert.match(await page.locator('#notifications').innerText(), /Tersimpan secara lokal \(Luring\)/);
assert.equal((await stored()).offline_queue.length, 1, 'offline transaction must be queued in storage');
assert.match(await page.locator('#net-status').innerText(), /Luring · 1 antrean/);

await context.setOffline(false);
await page.waitForTimeout(600);
assert.equal((await stored()).offline_queue.length, 0, 'queue is cleared after syncing');
assert.equal((await page.evaluate(() => VT.state.audit[0].action)), 'SYNC_OFFLINE');
assert.match(await page.locator('#net-status').innerText(), /Tersinkronisasi/);

// 2. Check-in outside the radius needs a selfie; inside the radius it does not.
await go('#/mobile/finance/attendance');
await page.getByRole('button', { name: 'Catat masuk' }).click();
await page.waitForTimeout(250);
await page.evaluate(() => { navigator.geolocation.getCurrentPosition = ok => ok({ coords: { latitude: -6.2088, longitude: 106.8456, accuracy: 10 } }); });
await page.click('#dialog [data-geo="gps"]');
await page.waitForTimeout(300);

assert.match(await page.locator('#dialog [data-geo-distance]').innerText(), /di luar radius/);
assert.equal(await page.locator('#dialog input[name="selfie"]').getAttribute('capture'), 'user');
await page.evaluate(() => { document.querySelector('#dialog input[name="selfie"]').required = false; });
await page.click('#dialog button[type=submit]');
await page.waitForTimeout(300);
assert.match(await page.locator('#dialog .dialog-error').innerText(), /swafoto wajib/);

await page.setInputFiles('#dialog input[name="selfie"]', { name: 'swafoto.png', mimeType: 'image/png', buffer: Buffer.from('89504e470d0a1a0a', 'hex') });
await page.click('#dialog button[type=submit]');
await page.waitForTimeout(600);

const record = await page.evaluate(() => VT.state.attendance[0]);
assert.equal(record.employeeId, 'finance');
assert.equal(record.status, 'NEEDS_REVIEW');
assert.equal(record.coords.origin, 'GPS');
assert.ok(record.selfie?.id, 'selfie metadata is stored with the attendance record');
assert.ok(record.distance > 1000, 'a Jakarta fix is far outside the Medan site radius');

// 3. Service worker must stay out of the way when the prototype is opened from a file.
assert.equal(await page.evaluate(() => navigator.serviceWorker?.controller), null);

assert.deepEqual(errors, [], 'no page, console, or native dialog errors');
console.log(JSON.stringify({ checks: ['offline queue + sync', 'geofenced check-in with selfie', 'no service worker on file://'], errors }, null, 2));
await browser.close();
