// H14's Playwright helpers: a headless Chromium with no proxy, a page that records console errors, page errors and
// failed responses, and a screenshot helper writing under bughunt/notes/H14/shots/.
import { chromium } from 'playwright';
import { mkdirSync } from 'node:fs';

export const SHOTS = '/home/user/openFermentUI/bughunt/notes/H14/shots';
mkdirSync(SHOTS, { recursive: true });

export async function open(origin, { width = 1440, height = 1000 } = {}) {
  const browser = await chromium.launch({
    executablePath: '/opt/pw-browsers/chromium',
    args: ['--no-proxy-server'],
  });
  const context = await browser.newContext({ viewport: { width, height } });
  const page = await context.newPage();
  const log = [];
  page.on('console', (m) => {
    if (m.type() === 'error' || m.type() === 'warning') log.push(`[console.${m.type()}] ${m.text()}`);
  });
  page.on('pageerror', (e) => log.push(`[pageerror] ${e.message}`));
  page.on('response', (r) => {
    if (r.status() >= 400) log.push(`[http ${r.status()}] ${r.request().method()} ${r.url()}`);
  });
  page.on('requestfailed', (r) => log.push(`[failed] ${r.method()} ${r.url()} ${r.failure()?.errorText}`));
  return { browser, context, page, log, origin };
}

export async function shot(page, name) {
  const p = `${SHOTS}/${name}.png`;
  await page.screenshot({ path: p, fullPage: true });
  return p;
}

export async function go(page, origin, path) {
  await page.goto(`${origin}/#${path}`);
  await page.waitForLoadState('networkidle').catch(() => {});
  await page.waitForTimeout(800);
}

export async function text(page, sel = '#of-main') {
  const el = await page.$(sel);
  return el ? (await el.innerText()).replace(/\n{3,}/g, '\n\n') : '(no ' + sel + ')';
}

export function drain(log) {
  const out = log.splice(0, log.length);
  return out;
}
