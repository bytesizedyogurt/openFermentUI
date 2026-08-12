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
  ['/', 'Bench'],
  ['/postdoc', 'Postdoc'],
  ['/trawl', 'Trawl'],
  ['/trawl/ingest', 'Ingest'],
  ['/trawl/review', 'Review queue'],
  ['/trawl/sources/H4', 'Source reader (P. pastoris precedent)'],
  ['/trawl/sources/D5', 'Source reader (the open question, no records)'],
  ['/trawl/sources/O8m', 'Source reader (industry estimates)'],
  ['/ledger', 'Ledger — parameter index'],
  ['/ledger/p/titer_secreted', 'Parameter page (contested)'],
  ['/ledger/p/expression_pct_tsp', 'Parameter page (contradicted)'],
  ['/ledger/p/kinase_identity', 'Parameter page (categorical)'],
  ['/ledger/records', 'Record table'],
  ['/ledger/contradictions', 'Contradiction queue'],
  ['/assay', 'Assay'],
  ['/geneos', 'geneOS index'],
  ['/geneos/cw15', 'Strain page (cw15)'],
  ['/geneos/creinhardtii-wt', 'Strain page (walled comparator)'],
  ['/geneos/bovine', 'Strain page (reference molecule)'],
  ['/runbook', 'Runbook'],
  ['/runbook/PR-TAP-01', 'Protocol detail'],
  ['/runbook/PR-TAP-01/edit', 'Protocol editor'],
  ['/runbook/PR-DISRUPT-01', 'Protocol detail (PEF disruption)'],
  ['/runbook/PR-PHOS-01', 'Protocol detail (Phos-tag assay)'],
  ['/fermos', 'fermOS index'],
  ['/fermos/s/sc-s1', 'Scenario S1'],
  ['/fermos/s/sc-s2', 'Scenario S2'],
  ['/fermos/s/sc-s3', 'Scenario S3 (the incumbent)'],
  ['/fermos/compare', 'Compare'],
  ['/parchment', 'Parchment'],
  ['/openlab', 'openLab'],
  ['/notary', 'Notary (not built)'],
  ['/learn', 'Learn map'],
  ['/learn/m0/l0-1', 'Lesson 0.1'],
  ['/learn/m0/l0-4', 'Lesson 0.4 (metrics)'],
  ['/settings/appearance', 'Settings — appearance'],
  ['/settings/units', 'Settings — units'],
  ['/settings/corpus', 'Settings — corpus'],
  ['/settings/export', 'Settings — export'],
  ['/settings/about', 'Settings — colophon'],
  // Aliases are permanent (OF-FE-003 §6.1) — a deep link from docs, the tour or
  // an old bookmark must still land somewhere real.
  ['/library', 'ALIAS library -> trawl'],
  ['/library/papers/H4', 'ALIAS library/papers -> trawl/sources'],
  ['/extract', 'ALIAS extract -> ledger'],
  ['/extract/validation', 'ALIAS extract/validation -> assay'],
  ['/organisms/cw15', 'ALIAS organisms -> geneos'],
  ['/simulate', 'ALIAS simulate -> fermos'],
  ['/ask', 'ALIAS ask -> postdoc'],
  ['/protocols/PR-TAP-01', 'ALIAS protocols -> runbook'],
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
