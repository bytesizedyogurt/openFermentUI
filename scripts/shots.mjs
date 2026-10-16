/**
 * Photographs of the running app (OF-BLD-014 §1.4).
 *
 *   pnpm shots [--url http://127.0.0.1:4173] [--prefix shot] /route [/route …]
 *
 * Opens each route against an app that is already running (`pnpm prototype:up`
 * or `pnpm demo:offline`), waits for the page to settle, and writes
 * docs/shots/<prefix>-<route>.png, the route's segments joined by dashes
 * (`/` is `home`): 1440 px wide, and as tall as the screen's content up to
 * 4000 px. A route that resolves to no screen fails, and so does the run.
 * The truth pass at the end of each phase keeps up to four of them in the
 * repository. Chromium is found the way scripts/smoke.mjs finds it:
 * CHROMIUM_PATH, then the pre-installed one, then Playwright's own.
 */
import { existsSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';
import { chromium } from 'playwright';

const ROOT = process.cwd();
const OUT = join(ROOT, 'docs', 'shots');
const WIDTH = 1440;
const HEIGHT = 900;
// The tallest photograph, so one long table cannot make a file nobody opens.
const MAX_HEIGHT = 4000;

const args = process.argv.slice(2);
let url = 'http://127.0.0.1:4173';
let prefix = 'shot';
const routes = [];
for (let i = 0; i < args.length; i++) {
  const a = args[i];
  if (a === '--url' || a === '--prefix') {
    const value = args[++i];
    if (!value) die(`${a} needs a value`);
    if (a === '--url') url = value.replace(/\/+$/, '');
    else prefix = value;
  } else if (a.startsWith('/')) {
    routes.push(a);
  } else {
    die(`unexpected argument ${a}: a route starts with /`);
  }
}
if (!routes.length) die('usage: pnpm shots [--url <app>] [--prefix <name>] /route [/route …]');
if (!/^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(prefix)) die(`--prefix ${prefix}: letters, digits, dot, dash and underscore only`);

function die(message) {
  console.error(`✗ ${message}`);
  process.exit(1);
}

/** `/biorepo/witness` → `biorepo-witness`; `/` → `home`. */
function fileStem(route) {
  const stem = route.split(/[/?#]/).filter(Boolean).join('-').replace(/[^A-Za-z0-9._-]/g, '_');
  return stem || 'home';
}

// The app must already be up: a photograph of an error page proves nothing.
try {
  const r = await fetch(`${url}/`);
  if (!r.ok) die(`${url} answered ${r.status}. Start the app first: pnpm prototype:up (or pnpm demo:offline)`);
} catch {
  die(`nothing answers at ${url}. Start the app first: pnpm prototype:up (or pnpm demo:offline)`);
}

mkdirSync(OUT, { recursive: true });
const executablePath = process.env.CHROMIUM_PATH ?? '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const browser = await chromium.launch(existsSync(executablePath) ? { executablePath } : {});
let failed = 0;
try {
  for (const route of routes) {
    const page = await browser.newPage({ viewport: { width: WIDTH, height: HEIGHT } });
    const errors = [];
    page.on('pageerror', (e) => errors.push(e.message));
    try {
      await page.goto(`${url}/#${route}`, { waitUntil: 'networkidle' });
      // Settled: no request in flight, fonts loaded, and the screen's own
      // simulated latency (src/sim/latency.ts) given time to resolve.
      await page.evaluate(() => document.fonts.ready);
      await page.waitForTimeout(1200);
      await page.waitForLoadState('networkidle');
      // The same test smoke.mjs makes: a route that resolves to no screen is
      // a typo, and its photograph would be a picture of an error page.
      if (/Route not found/i.test(await page.locator('body').innerText())) {
        throw new Error('the route resolves to no screen in this build');
      }
      // The app scrolls inside its main pane (#of-main), so the page itself
      // is one viewport tall. Grow the viewport by what the pane hides, up to
      // MAX_HEIGHT, and the photograph shows the whole screen.
      const hidden = await page.evaluate(() => {
        const main = document.getElementById('of-main');
        return main ? Math.max(0, main.scrollHeight - main.clientHeight) : 0;
      });
      if (hidden > 0) {
        await page.setViewportSize({ width: WIDTH, height: Math.min(HEIGHT + hidden, MAX_HEIGHT) });
        await page.waitForTimeout(300);
      }
      const file = join(OUT, `${prefix}-${fileStem(route)}.png`);
      await page.screenshot({ path: file });
      console.log(`✓ ${route.padEnd(32)} ${file.slice(ROOT.length + 1)}${errors.length ? `  (page errors: ${errors.length})` : ''}`);
    } catch (e) {
      failed++;
      console.log(`✗ ${route.padEnd(32)} ${String(e).split('\n')[0].slice(0, 200)}`);
    } finally {
      await page.close();
    }
  }
} finally {
  await browser.close();
}
process.exit(failed ? 1 : 0);
