/**
 * Route smoke test. Serves the production build, visits every route in the map,
 * and fails on console errors, uncaught exceptions, or an empty render.
 *
 *   pnpm build && node scripts/smoke.mjs
 */
import { chromium } from 'playwright';
import { createServer } from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { join, extname } from 'node:path';

const DIST = join(process.cwd(), 'dist');
const PORT = 4319;

const MIME = {
  '.html': 'text/html',
  '.js': 'text/javascript',
  '.css': 'text/css',
  '.svg': 'image/svg+xml',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.json': 'application/json',
};

const server = createServer(async (req, res) => {
  try {
    const url = decodeURIComponent((req.url ?? '/').split('?')[0]);
    let file = join(DIST, url === '/' ? 'index.html' : url);
    try {
      if ((await stat(file)).isDirectory()) file = join(file, 'index.html');
    } catch {
      file = join(DIST, 'index.html'); // SPA fallback
    }
    const body = await readFile(file);
    res.writeHead(200, { 'Content-Type': MIME[extname(file)] ?? 'application/octet-stream' });
    res.end(body);
  } catch (e) {
    res.writeHead(404).end('not found');
  }
});

const ROUTES = [
  ['/', 'Home'],
  ['/ask', 'Ask'],
  ['/library', 'Library'],
  ['/library/ingest', 'Ingest'],
  ['/library/papers/H4', 'Paper reader (P. pastoris precedent)'],
  ['/library/papers/D5', 'Paper reader (the open question, no records)'],
  ['/library/papers/O8m', 'Paper reader (industry estimates)'],
  ['/extract', 'Extract records'],
  ['/extract/review', 'Review queue'],
  ['/extract/validation', 'Validation dashboard'],
  ['/organisms', 'Organism index'],
  ['/organisms/cw15', 'Strain page (cw15)'],
  ['/organisms/creinhardtii-wt', 'Strain page (walled comparator)'],
  ['/organisms/bovine', 'Strain page (reference molecule)'],
  ['/molecules', 'Molecule index'],
  ['/molecules/taq-dna-polymerase', 'Molecule detail (Taq)'],
  ['/protocols', 'Protocol library'],
  ['/protocols/PR-TAP-01', 'Protocol detail'],
  ['/protocols/PR-TAP-01/edit', 'Protocol editor'],
  ['/protocols/PR-DISRUPT-01', 'Protocol detail (PEF disruption)'],
  ['/protocols/PR-PHOS-01', 'Protocol detail (Phos-tag assay)'],
  ['/runbooks', 'Runbook board'],
  ['/runbooks/rb-brazzein', 'Runbook (complete)'],
  ['/runbooks/rb-taq-kigali', 'Runbook (running)'],
  ['/simulate', 'Scenario index'],
  ['/simulate/sc-s1', 'Scenario S1'],
  ['/simulate/sc-s2', 'Scenario S2'],
  ['/simulate/sc-s3', 'Scenario S3 (the incumbent)'],
  ['/simulate/compare', 'Compare'],
  ['/learn', 'Learn map'],
  ['/learn/m0/l0-1', 'Lesson 0.1'],
  ['/learn/m0/l0-4', 'Lesson 0.4 (metrics)'],
  ['/settings/appearance', 'Settings — appearance'],
  ['/settings/units', 'Settings — units'],
  ['/settings/corpus', 'Settings — corpus'],
  ['/settings/export', 'Settings — export'],
  ['/settings/architecture', 'Architecture — the eighteen components'],
  ['/settings/about', 'Settings — colophon'],
];

const IGNORE = [/Download the React DevTools/i, /favicon/i];

async function main() {
  await new Promise((r) => server.listen(PORT, r));
  // Use the environment's pre-installed Chromium rather than downloading one;
  // its build number need not match the npm playwright version.
  const executablePath = process.env.CHROMIUM_PATH ?? '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
  const browser = await chromium.launch(
    existsSync(executablePath) ? { executablePath } : {},
  );
  const failures = [];

  for (const [route, label] of ROUTES) {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    const problems = [];
    page.on('console', (m) => {
      if (m.type() === 'error' && !IGNORE.some((re) => re.test(m.text()))) problems.push(m.text());
    });
    page.on('pageerror', (e) => problems.push(`UNCAUGHT: ${e.message}`));

    try {
      await page.goto(`http://localhost:${PORT}/#${route}`, { waitUntil: 'networkidle' });
      await page.waitForTimeout(900);
      const text = (await page.locator('body').innerText()).trim();
      if (text.length < 60) problems.push(`rendered only ${text.length} chars of text`);
      if (/Route not found/i.test(text)) problems.push('route did not resolve to a screen');
      const label_ = `${label.padEnd(30)} ${route}`;
      if (problems.length) {
        failures.push({ route, label, problems });
        console.log(`✗ ${label_}`);
        for (const p of problems.slice(0, 4)) console.log(`    ${p.slice(0, 220)}`);
      } else {
        console.log(`✓ ${label_} (${text.length} chars)`);
      }
    } catch (e) {
      failures.push({ route, label, problems: [String(e)] });
      console.log(`✗ ${label.padEnd(30)} ${route}\n    ${String(e).slice(0, 220)}`);
    }
    await page.close();
  }

  await browser.close();
  server.close();

  console.log(`\n${ROUTES.length - failures.length}/${ROUTES.length} routes clean`);
  if (failures.length) process.exit(1);
}

main();
