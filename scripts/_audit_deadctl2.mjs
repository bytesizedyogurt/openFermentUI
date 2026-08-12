import { chromium } from 'playwright';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';

const ROOT = '/tmp/claude-0/-home-user-openFermentUI/167fd0e3-b3d3-562c-b052-449a10776bea/scratchpad/dist-dc';
const PORT = 4487;
const MIME = { '.html':'text/html', '.js':'text/javascript', '.css':'text/css', '.woff2':'font/woff2', '.woff':'font/woff', '.svg':'image/svg+xml' };
const server = http.createServer((req, res) => {
  const u = decodeURIComponent(req.url.split('?')[0]);
  let f = path.join(ROOT, u);
  if (!fs.existsSync(f) || fs.statSync(f).isDirectory()) f = path.join(ROOT, 'index.html');
  res.writeHead(200, { 'Content-Type': MIME[path.extname(f)] ?? 'application/octet-stream' });
  fs.createReadStream(f).pipe(res);
});
await new Promise(r => server.listen(PORT, r));

const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
const page = await browser.newPage({ viewport: { width: 1500, height: 1000 } });
page.on('pageerror', e => console.log('PAGEERROR', String(e)));
const go = async (h) => { await page.goto(`http://localhost:${PORT}/#${h}`, { waitUntil:'domcontentloaded' }); await page.evaluate(x=>location.hash=x, h); await page.waitForTimeout(600); };
const sig = () => page.evaluate(() => document.querySelector('main')?.innerText.replace(/\s+/g,' ').slice(0,4000) ?? '');

console.log('### 1. Ledger rail mark click -> /ledger/records?record=');
await go('/ledger/p/titer_secreted');
const marks = await page.locator('div[aria-hidden] button').count();
console.log('rail buttons on param page:', marks);
if (marks) {
  await page.locator('div[aria-hidden] button').nth(1).click();
  await page.waitForTimeout(700);
  const h = await page.evaluate(()=>location.hash);
  const txt = await sig();
  console.log('hash after mark click:', h);
  console.log('scoped chip present:', /Scoped to/.test(txt));
  const hl = await page.evaluate(() => {
    const els = [...document.querySelectorAll('[class*="ring-"], [aria-selected="true"], [data-highlight]')];
    return els.length;
  });
  console.log('rows total after ?record= :', await page.locator('table tbody tr, [role="row"]').count());
  console.log('any highlight elements:', hl);
}

console.log('\n### 2. /extract?paper= link from Library');
await go('/trawl');
await page.waitForTimeout(400);
const exLinks = await page.locator('a[href*="/extract?paper="]').count();
console.log('links to /extract?paper= on /trawl:', exLinks);
if (exLinks) {
  const href0 = await page.locator('a[href*="/extract?paper="]').first().getAttribute('href');
  console.log('first href:', href0);
  await page.locator('a[href*="/extract?paper="]').first().click();
  await page.waitForTimeout(800);
  console.log('landed hash:', await page.evaluate(()=>location.hash));
  const t = await sig();
  console.log('shows Scoped-to chip:', /Scoped to/.test(t));
  console.log('page title:', t.slice(0,140));
}

console.log('\n### 3. Bulk "Extract" action on /trawl');
await go('/trawl');
await page.waitForTimeout(500);
const cbs = page.locator('table tbody input[type=checkbox]');
console.log('row checkboxes:', await cbs.count());
if (await cbs.count()) {
  await cbs.first().check().catch(()=>{});
  await page.waitForTimeout(300);
  const bar = await sig();
  console.log('bulk bar text:', bar.slice(0,200));
  const bulkLinks = await page.locator('a[href*="extract"]').count();
  console.log('bulk extract links:', bulkLinks);
}

console.log('\n### 4. Notary design selection changes checklist');
await go('/notary');
const cards = page.locator('section button[aria-pressed]');
const n = await cards.count();
console.log('design cards:', n);
const before = await sig();
if (n > 3) {
  await cards.nth(3).click(); await page.waitForTimeout(400);
  const after = await sig();
  console.log('changed on select:', before !== after);
  const diffOnlyId = before.replace(/sc-s\d-d\d+/g,'X') === after.replace(/sc-s\d-d\d+/g,'X');
  console.log('difference is ONLY the design id:', diffOnlyId);
  console.log('publish disabled:', await page.locator('button:has-text("Publish")').isDisabled());
}

console.log('\n### 5. DesignDetail links');
await go('/fermos/d/sc-s1-d01');
const dd = await sig();
console.log(dd.slice(0,120));
const recLinks = await page.locator('a[href*="/ledger/records?record="]').count();
console.log('record links:', recLinks);
if (recLinks) {
  const h0 = await page.locator('a[href*="/ledger/records?record="]').first().getAttribute('href');
  console.log('href:', h0);
  await page.locator('a[href*="/ledger/records?record="]').first().click();
  await page.waitForTimeout(800);
  console.log('landed:', await page.evaluate(()=>location.hash));
  const t = await sig();
  console.log('scoped/highlight visible:', /Scoped to|record=/.test(t));
}

console.log('\n### 6. Ledger records facets change rows');
await go('/ledger/records');
await page.waitForTimeout(900);
const rowCount = async () => page.evaluate(() => document.querySelectorAll('table tbody tr').length);
console.log('rows initial:', await rowCount());
const facetBtns = page.locator('button', { hasText: /^\s*\w/ });
// find facet chips in the left facet column
const facetLabels = await page.evaluate(() => [...document.querySelectorAll('button')].map(b=>b.textContent.trim().replace(/\s+/g,' ')).slice(0,60));
console.log('buttons:', JSON.stringify(facetLabels.slice(0,40)));

await browser.close(); server.close();
