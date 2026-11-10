// H7: open every rail screen and every secondary screen of the client in Chromium, in one state, and
// say what each page did: console errors, uncaught errors, unhandled rejections, failed requests,
// 4xx/5xx answers from /api, the screen boundary's card, the not-found page, and every in-app link
// whose address leaves the project (/p/<project>/...).
//
//   node walk_all.mjs <origin> <project> <state: empty|full|stopped> <out.json> [ids.json]
//
// State "stopped": the app is served, and every /api request is refused as a stopped service's would
// be (the page loads from the origin; each call to the service fails to connect).
import { chromium } from 'playwright';
import { writeFileSync, readFileSync, existsSync } from 'node:fs';

const [origin, project, state, out, idsFile] = process.argv.slice(2);
const ids = idsFile && existsSync(idsFile) ? JSON.parse(readFileSync(idsFile, 'utf8')) : {};
const id = (k, fallback) => ids[k] ?? fallback;

const RAIL = ['/', '/intake', '/biorepo', '/postdoc', '/geneos', '/fermos', '/pureos', '/proforma', '/runbooks', '/primer', '/guild', '/catalogues'];
const SECONDARY = [
  '/intake/ingest',
  '/biorepo/search', '/biorepo/compare', '/biorepo/witness', '/biorepo/artifacts',
  `/biorepo/artifacts/${id('artifact', 'missing-artifact')}`,
  `/biorepo/artifacts/${id('artifactCeiling', 'missing-artifact-2')}`,
  `/biorepo/paper/${id('paper', 'missing-paper')}`,
  `/postdoc/${id('conversation', 'lc-missing')}`,
  '/geneos/hosts', '/geneos/pathway', '/geneos/model', `/geneos/hosts/${id('strain', 'missing-strain')}`,
  '/fermos/simulate', '/fermos/vessel', '/fermos/forecast',
  '/pureos/build', '/pureos/build/new', `/pureos/train/${id('train', 'missing-train')}`, `/pureos/train/${id('trainScenario', 'missing-train-2')}`,
  '/proforma/studies', '/proforma/reference/corn', '/proforma/reference/cornstover',
  `/proforma/runs/${id('run', 'missing-run')}`, `/proforma/runs/${id('runCornstover', 'missing-run-2')}`,
  `/proforma/comparisons/${id('comparison', 'missing-comparison')}`,
  `/proforma/scenario/${id('scenario', 'missing-scenario')}`,
  '/runbooks/protocols', '/runbooks/depositions', '/runbooks/ledger',
  `/runbooks/${id('runbook', 'rb-missing')}`,
  `/runbooks/protocols/${id('protocol', 'missing-protocol')}`,
  `/runbooks/protocols/${id('protocol', 'missing-protocol')}/edit`,
  `/runbooks/depositions/${id('deposition', 'dep-missing')}`,
  '/primer/path', '/primer/practice', `/primer/${id('lesson', 'missing-lesson')}`,
  '/guild/matrix', '/guild/people', `/guild/people/${id('person', 'p-missing')}`, '/guild/skills', `/guild/skills/${id('skill', 'missing-skill')}`, '/guild/checks',
  '/catalogues/products', '/catalogues/skills', '/catalogues/lessons',
  '/flowsheets', `/flowsheets/${id('flowsheet', 'missing-flowsheet')}`, `/flowsheets/${id('flowsheetLibrary', 'missing-flowsheet-2')}`,
  '/settings', '/settings/appearance', '/settings/units', '/settings/corpus', '/settings/guild', '/settings/figures', '/settings/export', '/settings/about', '/settings/architecture',
];
// Full-screen takeovers, walked last (they hide the rail).
const TAKEOVERS = [
  `/runbooks/protocols/${id('protocol', 'missing-protocol')}/run/${id('protocolRun', 'dep-missing-run')}`,
  `/runbooks/depositions/${id('deposition', 'dep-missing')}/bench`,
  `/guild/checks/${id('check', 'chk-missing')}/run`,
];
const PATHS = [...RAIL, ...SECONDARY, ...TAKEOVERS];
const IGNORE = [/Download the React DevTools/i, /favicon/i];

const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--no-proxy-server'] });
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
if (state === 'stopped') {
  await context.route('**/api/**', (r) => r.abort('connectionrefused'));
}
// The reviewer name, so screens that gate on it open past the gate.
const results = [];
const prefix = `#/p/${encodeURIComponent(project)}`;
for (const path of PATHS) {
  const page = await context.newPage();
  const r = { path, console: [], pageErrors: [], failed: [], api4xx: [], boundary: null, notFound: false, chars: 0, leaks: [] };
  page.on('console', (m) => {
    if (m.type() === 'error' && !IGNORE.some((re) => re.test(m.text()))) r.console.push(m.text().slice(0, 300));
  });
  page.on('pageerror', (e) => r.pageErrors.push(String(e.message).slice(0, 300)));
  page.on('requestfailed', (q) => {
    if (state !== 'stopped' || !q.url().includes('/api/')) r.failed.push(`${q.method()} ${q.url().replace(origin, '')} ${q.failure()?.errorText}`);
  });
  page.on('response', (s) => {
    const u = s.url();
    if (u.startsWith(`${origin}/api/`) && s.status() >= 400) r.api4xx.push(`${s.status()} ${s.request().method()} ${u.slice(origin.length)}`);
  });
  try {
    await page.goto(`${origin}/${prefix}${path === '/' ? '' : path}`, { waitUntil: 'load', timeout: 60000 });
    await page.waitForTimeout(state === 'stopped' ? 3500 : 3000);
    // A project address reloads into the project once.
    await page.waitForLoadState('load');
    await page.waitForTimeout(500);
    if (await page.locator('[data-testid="screen-error"]').count()) r.boundary = (await page.locator('[data-testid="screen-error"]').first().innerText()).slice(0, 300);
    const text = await page.locator('body').innerText().catch(() => '');
    r.chars = text.trim().length;
    r.notFound = /Route not found/.test(text);
    r.address = await page.evaluate(() => window.location.hash);
    const anchors = await page.evaluate(() =>
      [...document.querySelectorAll('a[href]')].map((a) => ({ href: a.getAttribute('href'), text: (a.textContent || '').trim().slice(0, 60) })),
    );
    for (const a of anchors) {
      if (!a.href.startsWith('#')) continue;
      if (a.href === '#' || a.href.startsWith(prefix + '/') || a.href === prefix) continue;
      r.leaks.push(a);
    }
  } catch (e) {
    r.pageErrors.push(`walk: ${String(e).slice(0, 200)}`);
  }
  results.push(r);
  const bad = r.console.length + r.pageErrors.length + r.failed.length + (r.boundary ? 1 : 0) + (r.notFound ? 1 : 0);
  console.log(`${bad ? 'x' : '.'} ${state} ${path} chars=${r.chars} console=${r.console.length} errors=${r.pageErrors.length} failed=${r.failed.length} api4xx=${r.api4xx.length} leaks=${r.leaks.length}${r.boundary ? ' BOUNDARY' : ''}${r.notFound ? ' NOTFOUND' : ''}`);
  await page.close();
}
writeFileSync(out, JSON.stringify(results, null, 1));
await browser.close();
