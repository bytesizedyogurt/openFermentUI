// H7-05: open an address naming a project the service does not hold, and, as a control, an address naming the one
// project it holds, each in a fresh browser context with empty storage. Count the page loads and the
// GET /api/projects requests in a fixed window, then read where the page ends.
//   node unknown.mjs <origin> <held id> <unknown id> <seconds> <facts.json>
import { chromium } from 'playwright';
import { writeFileSync } from 'node:fs';

const [origin, held, unknown, seconds, factsPath] = process.argv.slice(2);
const windowMs = Number(seconds) * 1000;
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--no-proxy-server'] });

// A read of a page that may be mid-reload: a few short tries, each held to 1 s.
async function read(fn, fallback) {
  for (let i = 0; i < 5; i += 1) {
    try {
      return await Promise.race([fn(), new Promise((_, no) => setTimeout(() => no(new Error('slow')), 1000))]);
    } catch { await new Promise((r) => setTimeout(r, 50)); }
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
  const t0 = Date.now();
  await page.goto(`${origin}/#/p/${projectId}/runbooks`, { waitUntil: 'load' });
  await page.waitForTimeout(windowMs);
  const inWindow = { loads, projects, ms: Date.now() - t0 };
  // The 2 s after the window: is it still loading?
  await page.waitForTimeout(2000);
  const after = { loads: loads - inWindow.loads, projects: projects - inWindow.projects };
  const address = new URL(page.url()).hash;
  const stored = await read(() => page.evaluate(() => localStorage.getItem('openferment.project')), '?');
  const opening = await read(() => page.locator('[data-testid=opening-project]').count(), '?');
  const main = await read(async () => (await page.locator('main').first().innerText()).replace(/\s+/g, ' ').slice(0, 160), '');
  await read(() => context.close(), null);
  return { projectId, inWindow, after, address, stored, opening, main };
}

const facts = { seconds: Number(seconds), held: await visit(held), unknown: await visit(unknown) };
await read(() => browser.close(), null);
writeFileSync(factsPath, JSON.stringify(facts, null, 2));
process.exit(0);
