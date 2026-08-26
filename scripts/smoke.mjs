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
  // ── the eleven, in rail order ────────────────────────────────────────
  ['/intake', 'Intake'],
  ['/intake/ingest', 'Intake — ingest board'],
  ['/biorepo', 'BioRepo'],
  ['/biorepo/paper/H4', 'BioRepo — paper (P. pastoris precedent)'],
  ['/biorepo/paper/D5', 'BioRepo — paper (the open question, no records)'],
  ['/biorepo/paper/O8m', 'BioRepo — paper (industry estimates)'],
  ['/biorepo/compare', 'BioRepo — compare'],
  ['/biorepo/witness', 'BioRepo — Witness'],
  ['/postdoc', 'Postdoc'],
  ['/geneos', 'geneOS — Hosts is the default view'],
  ['/geneos/hosts', 'geneOS — hosts (the strain catalogue)'],
  ['/geneos/hosts/cw15', 'geneOS — strain page (cw15)'],
  ['/geneos/hosts/creinhardtii-wt', 'geneOS — strain (walled comparator)'],
  ['/geneos/hosts/bovine', 'geneOS — strain (reference molecule)'],
  ['/geneos/pathway', 'geneOS — pathway vocabulary'],
  ['/fermos', 'fermOS (the emptiest of the eleven)'],
  ['/pureos', 'pureOS'],
  ['/proforma', 'Proforma'],
  ['/proforma/scenario/sc-s1', 'Proforma — scenario S1'],
  ['/proforma/scenario/sc-s2', 'Proforma — scenario S2'],
  ['/proforma/scenario/sc-s3', 'Proforma — scenario S3 (the incumbent)'],
  ['/runbooks', 'Runbooks'],
  ['/runbooks/rb-brazzein', 'Runbooks — complete'],
  ['/runbooks/rb-taq-kigali', 'Runbooks — running'],
  ['/runbooks/protocols', 'Runbooks — protocols'],
  ['/runbooks/protocols/PR-TAP-01', 'Runbooks — protocol detail'],
  ['/runbooks/protocols/PR-TAP-01/edit', 'Runbooks — protocol editor'],
  ['/runbooks/protocols/PR-DISRUPT-01', 'Runbooks — protocol (PEF disruption)'],
  ['/runbooks/protocols/PR-PHOS-01', 'Runbooks — protocol (Phos-tag assay)'],
  ['/runbooks/depositions', 'Runbooks — depositions (empty in a fresh browser)'],
  ['/runbooks/depositions/dep-not-in-this-session', 'Runbooks — deposition (absent here)'],
  ['/dominion', 'Dominion'],
  ['/dominion/molecules', 'Dominion — molecules'],
  ['/dominion/molecules/taq-dna-polymerase', 'Dominion — molecule (Taq)'],
  ['/dominion/clearance', 'Dominion — clearance'],
  ['/primer', 'Primer'],
  ['/primer/l0-1', 'Primer — lesson 0.1'],
  ['/primer/l0-4', 'Primer — lesson 0.4 (metrics)'],
  ['/primer/m0/l0-1', 'Primer — lesson by module and id'],
  ['/guild', 'Guild'],
  // ── not rail entries, reachable from Home ────────────────────────────
  ['/settings/appearance', 'Settings — appearance'],
  ['/settings/units', 'Settings — units'],
  ['/settings/corpus', 'Settings — corpus'],
  ['/settings/export', 'Settings — export'],
  ['/settings/architecture', 'Architecture — the map of the eleven'],
  ['/settings/about', 'Settings — colophon'],
];

/**
 * Old path → where it must land (OF-BLD-006 §8).
 *
 * Checked as landings rather than as routes: a redirect that renders is not
 * enough, because the interstitial renders too. The URL has to have moved and
 * the deep-link tail has to have survived, or a bookmark to a specific paper
 * silently becomes a bookmark to the top of the corpus.
 */
const REDIRECTS = [
  // ── OF-BLD-011: the strain catalogue moved from fermOS to geneOS ─────
  ['/fermos/organisms', '/geneos/hosts'],
  ['/fermos/organisms/cw15', '/geneos/hosts/cw15'],
  // ── OF-BLD-008: the five that stopped being destinations ─────────────
  // Re-aimed at the current home rather than chained through the old one.
  ['/organisms', '/geneos/hosts'],
  ['/organisms/cw15', '/geneos/hosts/cw15'],
  ['/molecules', '/dominion/molecules'],
  ['/molecules/taq-dna-polymerase', '/dominion/molecules/taq-dna-polymerase'],
  ['/protocols', '/runbooks/protocols'],
  ['/protocols/PR-TAP-01', '/runbooks/protocols/PR-TAP-01'],
  ['/witness', '/biorepo/witness'],
  ['/depositions', '/runbooks/depositions'],
  // ── moved between owners ─────────────────────────────────────────────
  ['/biorepo/papers/H4', '/biorepo/paper/H4'],
  ['/biorepo/ingest', '/intake/ingest'],
  ['/proforma/compare', '/biorepo/compare'],
  ['/proforma/sc-s2', '/proforma/scenario/sc-s2'],
  // ── OF-BLD-006 legacy, re-aimed rather than chained ──────────────────
  ['/ask', '/postdoc'],
  ['/library', '/biorepo'],
  ['/library/papers/H4', '/biorepo/paper/H4'],
  ['/library/ingest', '/intake/ingest'],
  ['/extract', '/intake'],
  ['/extract/review', '/guild'],
  ['/extract/validation', '/biorepo/witness'],
  ['/simulate', '/proforma'],
  ['/simulate/compare', '/biorepo/compare'],
  ['/simulate/sc-s2', '/proforma/scenario/sc-s2'],
  ['/learn', '/primer'],
  ['/learn/m0/l0-1', '/primer/l0-1'],
  ['/review', '/guild'],
  ['/validation', '/biorepo/witness'],
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

  // ── §8 — old paths land on the new screens ─────────────────────────
  let redirectFails = 0;
  for (const [from, to] of REDIRECTS) {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    try {
      await page.goto(`http://localhost:${PORT}/#${from}`, { waitUntil: 'networkidle' });
      await page.waitForTimeout(700);
      const landed = decodeURIComponent(page.url().split('#')[1] ?? '');
      const text = (await page.locator('body').innerText()).trim();
      const ok = landed === to && !/Route not found/i.test(text) && text.length > 60;
      if (ok) {
        console.log(`✓ ${from.padEnd(28)} → ${to}`);
      } else {
        redirectFails++;
        console.log(`✗ ${from.padEnd(28)} → ${landed || '(nowhere)'}, expected ${to}`);
      }
    } catch (e) {
      redirectFails++;
      console.log(`✗ ${from.padEnd(28)} ${String(e).slice(0, 160)}`);
    }
    await page.close();
  }

  // ── OF-BLD-010 — the reference shelf renders, and a stub still reads as one
  //
  // Two things have to be true together on every owner with subsystems, and
  // checking either alone would miss the failure that matters: the domain
  // content is on screen, AND the screen still says the code is not built. A
  // shelf that quietly replaced the "not built" statement would look like a
  // working subsystem, which is the exact confusion the divider exists to stop.
  const SHELVES = [
    ['/geneos', 'geneOS subsystems', 'EC top-level classes'],
    ['/pureos', 'pureOS subsystems', 'Loss mechanisms'],
    ['/fermos', 'fermOS subsystems', 'Kinetic models'],
    ['/dominion', 'Dominion subsystems', 'Limitation kinds'],
    ['/intake', 'Intake subsystems', 'Parse status ladder'],
    ['/biorepo', 'BioRepo subsystems', 'Provenance levels'],
    ['/proforma', 'Proforma subsystems', 'Uncertain inputs'],
  ];
  let shelfFails = 0;
  for (const [route, heading, table] of SHELVES) {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    try {
      await page.goto(`http://localhost:${PORT}/#${route}`, { waitUntil: 'networkidle' });
      await page.waitForTimeout(800);
      const text = await page.locator('body').innerText();
      const problems = [];
      if (!text.includes(heading)) problems.push(`no "${heading}" section`);
      if (!text.includes(table)) problems.push(`reference table "${table}" not rendered`);
      if (!/not built/i.test(text)) problems.push('nothing on the page says "not built"');
      if (!/has no implementation/i.test(text)) problems.push('no subsystem states it is unimplemented');
      // The divider's label is the sentence that separates the two kinds of claim.
      if (!/what the field looks like, not what your answer would be/i.test(text)) {
        problems.push('the reference divider and its label are missing');
      }
      if (problems.length) {
        shelfFails++;
        console.log(`✗ shelf ${route.padEnd(12)} ${problems.join('; ')}`);
      } else {
        console.log(`✓ shelf ${route.padEnd(12)} content below the line, "not built" above it`);
      }
    } catch (e) {
      shelfFails++;
      console.log(`✗ shelf ${route.padEnd(12)} ${String(e).slice(0, 140)}`);
    }
    await page.close();
  }

  // ── OF-BLD-011 §2 — a seeded subsystem carries its reference on its own
  //    view, and must NOT appear on the shelf under a "no implementation"
  //    heading.
  //
  // Both halves matter. Hosts showing its chassis table proves the reference
  // survived the move to geneOS; Hosts being absent from the shelf proves the
  // shelf did not start calling a live catalogue of strains unbuilt.
  const SEEDED = [
    ['/geneos/hosts', 'Chassis trade-offs', 'Hosts has no implementation'],
    ['/geneos/pathway', 'Precursor pathways', 'Pathway has no implementation'],
  ];
  let seededFails = 0;
  for (const [route, table, mustNotSay] of SEEDED) {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    try {
      await page.goto(`http://localhost:${PORT}/#${route}`, { waitUntil: 'networkidle' });
      await page.waitForTimeout(800);
      const text = await page.locator('body').innerText();
      const problems = [];
      if (!text.includes(table)) problems.push(`reference table "${table}" not rendered`);
      if (text.includes(mustNotSay)) problems.push(`shelf claims "${mustNotSay}" for a seeded subsystem`);
      if (!/what the field looks like, not what your answer would be/i.test(text)) {
        problems.push('the reference divider and its label are missing');
      }
      if (problems.length) {
        seededFails++;
        console.log(`✗ seeded ${route.padEnd(17)} ${problems.join('; ')}`);
      } else {
        console.log(`✓ seeded ${route.padEnd(17)} reference below the line, not on the shelf`);
      }
    } catch (e) {
      seededFails++;
      console.log(`✗ seeded ${route.padEnd(17)} ${String(e).slice(0, 140)}`);
    }
    await page.close();
  }

  await browser.close();
  server.close();

  console.log(`\n${ROUTES.length - failures.length}/${ROUTES.length} routes clean`);
  console.log(`${SHELVES.length - shelfFails}/${SHELVES.length} reference shelves render beneath a "not built" statement`);
  console.log(`${SEEDED.length - seededFails}/${SEEDED.length} seeded subsystems carry reference without a "not built" claim`);
  console.log(`${REDIRECTS.length - redirectFails}/${REDIRECTS.length} redirects land on the new screen`);
  if (failures.length || redirectFails || shelfFails || seededFails) process.exit(1);
}

main();
