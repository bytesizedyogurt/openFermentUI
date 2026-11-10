// H7-06: what each detail page says of a row the project keeps, read in one of two states.
//   node words.mjs up      <origin> <project> <paths.json> <facts.json> <dist>
//   node words.mjs stopped <origin> <project> <paths.json> <facts.json> <dist>
// `up`: the service answers every request, the page's files and /api alike.
// `stopped`: run.sh has stopped the service, so nothing listens on the origin's port. The page's own files (index.html
// and assets/) come from the built app in <dist>, as they would from Vite under `pnpm dev` or from a page opened as the
// service went away; every /api request goes to the closed port and fails at the connection, as it does for a person.
// Each address opens in a fresh page of one fresh browser context, and the text of the main region (#of-main) and of
// the whole page is kept once it stops changing.
import { chromium } from 'playwright';
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const [state, origin, project, pathsFile, factsPath, dist] = process.argv.slice(2);
const paths = JSON.parse(readFileSync(pathsFile, 'utf8'));
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--no-proxy-server'] });
const flat = (s) => s.replace(/\s+/g, ' ').trim();
const facts = { state, apiRequests: 0, apiFailed: 0, apiAnswered: 0, pages: {} };

const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
if (state === 'stopped')
  await context.route(
    (url) => url.origin === origin && !url.pathname.startsWith('/api/'),
    (route) => {
      const pathname = new URL(route.request().url()).pathname;
      const file = join(dist, pathname === '/' ? 'index.html' : pathname);
      return existsSync(file) ? route.fulfill({ path: file }) : route.fulfill({ status: 404, body: '' });
    },
  );
context.on('request', (r) => { if (new URL(r.url()).pathname.startsWith('/api/')) facts.apiRequests += 1; });
context.on('requestfailed', (r) => { if (new URL(r.url()).pathname.startsWith('/api/')) facts.apiFailed += 1; });
context.on('requestfinished', (r) => { if (new URL(r.url()).pathname.startsWith('/api/')) facts.apiAnswered += 1; });

for (const [name, path] of Object.entries(paths)) {
  const page = await context.newPage();
  await page.goto(`${origin}/#/p/${encodeURIComponent(project)}${path}`, { waitUntil: 'load' });
  // The page's first reads settle (answered or failed), then the words stop changing.
  await page.waitForLoadState('networkidle').catch(() => undefined);
  let main = '';
  for (let i = 0; i < 12; i += 1) {
    await page.waitForTimeout(500);
    const now = flat(await page.locator('#of-main').innerText().catch(() => ''));
    if (now && now === main) break;
    main = now;
  }
  const body = flat(await page.locator('body').innerText().catch(() => ''));
  facts.pages[name] = { path, address: new URL(page.url()).hash, main, body };
  await page.close();
}
await context.close();
writeFileSync(factsPath, JSON.stringify(facts, null, 1));
await browser.close();
