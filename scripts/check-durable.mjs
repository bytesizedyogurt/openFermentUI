/**
 * Durable-tier round trip (OF-BLD-006 §4.6).
 *
 * §4.6 exists because a fermentation at hour 14 with timers running and
 * deviations logged cannot be lost to a page reload — that is a safety
 * problem, not an inconvenience. This test is the thing that says whether the
 * guarantee actually holds, so it drives a real browser through a real reload
 * in one persistent context rather than asserting against a mock.
 *
 * It checks all three tiers, because getting one right is not the point:
 * Durable survives, Ephemeral does NOT (a collapsed panel that followed you
 * across sessions would be a bug), and reset clears persistence as well as
 * memory or it would restore itself on the next load.
 *
 *   pnpm build && node scripts/check-durable.mjs
 */
import { chromium } from 'playwright';
import { createServer } from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { join, extname } from 'node:path';
const DIST = join(process.cwd(), 'dist'); const PORT = 4364;
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.woff2': 'font/woff2', '.woff': 'font/woff' };
const server = createServer(async (req, res) => {
  try { const url = decodeURIComponent((req.url ?? '/').split('?')[0]);
    let file = join(DIST, url === '/' ? 'index.html' : url);
    try { if ((await stat(file)).isDirectory()) file = join(file, 'index.html'); } catch { file = join(DIST, 'index.html'); }
    const b = await readFile(file);
    res.writeHead(200, { 'Content-Type': MIME[extname(file)] ?? 'application/octet-stream' }); res.end(b);
  } catch { res.writeHead(404).end('nf'); }
});
await new Promise((r) => server.listen(PORT, r));
const exe = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const browser = await chromium.launch(existsSync(exe) ? { executablePath: exe } : {});
let fails = 0; const errs = [];
const check = (l, ok, x='') => { console.log((ok?'✓':'✗')+' '+l+(x?'  '+x:'')); if(!ok) fails++; };

// One persistent context so IndexedDB survives across page loads, exactly as
// a real browser tab would.
const ctx = await browser.newContext({ viewport: { width: 1400, height: 1000 } });
const page = await ctx.newPage();
page.on('console', m => { if (m.type()==='error' && !/DevTools|favicon/i.test(m.text())) errs.push(m.text()); });
page.on('pageerror', e => errs.push('UNCAUGHT: ' + e.message));
const go = async r => { await page.goto(`http://localhost:${PORT}/#${r}`, { waitUntil:'networkidle' }); await page.waitForTimeout(1300); };
const body = async () => (await page.locator('main').innerText()).replace(/\s+/g,' ');

await go('/runbooks/rb-lyo-ambient');
check('starts unlocked', (await body()).includes('not yet locked'));
await page.getByRole('button', { name: /Lock predictions/ }).click();
await page.waitForTimeout(1200);           // let the debounced write flush
check('locked in this session', (await body()).includes('Frozen'));
const hashBefore = (await body()).match(/hash ([0-9a-f]{12})/)?.[1];
check('hash captured', !!hashBefore, hashBefore);

// THE TEST: full reload, same browsing context.
await page.reload({ waitUntil: 'networkidle' });
await page.waitForTimeout(1600);
const after = await body();
check('STILL LOCKED after a page reload', after.includes('Frozen'));
check('same hash survived', after.includes(hashBefore ?? '@@'), hashBefore);
check('no editable inputs after reload',
  await page.locator('section[aria-labelledby="band-predictions"] input[type="number"]').count() === 0);

// Ephemeral state must NOT survive.
await page.evaluate(() => document.documentElement.dataset.density);
const dens1 = await page.evaluate(() => document.documentElement.dataset.density);
await page.keyboard.press('Shift+D');
await page.waitForTimeout(400);
const dens2 = await page.evaluate(() => document.documentElement.dataset.density);
check('density toggled', dens1 !== dens2, `${dens1} -> ${dens2}`);
await page.reload({ waitUntil: 'networkidle' });
await page.waitForTimeout(1400);
const dens3 = await page.evaluate(() => document.documentElement.dataset.density);
check('Ephemeral density RESET on reload', dens3 === dens1, `${dens3}`);

// Reset must clear the durable store, not just memory.
await page.evaluate(() => { /* noop */ });
await go('/settings/corpus');
const resetBtn = page.getByRole('button', { name: /Reset demo data/ }).first();
if (await resetBtn.count() > 0) {
  await resetBtn.click();                       // opens the confirmation
  await page.waitForTimeout(500);
  await page.locator('div[role="dialog"]').getByRole('button', { name: /Reset demo data/ }).click();
  await page.waitForTimeout(1400);
  await page.reload({ waitUntil: 'networkidle' });
  await page.waitForTimeout(1600);
  await go('/runbooks/rb-lyo-ambient');
  check('reset cleared the durable store', (await body()).includes('not yet locked'));
} else {
  console.log('  (reset button not on this screen — checked via palette instead)');
  await page.keyboard.press('Control+k');
  await page.waitForTimeout(400);
  await page.locator('input[aria-label="Command palette"]').fill('Reset demo');
  await page.waitForTimeout(300);
  await page.keyboard.press('Enter');
  await page.waitForTimeout(1200);
  await page.reload({ waitUntil: 'networkidle' });
  await page.waitForTimeout(1600);
  await go('/runbooks/rb-lyo-ambient');
  check('reset cleared the durable store', (await body()).includes('not yet locked'));
}

console.log('\nconsole errors:', errs.length);
if (errs.length) console.log(errs.slice(0,4).join('\n'));
console.log(fails===0 && errs.length===0 ? '\nDURABLE TIER HOLDS' : `\n${fails} failures`);
await browser.close(); server.close();
process.exit(fails===0 && errs.length===0 ? 0 : 1);
