// H7-05: open an address naming a project the service does not hold, and, as a control, an address naming the one
// project it holds, each in a fresh browser context with empty storage. Count the page loads and the
// GET /api/projects requests over a fixed window, and read where the page ends.
//   node unknown.mjs <origin> <held id> <unknown id> <seconds> <facts.json>
import { chromium } from 'playwright';
import { writeFileSync } from 'node:fs';

const [origin, held, unknown, seconds, factsPath] = process.argv.slice(2);
const windowMs = Number(seconds) * 1000;
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--no-proxy-server'] });

async function settle(page, fn, fallback) {
  // The page may be mid-reload: try a few times before giving up.
  for (let i = 0; i < 20; i += 1) {
    try { return await fn(); } catch { await new Promise((r) => setTimeout(r, 50)); }
  }
  return fallback;
}

async function visit(projectId) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  let loads = 0;
  let projects = 0;
  page.on('load', () => (loads += 1));
  page.on('request', (r) => { if (new URL(r.url()).pathname === '/api/projects' && r.method() === 'GET') projects += 1; });
  await page.goto(`${origin}/#/p/${projectId}/runbooks`, { waitUntil: 'load' });
  await page.waitForTimeout(windowMs);
  const hash = await settle(page, () => page.evaluate(() => location.hash), '?');
  const stored = await settle(page, () => page.evaluate(() => localStorage.getItem('openferment.project')), '?');
  const screen = await settle(page, async () => (await page.locator('body').innerText()).replace(/\s+/g, ' ').slice(0, 200), '');
  // A second, shorter look: is it still loading?
  const before = loads;
  await page.waitForTimeout(2000);
  const later = loads - before;
  await context.close();
  return { projectId, loads, projects, hash, stored, screen, loadsInNext2s: later };
}

const facts = { seconds: Number(seconds), held: await visit(held), unknown: await visit(unknown) };
await browser.close();
writeFileSync(factsPath, JSON.stringify(facts, null, 2));
