/**
 * Route smoke test. Serves the production build, visits every route in the map,
 * and fails on console errors, uncaught exceptions, or an empty render.
 *
 * Every route runs with archived programs HIDDEN, the default (OF-BLD-016
 * §2.2): casein and PHA leave every list, and a deep link to one of their
 * papers, strains or scenarios still opens, under the banner naming its
 * program. The flows after the routes that exercise the B5 overlay, the
 * review queue and the PHA model turn the switch on first (`setShowArchived`),
 * because their fixtures sit on archived papers (OF-BLD-016 B.4, D1); the
 * golden path walks with it on throughout.
 *
 *   pnpm build && node scripts/smoke.mjs
 */
import { chromium } from 'playwright';
import { request as httpRequest } from 'node:http';
import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { LOOPBACK } from './lib/serve-dist.mjs';
import { createServiceDouble } from './lib/service-double.mjs';

const DIST = join(process.cwd(), 'dist');
const PORT = 4319;

/** The person the smoke reviews as. `biorepo.write` refuses a placeholder (F2). */
const REVIEWER = 'Sam Okonkwo';

// The service double (scripts/lib/service-double.mjs), shared with the golden path.
const { server, state: doubleState } = createServiceDouble({ dist: DIST });
const { decisions, checks, guildPosts, practicePosts } = doubleState;

const ROUTES = [
  ['/', 'Home'],
  // ── the eleven, in rail order ────────────────────────────────────────
  ['/intake', 'Intake'],
  ['/intake/ingest', 'Intake — ingest board'],
  ['/biorepo', 'BioRepo'],
  ['/biorepo/paper/H4', 'BioRepo — paper (P. pastoris precedent)'],
  ['/biorepo/paper/D5', 'BioRepo — paper (the open question, no records)'],
  ['/biorepo/paper/O8m', 'BioRepo — paper (industry estimates)'],
  ['/biorepo/paper/B5', 'BioRepo — paper (full text from the overlay)'],
  ['/biorepo/compare', 'BioRepo — compare'],
  ['/biorepo/witness', 'BioRepo — Witness'],
  ['/biorepo/search', 'BioRepo — search the papers'],
  ['/biorepo/artifacts', 'BioRepo — artifacts (what was computed)'],
  ['/biorepo/artifacts/02aef8a9e9cbaf88', 'BioRepo — one artifact, its basis and replay'],
  ['/postdoc', 'Postdoc'],
  ['/geneos', 'geneOS — Hosts is the default view'],
  ['/geneos/hosts', 'geneOS — hosts (the strain catalogue)'],
  ['/geneos/hosts/cw15', 'geneOS — strain page (cw15)'],
  ['/geneos/hosts/creinhardtii-wt', 'geneOS — strain (walled comparator)'],
  ['/geneos/hosts/bovine', 'geneOS — strain (reference molecule)'],
  ['/geneos/hosts/c-necator-h16', 'geneOS — strain (thread P host)'],
  ['/geneos/pathway', 'geneOS — pathway vocabulary'],
  ['/geneos/model', 'geneOS — Model: the ceiling beside what was reported'],
  ['/fermos', 'fermOS — Fits'],
  ['/fermos/forecast', 'fermOS — Forecast'],
  // OF-BLD-020 §3.3 — a model family simulated from its sources.
  ['/fermos/simulate', 'fermOS — Simulate'],
  // OF-BLD-020 §4.2 — the vessel BioSTEAM designs for a kept simulation.
  ['/fermos/vessel', 'fermOS — Vessel'],
  ['/pureos', 'pureOS'],
  // OF-BLD-019 §4.1 — the train of the run Proforma priced, by scenario; PHA's, so under its banner.
  ['/pureos/train/sc-pha-1', 'pureOS — train of a run, unit by unit'],
  ['/proforma', 'Proforma'],
  ['/proforma/scenario/sc-s1', 'Proforma — scenario S1'],
  ['/proforma/scenario/sc-s2', 'Proforma — scenario S2'],
  ['/proforma/scenario/sc-s3', 'Proforma — scenario S3 (the incumbent)'],
  ['/proforma/scenario/sc-pha-1', 'Proforma — BioSTEAM scenario (draft PHA flowsheet)'],
  // OF-BLD-019 §3.3 — the yeast program's shipped scenario, and the two reference biorefineries' pages.
  ['/proforma/scenario/sc-yeast-1', 'Proforma — BioSTEAM scenario (glucose to ethanol)'],
  ['/proforma/reference/cornstover_benchmark', 'Proforma — reference (corn stover benchmark)'],
  ['/proforma/reference/corn_drygrind', 'Proforma — reference (dry-grind corn ethanol)'],
  ['/runbooks', 'Runbooks'],
  ['/runbooks/rb-brazzein', 'Runbooks — complete'],
  ['/runbooks/rb-taq-kigali', 'Runbooks — running'],
  ['/runbooks/protocols', 'Runbooks — protocols'],
  ['/runbooks/protocols/PR-TAP-01', 'Runbooks — protocol detail'],
  ['/runbooks/protocols/PR-TAP-01/edit', 'Runbooks — protocol editor'],
  ['/runbooks/protocols/PR-DISRUPT-01', 'Runbooks — protocol (PEF disruption)'],
  ['/runbooks/protocols/PR-PHOS-01', 'Runbooks — protocol (Phos-tag assay)'],
  ['/runbooks/depositions', 'Runbooks — depositions (empty in a fresh browser)'],
  ['/runbooks/ledger', 'Runbooks — prediction ledger'],
  ['/runbooks/depositions/dep-not-in-this-session', 'Runbooks — deposition (absent here)'],
  ['/dominion', 'Dominion'],
  ['/dominion/molecules', 'Dominion — molecules'],
  ['/dominion/molecules/taq-dna-polymerase', 'Dominion — molecule (Taq)'],
  ['/dominion/clearance', 'Dominion — clearance'],
  ['/primer', 'Primer'],
  ['/primer/l0-1', 'Primer — lesson 0.1'],
  ['/primer/l0-4', 'Primer — lesson 0.4 (metrics)'],
  ['/primer/m0/l0-1', 'Primer — lesson by module and id'],
  // OF-BLD-013 §3 — a lesson that counts toward skills, and a path with nobody on the ledger.
  ['/primer/l6-1', 'Primer — bench lesson'],
  ['/primer/path', 'Primer — my path (empty ledger)'],
  ['/primer/practice', 'Primer — practice'],
  ['/guild', 'Guild'],
  // OF-BLD-013 — the competence ledger, empty in a fresh browser.
  ['/guild/matrix', 'Guild — matrix (empty ledger)'],
  ['/guild/people', 'Guild — people (empty ledger)'],
  ['/guild/skills', 'Guild — skills'],
  ['/guild/checks', 'Guild — checks (empty ledger)'],
  ['/guild/checks/ck-nothing/run', 'Guild — bench check (nothing to run)'],
  ['/guild/skills/SK-CIP', 'Guild — skill page'],
  ['/guild/people/p-nobody', 'Guild — person (absent here)'],
  // ── not rail entries, reachable from Home ────────────────────────────
  ['/settings/appearance', 'Settings — appearance'],
  // OF-BLD-016 §2.2 — the programs, and the one switch that shows archived ones.
  ['/settings/programs', 'Settings — programs and the archive switch'],
  ['/settings/units', 'Settings — units'],
  ['/settings/corpus', 'Settings — corpus'],
  ['/settings/figures', 'Settings — the figure grammar'],
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
  // OF-BLD-019 §3.3 — the benchmark's old paths land on its reference page.
  ['/proforma/benchmark', '/proforma/reference/cornstover_benchmark'],
  ['/proforma/biosteam', '/proforma/reference/cornstover_benchmark'],
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

/**
 * Move Settings → Programs' switch to `on` in this page's store, and wait out
 * the Durable tier's debounce so a reload keeps it. Each `browser.newPage()`
 * is a fresh context, so a page starts with archived programs hidden.
 */
async function setShowArchived(page, on) {
  await page.goto(`http://localhost:${PORT}/#/settings/programs`, { waitUntil: 'networkidle' });
  const sw = page.locator('[data-testid="show-archived"]');
  await sw.waitFor({ timeout: 8000 });
  if ((await sw.isChecked()) !== on) await (on ? sw.check() : sw.uncheck()).catch(() => {});
  await page
    .waitForFunction((want) => document.querySelector('[data-testid="show-archived"]')?.checked === want, on, { timeout: 4000 })
    .catch(() => {});
  await page.waitForTimeout(600);
  return (await sw.isChecked()) === on;
}

/**
 * Type a person's value into the parameter panel's row for `key`
 * (OF-BLD-020 §2.2), with its low, its high and what it rests on when given:
 * the panel keeps each as an Override under the reviewer name.
 */
async function typeParam(page, key, value, { low = null, high = null, note = null } = {}) {
  const row = page.locator(`[data-testid="param-row"][data-key="${key}"]`);
  await row.waitFor({ timeout: 8000 }).catch(() => {});
  await row.locator('[data-testid="param-value-input"]').fill(String(value));
  if (low !== null || high !== null || note !== null) {
    const more = row.locator('[data-testid="param-more"]');
    if (!(await more.evaluate((d) => d.open).catch(() => false))) await more.locator('summary').click();
    if (low !== null) await row.locator('[data-testid="param-low-input"]').fill(String(low));
    if (high !== null) await row.locator('[data-testid="param-high-input"]').fill(String(high));
    if (note !== null) await row.locator('[data-testid="param-note-input"]').fill(note);
  }
  await page.waitForTimeout(150);
}

/** The source chip of the panel's row for `key`: its origin and its words. */
async function chipOf(page, key) {
  const chip = page.locator(`[data-testid="param-row"][data-key="${key}"] [data-testid="param-chip"]`).first();
  return { origin: await chip.getAttribute('data-origin', { timeout: 3000 }).catch(() => null), text: (await chip.innerText({ timeout: 3000 }).catch(() => '')).replace(/\s+/g, ' ') };
}

async function main() {
  await new Promise((r) => server.listen(PORT, LOOPBACK, r));

  // §6.9 — the static handler is confined to dist/. Every script that serves
  // the build shares it, the offline demo included, and `join(DIST, url)`
  // used to collapse `..`: a request for /../core/.env read the key off the
  // disk of whoever was running the demo. Sent raw — `fetch` would normalise
  // the path away before it left — and every shape has to come back 404.
  const rawGet = (path) =>
    new Promise((resolve, reject) => {
      const rq = httpRequest({ host: LOOPBACK, port: PORT, path, method: 'GET' }, (rs) => {
        rs.resume();
        rs.on('end', () => resolve(rs.statusCode));
      });
      rq.on('error', reject);
      rq.end();
    });
  const OUTSIDE = ['/../package.json', '/%2e%2e/core/.env.example', '/../../etc/passwd', '/assets/../../package.json'];
  let confineFails = 0;
  for (const path of OUTSIDE) {
    const status = await rawGet(path);
    if (status !== 404) {
      confineFails++;
      console.log(`✗ confined     ${path} answered ${status}, not 404 — the static server left dist/`);
    }
  }
  if (!confineFails) console.log(`✓ confined     ${OUTSIDE.length} requests outside dist/ refused`);

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
    // OF-BLD-020 §4.2 — transport is live, so its table moved to the Vessel
    // view (SEEDED below); control is still a stub on the shelf.
    ['/fermos', 'fermOS subsystems', 'Measured online'],
    ['/dominion', 'Dominion subsystems', 'Limitation kinds'],
    ['/intake', 'Intake subsystems', 'Parse status ladder'],
    ['/biorepo', 'BioRepo subsystems', 'Provenance levels'],
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
    // §8.4 — Uncertainty is live: its reference stays on Proforma, off any shelf.
    ['/proforma', 'Uncertain inputs', 'Uncertainty has no implementation'],
    // OF-BLD-020 §4.2 — transport and scale are live: their reference stays on fermOS → Vessel, off the shelf.
    ['/fermos/vessel', 'Oxygen transfer', 'Transport has no implementation'],
    ['/fermos/vessel', 'Scale-up criteria', 'Scale has no implementation'],
    // OF-BLD-020 §8.R (finding 7) — operating mode is live: its reference sits on fermOS → Simulate, where the mode is chosen.
    ['/fermos/simulate', 'Operating modes', 'Operating mode has no implementation'],
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

  // ── OF-BLD-016 §2.2 — casein and PHA leave the default view, a link to
  //    one of their papers opens under a banner, and the switch brings them
  //    back.
  //
  // In a fresh browser the switch is off: Settings lists the three programs
  // with their status, the strain catalogue holds no casein or PHA host,
  // BioRepo says how many papers it hides and whose, Intake's table and
  // Proforma's index are empty and say why, and geneOS → Model has nothing for an active program
  // on the double's shelf. A deep link to H4 (casein) opens under the banner;
  // Q1 (yeast) opens without one. Then the switch goes on, in the same page,
  // and cw15 is back on the catalogue.
  let programFails = 0;
  {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    const problems = [];
    page.on('pageerror', (e) => problems.push(`page error: ${e.message}`));
    const goTo = async (route, ready) => {
      await page.goto(`http://localhost:${PORT}/#${route}`, { waitUntil: 'networkidle' });
      if (ready) await page.locator(ready).first().waitFor({ timeout: 8000 }).catch(() => {});
      await page.waitForTimeout(500);
    };
    try {
      await goTo('/settings/programs', '[data-testid="settings-programs"]');
      const status = await page
        .locator('[data-program-status]')
        .evaluateAll((els) => els.map((e) => `${e.getAttribute('data-program')}:${e.getAttribute('data-program-status')}`).join());
      if (status !== 'yeast:active,casein:archived,pha:archived') problems.push(`Settings → Programs lists ${status || 'nothing'}`);
      if (await page.locator('[data-testid="show-archived"]').isChecked()) problems.push('the archive switch is on in a fresh browser');
      // OF-BLD-016 §3.3 — the one switch also shows the examples, and says so.
      if (!/Show archived programs and examples/.test(await page.locator('[data-testid="settings-programs"]').innerText().catch(() => '')))
        problems.push('the switch is not labelled as showing examples too');
      if ((await page.locator('[data-testid="show-archived-examples"]').count()) !== 1) problems.push('Settings → Programs does not say the switch shows the examples');

      await goTo('/geneos/hosts', 'a[href="#/geneos/hosts/s-cerevisiae-s288c"]');
      if ((await page.locator('a[href="#/geneos/hosts/s-cerevisiae-s288c"]').count()) === 0) problems.push('the yeast host is not on the catalogue');
      for (const id of ['cw15', 'c-necator-h16']) {
        if ((await page.locator(`a[href="#/geneos/hosts/${id}"]`).count()) !== 0) problems.push(`the archived host ${id} is on the catalogue with the switch off`);
      }

      await goTo('/biorepo', '[data-testid="archived-hidden"]');
      const hiddenLine = await page.locator('[data-testid="archived-hidden"]').first().innerText().catch(() => '');
      if (!/papers in Casein and PHA are\s+hidden/.test(hiddenLine)) problems.push(`BioRepo does not say which papers it hides: ${JSON.stringify(hiddenLine)}`);
      if ((await page.locator('a[href^="#/biorepo/paper/H4"]').count()) !== 0) problems.push('BioRepo lists the casein paper H4 with the switch off');

      await goTo('/intake');
      if (!/Every record here is in an archived program/.test(await page.locator('main').innerText().catch(() => '')))
        problems.push('Intake does not say its records are all in archived programs');

      await goTo('/proforma', '[data-testid="hidden-by-archive"]');
      if (!/Casein and PHA/.test(await page.locator('[data-testid="hidden-by-archive"]').innerText().catch(() => '')))
        problems.push('Proforma does not say its scenarios are in archived programs');
      if ((await page.locator('a[href="#/proforma/scenario/sc-s1"]').count()) !== 0) problems.push('Proforma lists a casein scenario with the switch off');

      await goTo('/', '[data-testid="home-programs-archived"]');
      if (!/Casein[\s\S]*PHA/.test(await page.locator('[data-testid="home-programs-archived"]').innerText().catch(() => '')))
        problems.push('Home does not name the archived programs in one line');

      await goTo('/geneos/model', 'main >> text=/No model on the shelf/');
      if (!/No model on the shelf computes for an active program/.test(await page.locator('main').innerText().catch(() => '')))
        problems.push('geneOS → Model does not say the shelf has nothing for an active program');

      await goTo('/biorepo/paper/H4', '[role="note"][data-archived-program]');
      if ((await page.locator('[role="note"][data-archived-program="casein"]').count()) !== 1) problems.push('a deep link to H4 does not open under the casein banner');
      if (!/belongs to Casein, an archived program/.test(await page.locator('main').innerText().catch(() => ''))) problems.push('the banner does not name the program');
      await goTo('/biorepo/paper/Q1');
      if ((await page.locator('[data-archived-program]').count()) !== 0) problems.push('a yeast paper opens under an archive banner');

      // OF-BLD-016 §3.3 — the seed runbooks are examples: the board, the
      // ledger and Home say so and name the next step, and a deep link opens
      // one under the same banner, which says it describes a run nobody made.
      await goTo('/runbooks', '[data-testid="runbooks-empty"]');
      const board = await page.locator('[data-testid="runbooks-empty"]').innerText().catch(() => '');
      if (!/seed runbooks are examples/.test(board) || !/Next step/.test(board) || !/Postdoc/.test(board))
        problems.push(`the empty runbook board does not say the seed runbooks are examples and name the next step: ${JSON.stringify(board.slice(0, 200))}`);
      if ((await page.locator('a[href="#/runbooks/rb-taq-kigali"]').count()) !== 0) problems.push('the board lists an example runbook with the switch off');
      await goTo('/runbooks/ledger', '[data-testid="ledger-examples-hidden"]');
      const ledger = await page.locator('[data-testid="ledger-examples-hidden"]').innerText().catch(() => '');
      if (!/locked runbooks are examples/.test(ledger) || !/Next step/.test(ledger)) problems.push('the empty ledger does not say its locked runbooks are examples and name the next step');
      await goTo('/runbooks/depositions');
      if (!/ask Postdoc to draft a runbook/.test(await page.locator('main').innerText().catch(() => ''))) problems.push('the empty deposition list does not name the next step');
      await goTo('/', '[data-testid="home-predictions"]');
      if ((await page.locator('[data-testid="home-predictions-examples"]').count()) !== 1) problems.push('Home\u2019s predictions card does not say the locked runbooks are examples');
      await goTo('/runbooks/rb-taq-kigali', '[role="note"][data-example="true"]');
      if (!/This runbook is an example/.test(await page.locator('main').innerText().catch(() => ''))) problems.push('a deep link to an example runbook does not open under the banner saying so');
      if ((await page.locator('[role="note"][data-archived-program]').count()) !== 0) problems.push('an example runbook of no archived program names one');

      if (!(await setShowArchived(page, true))) problems.push('the archive switch did not turn on');
      await goTo('/runbooks', 'a[href="#/runbooks/rb-taq-kigali"]');
      if ((await page.locator('a[href="#/runbooks/rb-taq-kigali"]').count()) === 0) problems.push('turning the switch on did not bring the example runbooks back');
      await goTo('/geneos/hosts', 'a[href="#/geneos/hosts/cw15"]');
      if ((await page.locator('a[href="#/geneos/hosts/cw15"]').count()) === 0) problems.push('turning the switch on did not bring cw15 back to the catalogue');
      await goTo('/biorepo');
      if ((await page.locator('[data-testid="archived-hidden"]').count()) !== 0) problems.push('BioRepo still says papers are hidden with the switch on');
    } catch (e) {
      problems.push(String(e).slice(0, 160));
    }
    if (problems.length) {
      programFails++;
      console.log(`✗ programs     ${problems.join('; ')}`);
    } else {
      console.log('✓ programs     Settings lists yeast active, casein and PHA archived; with the switch off no casein or PHA host, paper or scenario is listed and each list says what it hides; the example runbooks leave the board, the ledger and Home, each naming the next step, and rb-taq-kigali opens under the example banner; H4 opens under the casein banner and Q1 under none; the switch brings cw15 and the runbooks back');
    }
    await page.close();
  }

  // ── OF-BLD-019 §3.1 — Proforma's index shows the shelf and the reference
  //    runs, and New scenario makes a scenario that opens on its page.
  //
  // The double's shelf is the one demo.py --prototype generates from
  // flowsheets/shelf.py, with the switch off and on. Off, every reference on
  // it has a card that says it has not run and offers a run beside the
  // simulator's status line, the Flowsheets row and the chooser offer every
  // other flowsheet on it (and say why when there is none), and New scenario
  // is never disabled. Each flowsheet offered with the switch off makes a
  // scenario that lands on its page. On, pha_sugar_v0 is offered: New
  // scenario from it makes a PHA scenario that lands on its page, which says
  // it has not run; the index lists it as not run, and it survives a reload,
  // as does a deep link to it. The palette opens the same chooser.
  let proformaFails = 0;
  {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    const problems = [];
    page.on('pageerror', (e) => problems.push(`page error: ${e.message}`));
    const fixture = (name) => JSON.parse(readFileSync(join(process.cwd(), 'core/tests/fixtures/prototype', name), 'utf8')).response;
    const ids = (sel) => page.locator(sel).evaluateAll((els) => els.map((e) => e.getAttribute('data-flowsheet')).join());
    const make = async (flowsheetId, name) => {
      await page.locator(`[data-testid="new-scenario-flowsheet"][data-flowsheet="${flowsheetId}"] input`).check();
      await page.locator('[data-testid="new-scenario-name"]').fill(name);
      await page.locator('[data-testid="new-scenario-create"]').click();
      // The page's own card (the index's cards carry the same test id), drawn
      // once the service has said it holds no run of the scenario (§3.R).
      await page.locator('[data-testid="proforma-biosteam"] [data-testid="scenario-not-run"]').waitFor({ timeout: 8000 }).catch(() => {});
      const made = /#\/proforma\/scenario\/(sc-[^/?]+)$/.exec(page.url())?.[1] ?? null;
      const said = await page.locator('main').innerText().catch(() => '');
      if (!made) problems.push(`New scenario on ${flowsheetId} did not land on a scenario page (${page.url()})`);
      else if (!/This scenario has not run yet/.test(said) || !said.includes(name)) problems.push(`the page of the scenario made on ${flowsheetId} does not say it has not run`);
      return made;
    };
    try {
      const off = fixture('proforma-shelf.json');
      const on = fixture('proforma-shelf-archived.json');
      const startsOff = off.filter((f) => !f.reference).map((f) => f.id);
      await page.goto(`http://localhost:${PORT}/#/proforma`, { waitUntil: 'networkidle' });
      await page.locator('[data-testid="reference-status"]').first().waitFor({ timeout: 8000 }).catch(() => {});
      await page.waitForTimeout(300);
      const refs = await ids('[data-testid="reference-card"]');
      if (refs !== off.filter((f) => f.reference).map((f) => f.id).join()) problems.push(`the Reference runs row lists ${refs || 'nothing'}`);
      for (const f of off.filter((x) => x.reference)) {
        const card = page.locator(`[data-testid="reference-card"][data-flowsheet="${f.id}"]`);
        // Each card asks for its own newest run: wait for its answer before reading it.
        await card.locator('[data-testid="reference-not-run"], [data-testid="reference-result"]').first().waitFor({ timeout: 8000 }).catch(() => {});
        const text = await card.innerText().catch(() => '');
        if (!text.includes(f.title) || !/Not run on this service yet|Ran\s+\d{4}-/.test(text)) problems.push(`the reference card for ${f.id} does not name it and its newest run`);
        if (!(await card.locator('[data-testid="reference-run"]').isEnabled().catch(() => false))) problems.push(`the reference card for ${f.id} offers no run`);
        if (!/The simulator (has not started|is starting|is warm|failed)/.test(await card.locator('[data-testid="reference-status"]').innerText().catch(() => '')))
          problems.push(`the reference card for ${f.id} has no status line`);
      }
      const rows = await ids('[data-testid="flowsheet-card"]');
      if (rows !== startsOff.join()) problems.push(`the Flowsheets row lists ${rows || 'nothing'}, not ${startsOff.join() || 'nothing'}`);
      if (startsOff.length === 0 && !/Glucose to ethanol, the yeast program\u2019s own flowsheet, is still to be added/.test(await page.locator('[data-testid="flowsheets"]').innerText().catch(() => '')))
        problems.push('the empty Flowsheets row does not say why it is empty');
      if (await page.locator('[data-testid="new-scenario"]').isDisabled()) problems.push('New scenario is disabled');
      if (await page.locator('main button[disabled]').count()) problems.push(`${await page.locator('main button[disabled]').count()} button(s) on the index are disabled`);
      if (!/Casein and PHA/.test(await page.locator('[data-testid="scenarios"] [data-testid="hidden-by-archive"]').innerText().catch(() => '')))
        problems.push('the Scenarios row does not say whose scenarios it hides');
      await page.locator('[data-testid="new-scenario"]').click();
      await page.locator('[data-testid="new-scenario-dialog"]').waitFor({ timeout: 8000 }).catch(() => {});
      await page.waitForTimeout(400);
      const offeredOff = await ids('[data-testid="new-scenario-flowsheet"]');
      if (offeredOff !== startsOff.join()) problems.push(`the chooser offers ${offeredOff || 'nothing'} with the switch off, not ${startsOff.join() || 'nothing'}`);
      if (startsOff.length === 0) {
        if (!(await page.locator('[data-testid="new-scenario-dialog"] [data-testid="no-flowsheet"]').count())) problems.push('the empty chooser does not say why');
        await page.getByRole('button', { name: 'Cancel' }).click();
      } else {
        for (const [i, id] of startsOff.entries()) {
          if (i > 0) {
            await page.goto(`http://localhost:${PORT}/#/proforma`, { waitUntil: 'networkidle' });
            await page.locator('[data-testid="new-scenario"]').click();
            await page.locator('[data-testid="new-scenario-dialog"]').waitFor({ timeout: 8000 }).catch(() => {});
          }
          await make(id, `From the shelf: ${id}`);
        }
      }

      // The switch on: PHA's draft is on the shelf, and New scenario from it works end to end.
      if (!(await setShowArchived(page, true))) problems.push('the archive switch did not turn on');
      await page.goto(`http://localhost:${PORT}/#/proforma`, { waitUntil: 'networkidle' });
      const pha = page.locator('[data-testid="flowsheet-card"][data-flowsheet="pha_sugar_v0"]');
      await pha.waitFor({ timeout: 8000 }).catch(() => {});
      const rowsOn = await ids('[data-testid="flowsheet-card"]');
      if (rowsOn !== on.filter((f) => !f.reference).map((f) => f.id).join()) problems.push(`with the switch on the Flowsheets row lists ${rowsOn || 'nothing'}`);
      if ((await pha.locator('[data-testid="flowsheet-inputs"] li').count()) !== on.find((f) => f.id === 'pha_sugar_v0').inputs.length)
        problems.push('the PHA flowsheet card does not list its inputs');
      await pha.getByRole('button', { name: 'New scenario from this' }).click();
      await page.locator('[data-testid="new-scenario-dialog"]').waitFor({ timeout: 8000 }).catch(() => {});
      await page.waitForTimeout(400);
      if (!(await page.locator('[data-testid="new-scenario-flowsheet"][data-flowsheet="pha_sugar_v0"] input').isChecked().catch(() => false)))
        problems.push('New scenario from this does not open on its flowsheet');
      if ((await page.locator('[data-testid="new-scenario-program"]').inputValue().catch(() => '')) !== 'pha') problems.push('a scenario on the PHA flowsheet does not start in PHA');
      const made = await make('pha_sugar_v0', 'PHA from the shelf');
      // §3.2: the page lists the inputs the service bound for its flowsheet,
      // as the parameter panel's rows (OF-BLD-020 §2.2); wait for them.
      await page.locator('[data-testid="proforma-inputs"] [data-testid="param-row"]').first().waitFor({ timeout: 8000 }).catch(() => {});
      const pageRows = await page.locator('[data-testid="proforma-inputs"] [data-testid="param-row"]').count();
      if (pageRows !== 7) problems.push('the made scenario\u2019s page does not list the seven inputs a run needs');
      if (made) {
        await page.goto(`http://localhost:${PORT}/#/proforma`, { waitUntil: 'networkidle' });
        const card = page.locator(`[data-testid="biosteam-card"][data-scenario="${made}"]`);
        await card.waitFor({ timeout: 8000 }).catch(() => {});
        // A hash navigation remounts the index without a network-idle wait:
        // the counts line draws once the shelf answers, so wait for it.
        await card.locator('[data-testid="scenario-inputs"]').waitFor({ timeout: 8000 }).catch(() => {});
        const said = await card.innerText().catch(() => '');
        // §2.R: the card counts the inputs as the service binds them (the
        // double's answer to GET /api/proforma/bind), as the page lists them.
        const bound = fixture('proforma-bind.json').on.pha_sugar_v0.body.inputs;
        const of = (b) => bound.filter((i) => i.binding === b).length;
        const counted = `${bound.length} inputs: ${of('records')} bound to records, ${of('waiting')} waiting for an assumption`;
        if (!/Not run yet/.test(said) || !said.includes(counted) || bound.length !== pageRows)
          problems.push(`the index does not list the made scenario as not run with its inputs as the service binds them (${counted}; the page lists ${pageRows}): ${JSON.stringify(said.slice(0, 200))}`);
        await page.waitForTimeout(700);
        await page.reload({ waitUntil: 'networkidle' });
        await card.waitFor({ timeout: 8000 }).catch(() => {});
        if (!(await card.count())) problems.push('the made scenario did not survive a reload');
        await page.goto(`http://localhost:${PORT}/#/settings`, { waitUntil: 'networkidle' });
        await page.goto(`http://localhost:${PORT}/#/proforma/scenario/${made}`, { waitUntil: 'networkidle' });
        await page.reload({ waitUntil: 'networkidle' });
        await page.locator('[data-testid="scenario-not-run"]').waitFor({ timeout: 8000 }).catch(() => {});
        if (!(await page.locator('[data-testid="scenario-not-run"]').count())) problems.push('a deep link to the made scenario, after a reload, does not open it');
      }
      // The palette's New Proforma scenario opens the chooser on the index.
      await page.goto(`http://localhost:${PORT}/#/biorepo`, { waitUntil: 'networkidle' });
      await page.keyboard.press('Control+k');
      await page.locator('input[aria-label="Command palette"]').fill('New Proforma scenario');
      await page.waitForTimeout(200);
      await page.keyboard.press('Enter');
      await page.locator('[data-testid="new-scenario-dialog"]').waitFor({ timeout: 8000 }).catch(() => {});
      if (!/#\/proforma$/.test(page.url()) || !(await page.locator('[data-testid="new-scenario-dialog"]').count()))
        problems.push('the palette\u2019s New Proforma scenario does not open the chooser on Proforma');
    } catch (e) {
      problems.push(String(e).slice(0, 160));
    }
    if (problems.length) {
      proformaFails++;
      console.log(`✗ proforma     ${problems.join('; ')}`);
    } else {
      console.log('✓ proforma     the index lists the shelf\u2019s reference runs with a run and a status line and its flowsheets with their inputs, says why a row is empty, disables nothing; New scenario makes a scenario that lands on its page saying it has not run, is listed as not run, and survives a reload; the palette opens the same chooser');
    }
    await page.close();
  }

  // ── OF-BLD-019 §3.2 — the scenario page runs the flowsheet and reads
  //    every table from the run.
  //
  // With the switch on, sc-pha-1 (a seed scenario, run by its id) and a
  // scenario made from the shelf's pha_sugar_v0 (run by its flowsheet, bound
  // as GET /api/proforma/bind binds it) each take the three inputs that wait,
  // typed into the parameter panel under the reviewer's name (OF-BLD-020
  // §2.2), and run against the double with them as overrides. After Run
  // every section is on the page and each table is as long as the stored
  // run's; after a reload the newest run reads back from its artifact, and
  // the index reads the made scenario's price from it. With the switch off,
  // a scenario made on a flowsheet the double cannot bind opens, says the
  // service's words and that it has not run, offers no run, and nothing
  // crashes; the made PHA scenario still opens its own program, under the
  // banner, with its run.
  let scenarioPageFails = 0;
  {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    const problems = [];
    page.on('pageerror', (e) => problems.push(`page error: ${e.message}`));
    const run = JSON.parse(readFileSync(join(process.cwd(), 'core/tests/fixtures/prototype/proforma-run.json'), 'utf8')).response;
    const count = (sel) => page.locator(sel).count();
    const typeAssumptions = async () => {
      for (const [key, value, low, high] of [['recovery', 0.95, 0.9, 0.98], ['sugarPrice', 0.4, 0.3, 0.5], ['sugarFeed', 10000, null, null]])
        await typeParam(page, key, value, { low, high });
    };
    const sections = async (who) => {
      await page.locator('[data-testid="run-result"]').waitFor({ timeout: 8000 }).catch(() => {});
      const lacks = [];
      if (!(await count('[data-testid="run-result"] [data-testid="scenario-price"]'))) lacks.push('the price');
      if (!/Base case, every input at its value/.test(await page.locator('[data-testid="base-case"]').innerText().catch(() => ''))) lacks.push('the base case');
      if ((await count('[data-testid="waterfall-row"]')) !== run.tea.lines.length || (await count('[data-testid="waterfall-total"]')) !== 1) lacks.push('the cost breakdown');
      if ((await count('[data-testid="sensitivity"] [data-testid="tornado-row"]')) !== run.sensitivity.length) lacks.push('the sensitivity');
      if ((await count('[data-testid="distribution-bin"]')) !== run.histogram.length) lacks.push('the distribution');
      if ((await count('[data-testid="stream-row"]')) !== run.streams.length) lacks.push('the streams');
      if ((await count('[data-testid="unit-row"]')) !== run.units.length) lacks.push('the equipment');
      if ((await count('[data-testid="utility-row"]')) !== (run.utilities ? 4 : 0)) lacks.push('the utilities');
      if (run.diagram ? (await count('[data-testid="diagram-svg"]')) !== 1 : (await count('[data-testid="diagram-units"] li')) !== run.unitOrder.length)
        lacks.push('the diagram or its ordered units');
      if (!run.diagram && !(await page.locator('[data-testid="diagram-note"]').innerText().catch(() => '')).includes(run.diagramNote)) lacks.push("the diagram's note");
      for (const t of ['streams-table', 'equipment-table', 'utilities', 'diagram']) if (!(await count(`[data-testid="csv-${t}"]`))) lacks.push(`the CSV of ${t}`);
      if (!(await count('[data-testid="scenario-pin"]')) || !(await count('[data-testid="compare-link"]'))) lacks.push('pin and Compare');
      const train = await page.locator('[data-testid="train-link"]').getAttribute('href').catch(() => null);
      if (train !== `#/pureos/train/${run.artifactId}`) lacks.push(`the link to pureOS's train (${train})`);
      if (lacks.length) problems.push(`${who}: the page lacks ${lacks.join(', ')}`);
    };
    try {
      if (!(await setShowArchived(page, true))) problems.push('the archive switch did not turn on');
      await page.goto(`http://localhost:${PORT}/#/settings/corpus`, { waitUntil: 'networkidle' });
      await page.locator('input[aria-label="Reviewer name"]').fill(REVIEWER);
      await page.waitForTimeout(400);

      // The seed scenario, by its id.
      await page.goto(`http://localhost:${PORT}/#/proforma/scenario/sc-pha-1`, { waitUntil: 'networkidle' });
      await page.locator('[data-testid="proforma-inputs"]').waitFor({ timeout: 8000 }).catch(() => {});
      if (!(await count('[data-testid="scenario-not-run"]'))) problems.push('sc-pha-1 does not say it has not run');
      const meta = await page.locator('[data-testid="scenario-meta"]').innerText().catch(() => '');
      if (!/Flowsheet: PHA from fermentable sugar, draft v0/.test(meta) || !/Program: PHA/.test(meta)) problems.push(`sc-pha-1's header does not name its flowsheet and program: ${JSON.stringify(meta)}`);
      if (!/The simulator (has not started|is starting|is warm|failed)/.test(await page.locator('[data-testid="run-status"]').innerText().catch(() => '')))
        problems.push('the Run has no status line');
      await typeAssumptions();
      await page.getByRole('button', { name: 'Run the scenario' }).click();
      await sections('sc-pha-1');
      const seedPost = doubleState.proformaRuns.at(-1);
      if (seedPost?.scenarioId !== 'sc-pha-1' || 'flowsheet' in (seedPost ?? {})) problems.push(`sc-pha-1 was not run by its id alone: ${JSON.stringify(seedPost).slice(0, 120)}`);
      await page.waitForTimeout(700);
      await page.reload({ waitUntil: 'networkidle' });
      await sections('sc-pha-1 after a reload');
      if (!/computed \d{4}-\d\d-\d\d \d\d:\d\d UTC in [\d.]+ s/.test(await page.locator('[data-testid="run-result"]').innerText().catch(() => '')))
        problems.push('after a reload sc-pha-1 does not read its newest run back from the artifact');

      // OF-BLD-019 §3.R (findings 8, 21): a run the service holds is found
      // by a browser that kept none, on the page and on the index card.
      {
        const fresh = await browser.newPage({ viewport: { width: 1440, height: 900 } });
        fresh.on('pageerror', (e) => problems.push(`page error (a fresh browser): ${e.message}`));
        if (!(await setShowArchived(fresh, true))) problems.push('the archive switch did not turn on in a fresh browser');
        await fresh.goto(`http://localhost:${PORT}/#/proforma/scenario/sc-pha-1`, { waitUntil: 'networkidle' });
        await fresh.locator('[data-testid="run-result"]').waitFor({ timeout: 8000 }).catch(() => {});
        const shown = await fresh.locator('[data-testid="run-result"]').innerText().catch(() => '');
        if (!shown.includes(run.artifactId) || (await fresh.locator('[data-testid="scenario-not-run"]').count()))
          problems.push(`a browser that kept no run does not show the run the service holds for sc-pha-1 (${JSON.stringify(shown.slice(0, 120))})`);
        await fresh.goto(`http://localhost:${PORT}/#/proforma`, { waitUntil: 'networkidle' });
        const freshCard = fresh.locator('[data-testid="biosteam-card"][data-scenario="sc-pha-1"]');
        await freshCard.locator('[data-testid="scenario-price"]').waitFor({ timeout: 8000 }).catch(() => {});
        if (!(await freshCard.locator('[data-testid="scenario-price"]').count()) || (await freshCard.locator('[data-testid="scenario-not-run"]').count()))
          problems.push('the index card of a browser that kept no run does not read the run the service holds');
        await fresh.close();
      }

      // A scenario made from the shelf, run by its flowsheet.
      await page.goto(`http://localhost:${PORT}/#/proforma`, { waitUntil: 'networkidle' });
      const pha = page.locator('[data-testid="flowsheet-card"][data-flowsheet="pha_sugar_v0"]');
      await pha.waitFor({ timeout: 8000 }).catch(() => {});
      await pha.getByRole('button', { name: 'New scenario from this' }).click();
      await page.locator('[data-testid="new-scenario-dialog"]').waitFor({ timeout: 8000 }).catch(() => {});
      await page.locator('[data-testid="new-scenario-name"]').fill('Runs from the shelf');
      await page.locator('[data-testid="new-scenario-create"]').click();
      await page.locator('[data-testid="proforma-inputs"]').waitFor({ timeout: 8000 }).catch(() => {});
      const made = /#\/proforma\/scenario\/(sc-[^/?]+)$/.exec(page.url())?.[1] ?? null;
      if (!made) throw new Error(`New scenario did not land on a scenario page (${page.url()})`);
      await page.locator('[data-testid="param-row"]').first().waitFor({ timeout: 8000 }).catch(() => {});
      if ((await count('[data-testid="param-row"]')) !== 7 || (await count('[data-testid="param-chip"][data-origin="record"]')) !== 4)
        problems.push('the made scenario does not list its seven inputs with four bound to records');
      if (!(await count('[data-testid="scenario-not-run"]'))) problems.push('the made scenario does not say it has not run');
      if (!(await page.getByRole('button', { name: 'Run the scenario' }).isDisabled())) problems.push('the made scenario is offered a run while inputs wait');
      await typeAssumptions();
      await page.getByRole('button', { name: 'Run the scenario' }).click();
      await sections('a scenario made from pha_sugar_v0');
      const madePost = doubleState.proformaRuns.at(-1);
      if (madePost?.scenarioId !== made || madePost?.flowsheet !== 'pha_sugar_v0' || madePost?.overrides?.length !== 3 ||
        madePost.overrides.some((o) => o.by !== REVIEWER || o.scope !== `proforma:${made}`) || 'assumptions' in madePost)
        problems.push(`the made scenario was not run by its flowsheet with three signed overrides of its scope: ${JSON.stringify(madePost).slice(0, 160)}`);
      await page.waitForTimeout(700);
      await page.goto(`http://localhost:${PORT}/#/proforma`, { waitUntil: 'networkidle' });
      const card = page.locator(`[data-testid="biosteam-card"][data-scenario="${made}"]`);
      await card.locator('[data-testid="scenario-price"]').waitFor({ timeout: 8000 }).catch(() => {});
      if (!(await card.locator('[data-testid="scenario-price"]').count())) problems.push('the index does not read the made scenario\u2019s price from its run');

      // The switch off, and a scenario made on a flowsheet the double cannot bind.
      if (!(await setShowArchived(page, false))) problems.push('the archive switch did not turn off');
      await page.evaluate(
        async ({ from, to }) => {
          const db = await new Promise((resolve, reject) => {
            const r = indexedDB.open('openferment', 1);
            r.onsuccess = () => resolve(r.result);
            r.onerror = () => reject(r.error);
          });
          const snap = await new Promise((resolve) => {
            const g = db.transaction('durable', 'readonly').objectStore('durable').get('snapshot');
            g.onsuccess = () => resolve(g.result);
          });
          const sc = { ...snap.createdScenarios[from], ...to };
          delete sc.program;
          snap.createdScenarios = { ...snap.createdScenarios, [sc.id]: sc };
          await new Promise((resolve) => {
            const tx = db.transaction('durable', 'readwrite');
            tx.objectStore('durable').put(snap, 'snapshot');
            tx.oncomplete = resolve;
          });
          db.close();
        },
        { from: made, to: { id: 'sc-smoke-unbound', name: 'Made on a flowsheet this service lacks', flowsheetId: 'no_such_flowsheet', modelId: 'no_such_flowsheet', lastRunId: null } },
      );
      await page.reload({ waitUntil: 'networkidle' });
      await page.goto(`http://localhost:${PORT}/#/proforma/scenario/sc-smoke-unbound`, { waitUntil: 'networkidle' });
      await page.locator('[data-testid="bind-problem"]').waitFor({ timeout: 8000 }).catch(() => {});
      const unbound = await page.locator('main').innerText().catch(() => '');
      if (!/This scenario has not run yet/.test(unbound)) problems.push('a scenario the double cannot bind does not say it has not run');
      if (!/there is no flowsheet no_such_flowsheet on the shelf/.test(unbound)) problems.push('a scenario the double cannot bind does not say the service\u2019s words');
      const unboundRun = await page.getByRole('button', { name: 'Run the scenario' }).isDisabled({ timeout: 5000 }).catch(() => null);
      if (unboundRun !== true) problems.push(unboundRun === null ? 'a scenario the double cannot bind shows no Run' : 'a scenario with no binding is offered a run');
      await page.goto(`http://localhost:${PORT}/#/proforma/scenario/${made}`, { waitUntil: 'networkidle' });
      await page.locator('[data-testid="proforma-inputs"]').waitFor({ timeout: 8000 }).catch(() => {});
      if (!(await count('[data-archived-program="pha"]'))) problems.push('the made PHA scenario does not open under its banner with the switch off');
      await page.locator('[data-testid="param-row"]').first().waitFor({ timeout: 8000 }).catch(() => {});
      if ((await count('[data-testid="param-row"]')) !== 7) problems.push('with the switch off the made PHA scenario does not bind its own program\u2019s inputs');
      await sections('the made PHA scenario with the switch off');
    } catch (e) {
      problems.push(String(e).slice(0, 160));
    }
    if (problems.length) {
      scenarioPageFails++;
      console.log(`✗ scenario     ${problems.join('; ')}`);
    } else {
      console.log('✓ scenario     sc-pha-1 by its id and a scenario made from pha_sugar_v0 by its flowsheet each take three values typed in the parameter panel and run with them as signed overrides; the price, the base case, the cost breakdown, the sensitivity, the distribution, the streams, the equipment, the utilities and the ordered units are each as long as the stored run, each table with its CSV, with pin, Compare and pureOS\u2019s train; the newest run reads back from its artifact after a reload and gives the index its price; with the switch off a scenario the double cannot bind says the service\u2019s words and that it has not run, and the made PHA scenario opens its own program under the banner');
    }
    await page.close();
  }

  // ── OF-BLD-020 §2.2 — one parameter panel renders every input with its
  //    source, and a person's change is a named assumption the run carries.
  //
  // With the switch off, on sc-yeast-1: the panel shows every parameter the
  // scope serves, in its groups, each with the source the service bound; with
  // no reviewer name every edit control is disabled and the rows say where to
  // set one. With one: a record-bound row shows `record ×N` and opens its
  // records; Why gives the gloss, the source chain with the one that
  // answered, and the bounds' reason; a yield typed above its bounds makes the
  // chip say `assumption by <name>`, is kept as typed, and carries the
  // warning the service returned; the economic inputs typed with their low,
  // high and basis take the inputs out of waiting; Run posts the three as
  // overrides of the scenario's scope, signed, and no assumptions; the run's
  // basis is read back with `assumption by`; Reset to source brings the
  // records back; with the resolve unreachable the panel says so and keeps
  // the override; a reload keeps them.
  let panelFails = 0;
  {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    const problems = [];
    page.on('pageerror', (e) => problems.push(`page error: ${e.message}`));
    const fixture = (name) => JSON.parse(readFileSync(join(process.cwd(), 'core/tests/fixtures/prototype', name), 'utf8')).response;
    const recorded = fixture('params-proforma.json');
    const served = recorded.scopes['proforma:sc-yeast-1'].body;
    const outside = recorded.resolve.body.values.find((v) => v.key === 'yield');
    const yieldSpec = served.specs.find((sp) => sp.key === 'yield');
    const yieldRecords = served.values.find((v) => v.key === 'yield').recordIds.length;
    const yeastRun = fixture('proforma-run-yeast.json');
    const row = (key) => page.locator(`[data-testid="param-row"][data-key="${key}"]`);
    try {
      doubleState.proformaRunsOnFile.clear();
      if (!(await setShowArchived(page, false))) problems.push('the archive switch is not off');
      await page.goto(`http://localhost:${PORT}/#/proforma/scenario/sc-yeast-1`, { waitUntil: 'networkidle' });
      await row('yield').waitFor({ timeout: 8000 }).catch(() => {});
      const rows = await page.locator('[data-testid="param-row"]').evaluateAll((els) => els.map((e) => `${e.getAttribute('data-key')}:${e.getAttribute('data-origin')}`).join());
      const want = served.values.map((v) => `${v.key}:${v.origin}`).join();
      if (rows !== want) problems.push(`the panel does not show each parameter with the source the service served (${rows}; the service: ${want})`);
      const groups = await page.locator('[data-testid="param-group"]').evaluateAll((els) => els.map((e) => e.getAttribute('data-group')).join());
      if (groups !== 'Process,Economics,Conventions') problems.push(`the panel's groups are ${groups}`);
      if (!(await page.locator('[data-testid="param-need-reviewer"]').count()) || (await page.locator('[data-testid="param-value-input"]:enabled').count()) !== 0)
        problems.push('with no reviewer name an edit control is enabled, or no row says where to set one');
      if (await row('ethanol_purity').locator('[data-testid="param-edit"]').count()) problems.push('a convention stated in words offers an edit');

      await page.goto(`http://localhost:${PORT}/#/settings/corpus`, { waitUntil: 'networkidle' });
      await page.locator('input[aria-label="Reviewer name"]').fill(REVIEWER);
      await page.waitForTimeout(400);
      await page.goto(`http://localhost:${PORT}/#/proforma/scenario/sc-yeast-1`, { waitUntil: 'networkidle' });
      await row('yield').waitFor({ timeout: 8000 }).catch(() => {});
      if (await page.locator('[data-testid="param-need-reviewer"]').count()) problems.push('with a reviewer name a row still asks for one');
      const fromRecords = await chipOf(page, 'yield');
      if (fromRecords.origin !== 'record' || !fromRecords.text.includes(`record ×${yieldRecords}`)) problems.push(`the yield's chip does not say record ×${yieldRecords} (${JSON.stringify(fromRecords)})`);
      await row('yield').locator('[data-testid="param-records"] summary').click();
      if ((await row('yield').locator('[data-testid="source-records"] > span.inline-flex').count()) !== yieldRecords) problems.push("the yield's records do not open from its chip");
      await row('yield').locator('[data-testid="param-why"] summary').click();
      const why = (await row('yield').locator('[data-testid="param-why"]').innerText().catch(() => '')).replace(/\s+/g, ' ');
      const answered = await row('yield').locator('[data-testid="param-why-source"][data-answered="true"]').innerText().catch(() => '');
      if (!why.includes(yieldSpec.boundsReason) || !why.includes(yieldSpec.gloss) || !/records of ethanol_yield_substrate/.test(answered))
        problems.push(`Why does not give the gloss, the chain with the records that answered, and the bounds' reason (${JSON.stringify(why.slice(0, 160))})`);

      // A yield above its bounds: kept as typed, named, and warned.
      await typeParam(page, 'yield', outside.value);
      await row('yield').locator('[data-testid="param-warning"]').waitFor({ timeout: 8000 }).catch(() => {});
      const typed = await chipOf(page, 'yield');
      if (typed.origin !== 'assumption' || !typed.text.includes(`assumption by ${REVIEWER}`)) problems.push(`a typed yield's chip does not say assumption by ${REVIEWER} (${JSON.stringify(typed)})`);
      if ((await row('yield').locator('[data-testid="param-warning"]').innerText().catch(() => '')) !== outside.outOfBounds) problems.push("a yield outside its bounds does not carry the service's warning");
      if (!(await row('yield').locator('[data-testid="param-value"]').innerText().catch(() => '')).startsWith(String(outside.value))) problems.push('a yield outside its bounds is not kept as typed');
      const asked = doubleState.paramResolves.at(-1);
      if (asked?.scope !== 'proforma:sc-yeast-1' || !asked.overrides?.some((o) => o.key === 'yield' && o.value === outside.value && o.by === REVIEWER))
        problems.push(`the panel did not ask the service to resolve the yield typed: ${JSON.stringify(asked).slice(0, 160)}`);
      if (!(await row('yield').locator('[data-testid="param-value-input"]').getAttribute('aria-label').catch(() => null))) problems.push('the value box carries no label');

      // The economic inputs, with a low, a high and what each rests on.
      await typeParam(page, 'plant_scale', 100000, { note: 'a smoke test value' });
      await typeParam(page, 'glucose_price', 0.4, { low: 0.3, high: 0.5, note: 'a smoke test value' });
      await page.waitForTimeout(600);
      if (await page.locator('[data-testid="proforma-waiting"]').count()) problems.push('inputs still wait with every value typed');
      await page.getByRole('button', { name: 'Run the scenario' }).click();
      await page.locator('[data-testid="run-result"]').waitFor({ timeout: 8000 }).catch(() => {});
      const posted = doubleState.proformaRuns.at(-1);
      const sent = (posted?.overrides ?? []).map((o) => o.key).sort().join();
      const price = (posted?.overrides ?? []).find((o) => o.key === 'glucose_price');
      if (sent !== 'glucose_price,plant_scale,yield' || posted.overrides.some((o) => o.scope !== 'proforma:sc-yeast-1' || o.by !== REVIEWER) ||
        price?.low !== 0.3 || price?.high !== 0.5 || price?.note !== 'a smoke test value' || 'assumptions' in posted)
        problems.push(`the run did not post the scope's three overrides, signed, and no assumptions: ${JSON.stringify(posted).slice(0, 200)}`);
      const by = yeastRun.evidence.basis.inputs.find((i) => i.name === 'glucose_price')?.source.by;
      const basisLine = await page.locator('[data-testid="run-basis-assumptions"]').innerText().catch(() => '');
      if (!by || !basisLine.includes(`assumption by ${by}`)) problems.push(`the run's basis is not read back with who each assumption is by (${JSON.stringify(basisLine.slice(0, 120))})`);

      // Reset to source: the records come back, and the warning goes.
      await row('yield').locator('[data-testid="param-reset"]').click();
      await row('yield').locator('[data-testid="param-chip"][data-origin="record"]').waitFor({ timeout: 8000 }).catch(() => {});
      const back = await chipOf(page, 'yield');
      if (back.origin !== 'record' || !back.text.includes(`record ×${yieldRecords}`) || (await row('yield').locator('[data-testid="param-warning"]').count()))
        problems.push(`Reset to source does not bring the records back (${JSON.stringify(back)})`);
      if (await row('yield').locator('[data-testid="param-reset"]').count()) problems.push('a row with no override still offers Reset to source');

      // The resolve unreachable: the panel says so, and keeps the override.
      await page.route('**/api/params/**/resolve', (r) => r.abort());
      await typeParam(page, 'yield', 0.45);
      await page.locator('[data-testid="param-problem"][data-down="true"]').waitFor({ timeout: 8000 }).catch(() => {});
      if (!(await page.locator('[data-testid="param-problem"][data-down="true"]').count())) problems.push('with the service unreachable the panel does not say so');
      if ((await chipOf(page, 'yield')).origin !== 'assumption') problems.push('with the service unreachable the override is not kept');
      await page.unroute('**/api/params/**/resolve');

      // A reload keeps every override.
      await page.waitForTimeout(700);
      await page.reload({ waitUntil: 'networkidle' });
      await row('plant_scale').locator('[data-testid="param-chip"][data-origin="assumption"]').waitFor({ timeout: 8000 }).catch(() => {});
      for (const key of ['plant_scale', 'glucose_price', 'yield']) {
        const c = await chipOf(page, key);
        if (c.origin !== 'assumption' || !c.text.includes(`assumption by ${REVIEWER}`)) problems.push(`${key}'s override did not survive a reload (${JSON.stringify(c)})`);
      }
    } catch (e) {
      problems.push(String(e).slice(0, 160));
    }
    if (problems.length) {
      panelFails++;
      console.log(`✗ panel        ${problems.join('; ')}`);
    } else {
      console.log("✓ panel        sc-yeast-1's inputs are the parameter panel: every parameter in its group with the source the service bound; no reviewer name, no edit; record ×N opens its records, Why gives the chain and the bounds' reason; a yield typed above its bounds is kept, named and warned; the run posts the scope's overrides, signed, and the basis reads back who each is by; Reset to source brings the records back; with the resolve unreachable the panel says so and keeps the override; a reload keeps them");
    }
    await page.close();
  }

  // ── OF-BLD-019 §3.3 — a reference biorefinery's page, for each reference
  //    on the shelf.
  //
  // Over the double's fixtures (each a run made through the real code with
  // the stand-in in place of BioSTEAM, and the package test's values parsed
  // from the installed file): the header names the source, the program, the
  // package test and the provenance; the price is the output the shelf
  // names; "Held to its package's own test" has one row per regression value
  // (eleven for corn), each with this run's measured value and whether it is
  // within; every section of a scenario page is as long as the run's table;
  // the TEA's installed equipment cost is the TEA's; the corn plant states its
  // compatibility line in words; Run posts. The index's reference cards link
  // to their pages.
  let referenceFails = 0;
  {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    const problems = [];
    page.on('pageerror', (e) => problems.push(`page error: ${e.message}`));
    page.on('console', (m) => {
      if (m.type() === 'error' && !IGNORE.some((re) => re.test(m.text()))) problems.push(`console: ${m.text().slice(0, 140)}`);
    });
    const fixture = (name) => JSON.parse(readFileSync(join(process.cwd(), 'core/tests/fixtures/prototype', name), 'utf8')).response;
    const count = (sel) => page.locator(sel).count();
    // As the page prints a regression value: thousands grouped, else five significant figures.
    const sig = (v) => (v == null ? '—' : Math.abs(v) >= 1000 ? Math.round(v).toLocaleString('en-US') : String(Number(v.toPrecision(5))));
    try {
      for (const id of ['cornstover_benchmark', 'corn_drygrind']) {
        const ref = fixture(`proforma-reference-${id}.json`);
        const o = ref.artifact.output;
        const lacks = [];
        await page.goto(`http://localhost:${PORT}/#/proforma/reference/${id}`, { waitUntil: 'networkidle' });
        await page.locator('[data-testid="regression-row"]').first().waitFor({ timeout: 8000 }).catch(() => {});
        const meta = await page.locator('[data-testid="reference-meta"]').innerText().catch(() => '');
        if (!meta.includes(ref.flowsheet.source) || !meta.includes(ref.flowsheet.packageTest) || !(await count('[data-testid="reference-provenance"]')))
          lacks.push(`the header's source, package test and provenance (${JSON.stringify(meta.slice(0, 160))})`);
        if (!/Program: (Yeast ethanol|none \(general\))/.test(meta)) lacks.push('the program');
        if (!(await page.locator('h1').innerText().catch(() => '')).includes(ref.flowsheet.title)) lacks.push('its title');
        const price = Number(await page.locator('[data-testid="reference-price"]').innerText().catch(() => 'NaN'));
        if (!(Math.abs(price - o[ref.flowsheet.priceOutput]) < 1e-3)) lacks.push(`the price the shelf names (${ref.flowsheet.priceOutput}: ${price})`);
        const checks = o.checks;
        if ((await count('[data-testid="regression-row"]')) !== ref.regression.values.length || checks.length !== ref.regression.values.length)
          lacks.push(`one row per package test value (${await count('[data-testid="regression-row"]')} of ${ref.regression.values.length})`);
        if (id === 'corn_drygrind' && (await count('[data-testid="regression-row"]')) !== 11) lacks.push('the eleven values of test_corn');
        const measured = await page.locator('[data-testid="regression-measured"]').allInnerTexts();
        const within = await page.locator('[data-testid="regression-row"]').evaluateAll((rs) => rs.map((r) => r.getAttribute('data-within')));
        if (measured.join('|') !== checks.map((c) => sig(c.measured)).join('|')) lacks.push(`this run's measured values (${measured.join(', ')})`);
        if (within.join('|') !== checks.map((c) => String(c.within)).join('|')) lacks.push('within or not, as the service decided');
        if (!/within the package’s tolerance on this run/.test(await page.locator('[data-testid="regression-summary"]').innerText().catch(() => ''))) lacks.push('the count within');
        if ((await count('[data-testid="waterfall-row"]')) !== o.tea.lines.length || (await count('[data-testid="waterfall-total"]')) !== 1) lacks.push('the cost breakdown');
        if ((await count('[data-testid="stream-row"]')) !== o.streams.length) lacks.push('the streams');
        if ((await count('[data-testid="unit-row"]')) !== o.units.length) lacks.push('the equipment');
        if ((await count('[data-testid="utility-row"]')) !== (o.utilities ? 4 : 0)) lacks.push('the utilities');
        if (o.diagram ? (await count('[data-testid="diagram-svg"]')) !== 1 : (await count('[data-testid="diagram-units"] li')) !== o.unitOrder.length)
          lacks.push('the diagram or its ordered units');
        for (const t of ['streams-table', 'equipment-table', 'utilities', 'diagram', 'regression']) if (!(await count(`[data-testid="csv-${t}"]`))) lacks.push(`the CSV of ${t}`);
        const installed = await page.locator('[data-testid="tea-installed"]').innerText().catch(() => '');
        if (!installed.includes(Math.round(o.tea.installedEquipmentCost).toLocaleString('en-US'))) lacks.push(`the TEA's own installed equipment cost (${JSON.stringify(installed)})`);
        if (!/never a sum|need not equal/.test(await page.locator('[data-testid="tea-installed-note"]').innerText().catch(() => ''))) lacks.push('why the installed cost is the TEA’s');
        const compat = ref.artifact.inputs.find((i) => i.name === 'compatibility');
        const compatText = await page.locator('[data-testid="compatibility"]').innerText().catch(() => '');
        if (compat ? !compatText.includes(compat.value) || !compatText.includes('No number of the package') : compatText) lacks.push('the compatibility line, where and only where the basis states one');
        if (id === 'corn_drygrind' && !compat) lacks.push('the corn plant’s compatibility input in its fixture');
        if (!/The simulator (has not started|is starting|is warm|failed)/.test(await page.locator('[data-testid="reference-status"]').innerText().catch(() => ''))) lacks.push('the status line');
        const before = doubleState.proformaReferences.length;
        await page.locator('[data-testid="reference-run"]').click();
        await page.locator('[data-testid="reference-run"]:has-text("Rerun")').waitFor({ timeout: 8000 }).catch(() => {});
        if (doubleState.proformaReferences.length !== before + 1 || doubleState.proformaReferences.at(-1) !== id) lacks.push('Run did not post');
        if ((await count('[data-testid="regression-row"]')) !== ref.regression.values.length) lacks.push('the table after a run');
        // §2.R: the run the page names reads back by its id, as the service keeps it.
        await page.goto(`http://localhost:${PORT}/#/biorepo/artifacts/${ref.artifact.id}`, { waitUntil: 'networkidle' });
        await page.locator('[data-testid="artifact-inputs"]').waitFor({ timeout: 8000 }).catch(() => {});
        if ((await count('[data-testid="artifact-inputs"] tbody tr')) !== ref.artifact.inputs.length) lacks.push(`its run ${ref.artifact.id} read back by its id`);
        if (lacks.length) problems.push(`${id}: the page lacks ${lacks.join(', ')}`);
      }
      // OF-BLD-019 §3.R (findings 13, 24): a run still in flight when the
      // reader moves to the other reference lands on the page that asked,
      // never on the one now open.
      {
        const stover = fixture('proforma-reference-cornstover_benchmark.json');
        await page.goto(`http://localhost:${PORT}/#/proforma/reference/corn_drygrind`, { waitUntil: 'networkidle' });
        await page.locator('[data-testid="reference-run"]').waitFor({ timeout: 8000 }).catch(() => {});
        let release;
        const held = new Promise((r) => (release = r));
        await page.route('**/api/proforma/reference/corn_drygrind', async (r) => {
          if (r.request().method() !== 'POST') return r.continue();
          await held;
          return r.continue();
        });
        await page.locator('[data-testid="reference-run"]').click();
        await page.evaluate(() => {
          window.location.hash = '#/proforma/reference/cornstover_benchmark';
        });
        await page.locator('[data-testid="proforma-reference"][data-flowsheet="cornstover_benchmark"] [data-testid="reference-price"]').waitFor({ timeout: 8000 }).catch(() => {});
        release();
        await page.waitForTimeout(800);
        await page.unroute('**/api/proforma/reference/corn_drygrind');
        const h1 = await page.locator('h1').innerText().catch(() => '');
        const shownPrice = Number(await page.locator('[data-testid="reference-price"]').innerText().catch(() => 'NaN'));
        const caption = await page.locator('[data-testid="regression-table"]').innerText().catch(() => '');
        if (!h1.includes(stover.flowsheet.title) || !(Math.abs(shownPrice - stover.artifact.output[stover.flowsheet.priceOutput]) < 1e-3) || !/test_cornstover/.test(caption))
          problems.push(`a corn run answered after the reader moved on lands on the corn stover page (${JSON.stringify(h1)}, ${shownPrice})`);
        if (await page.locator('[data-testid="reference-run"]:has-text("Running")').count()) problems.push('the corn stover page shows the corn plant\u2019s run as its own');
      }
      // The index's reference cards say how many of their package test's values the run holds (finding 30).
      await page.goto(`http://localhost:${PORT}/#/proforma`, { waitUntil: 'networkidle' });
      for (const id of ['cornstover_benchmark', 'corn_drygrind']) {
        const checks = fixture(`proforma-reference-${id}.json`).artifact.output.checks;
        const card = page.locator(`[data-testid="reference-card"][data-flowsheet="${id}"]`);
        await card.locator('[data-testid="reference-within"]').waitFor({ timeout: 8000 }).catch(() => {});
        const within = await card.locator('[data-testid="reference-within"]').innerText().catch(() => '');
        if (!within.startsWith(`${checks.filter((c) => c.within).length} of ${checks.length} values of test_`)) problems.push(`the ${id} card does not say how many of its package test's values the run holds (${JSON.stringify(within)})`);
      }
      // The index's reference cards link to their pages.
      await page.goto(`http://localhost:${PORT}/#/proforma`, { waitUntil: 'networkidle' });
      const link = page.locator('[data-testid="reference-card"][data-flowsheet="corn_drygrind"] [data-testid="reference-title"]');
      await link.waitFor({ timeout: 8000 }).catch(() => {});
      await link.click().catch(() => {});
      await page.locator('[data-testid="proforma-reference"]').waitFor({ timeout: 8000 }).catch(() => {});
      if (!/#\/proforma\/reference\/corn_drygrind$/.test(page.url())) problems.push(`the corn reference card does not open its page (${page.url()})`);

      // OF-BLD-019 §3.R (finding 14): an id that is no reference on the shelf
      // says the service's words and claims nothing: no reference subtitle,
      // no run, no "not run yet". (Its own page: the service's 404 is a
      // console line by design.)
      const bad = await browser.newPage({ viewport: { width: 1440, height: 900 } });
      bad.on('pageerror', (e) => problems.push(`page error: ${e.message}`));
      for (const id of ['nope', 'ethanol_glucose_v0']) {
        await bad.goto(`http://localhost:${PORT}/#/proforma/reference/${id}`, { waitUntil: 'networkidle' });
        await bad.locator('[data-testid="reference-problem"]').waitFor({ timeout: 8000 }).catch(() => {});
        const said = await bad.locator('[data-testid="reference-problem"]').innerText().catch(() => '');
        const body = await bad.locator('main').innerText().catch(() => '');
        if (!said.includes(`${id} is not a reference biorefinery on the shelf`)) problems.push(`/proforma/reference/${id} does not say the service's words (${JSON.stringify(said.slice(0, 120))})`);
        if ((await bad.locator('[data-testid="reference-run"]').count()) || /Not run on this service yet|A published biorefinery|· reference biorefinery/i.test(body))
          problems.push(`/proforma/reference/${id} still presents a reference biorefinery that has not run`);
      }
      await bad.close();
    } catch (e) {
      problems.push(String(e).slice(0, 160));
    }
    if (problems.length) {
      referenceFails++;
      console.log(`✗ reference    ${problems.join('; ')}`);
    } else {
      console.log('✓ reference    both reference pages name their source, program, package test and provenance, read the price the shelf names, hold every value of the package’s own test beside this run’s (eleven for corn), draw the cost breakdown, the TEA’s own installed cost, streams, equipment, utilities and units as long as the run, say the corn plant’s compatibility change in words, and Run posts; the index’s cards open them');
    }
    await page.close();
  }

  // ── OF-BLD-019 §3.3 — Compare sets BioSTEAM scenarios side by side.
  //
  // With the switch off: sc-yeast-1 and a scenario made from the shelf's
  // ethanol_glucose_v0 each take the two economic assumptions under the
  // reviewer's name, run against the double and are pinned. Compare shows
  // both, each read from its newest run artifact: the price, every TEA line
  // and every input the flowsheet takes with its source; the same flowsheet
  // draws no "bases differ" line. The pins survive a reload. With the switch
  // on, pinning sc-pha-1 (not run here) adds a column that says it has not
  // run and the line that their bases differ; pinning the casein example
  // sc-s1 brings the authored compare back beside them.
  let compareFails = 0;
  {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    const problems = [];
    page.on('pageerror', (e) => problems.push(`page error: ${e.message}`));
    page.on('console', (m) => {
      if (m.type() === 'error' && !IGNORE.some((re) => re.test(m.text()))) problems.push(`console: ${m.text().slice(0, 140)}`);
    });
    const fixture = (name) => JSON.parse(readFileSync(join(process.cwd(), 'core/tests/fixtures/prototype', name), 'utf8')).response;
    const count = (sel) => page.locator(sel).count();
    const yeast = fixture('proforma-run-yeast.json');
    const shelfEntry = fixture('proforma-shelf.json').find((f) => f.id === 'ethanol_glucose_v0');
    const typeYeast = async () => {
      await typeParam(page, 'plant_scale', 100000);
      await typeParam(page, 'glucose_price', 0.4, { low: 0.3, high: 0.5 });
    };
    const runAndPin = async (who) => {
      await page.getByRole('button', { name: 'Run the scenario' }).click();
      await page.locator('[data-testid="run-result"]').waitFor({ timeout: 8000 }).catch(() => {});
      if (!(await count('[data-testid="run-result"] [data-testid="scenario-price"]'))) problems.push(`${who} did not run`);
      await page.locator('[data-testid="scenario-pin"]').click();
      if ((await page.locator('[data-testid="scenario-pin"]').getAttribute('aria-pressed')) !== 'true') problems.push(`${who} did not pin`);
    };
    try {
      // A service with no run on file yet: the runs earlier flows made are forgotten (§3.R).
      doubleState.proformaRunsOnFile.clear();
      if (!(await setShowArchived(page, false))) problems.push('the archive switch is not off');
      await page.goto(`http://localhost:${PORT}/#/settings/corpus`, { waitUntil: 'networkidle' });
      await page.locator('input[aria-label="Reviewer name"]').fill(REVIEWER);
      await page.waitForTimeout(400);

      await page.goto(`http://localhost:${PORT}/#/proforma/scenario/sc-yeast-1`, { waitUntil: 'networkidle' });
      await page.locator('[data-testid="proforma-inputs"]').waitFor({ timeout: 8000 }).catch(() => {});
      await typeYeast();
      // OF-BLD-019 §3.R (finding 7): while the simulator is starting, Run
      // waits and says so, and comes back once the status line reads it
      // ready (or cold) again.
      await page.waitForTimeout(700);
      await page.route('**/api/proforma/status', (r) => r.fulfill({ json: { status: 'starting', error: null } }));
      await page.reload({ waitUntil: 'networkidle' });
      await page.locator('[data-testid="run-status"][data-status="starting"]').waitFor({ timeout: 8000 }).catch(() => {});
      await page.locator('[data-testid="run-waits"]').waitFor({ timeout: 8000 }).catch(() => {});
      const startingRun = page.getByRole('button', { name: 'Run the scenario' });
      if (!(await startingRun.isDisabled().catch(() => false)) || !(await count('[data-testid="run-waits"]')))
        problems.push('Run is offered while the simulator is starting, or the page does not say it waits');
      await page.unroute('**/api/proforma/status');
      await page.waitForFunction(() => [...document.querySelectorAll('button')].some((b) => /Run the scenario/.test(b.textContent ?? '') && !b.disabled), null, { timeout: 9000 }).catch(() => {});
      if (await startingRun.isDisabled().catch(() => true)) problems.push('Run does not come back once the simulator has started');
      await runAndPin('sc-yeast-1');
      // §2.R: after a reload the yeast scenario reads its newest run back from its artifact, as sc-pha-1 does.
      await page.waitForTimeout(700);
      await page.reload({ waitUntil: 'networkidle' });
      await page.locator('[data-testid="run-result"]').waitFor({ timeout: 8000 }).catch(() => {});
      if (!/computed \d{4}-\d\d-\d\d \d\d:\d\d UTC in [\d.]+ s/.test(await page.locator('[data-testid="run-result"]').innerText().catch(() => '')))
        problems.push('after a reload sc-yeast-1 does not read its newest run back from the artifact');

      await page.goto(`http://localhost:${PORT}/#/proforma`, { waitUntil: 'networkidle' });
      const card = page.locator('[data-testid="flowsheet-card"][data-flowsheet="ethanol_glucose_v0"]');
      await card.waitFor({ timeout: 8000 }).catch(() => {});
      await card.getByRole('button', { name: 'New scenario from this' }).click();
      await page.locator('[data-testid="new-scenario-dialog"]').waitFor({ timeout: 8000 }).catch(() => {});
      await page.locator('[data-testid="new-scenario-name"]').fill('Glucose to ethanol, compared');
      await page.locator('[data-testid="new-scenario-create"]').click();
      await page.locator('[data-testid="proforma-inputs"]').waitFor({ timeout: 8000 }).catch(() => {});
      const made = /#\/proforma\/scenario\/(sc-[^/?]+)$/.exec(page.url())?.[1] ?? null;
      if (!made) throw new Error(`New scenario did not land on a scenario page (${page.url()})`);
      await typeYeast();
      await runAndPin('the scenario made from ethanol_glucose_v0');
      await page.waitForTimeout(700);

      const compared = async (want) => {
        await page.goto(`http://localhost:${PORT}/#/biorepo/compare`, { waitUntil: 'networkidle' });
        await page.locator('[data-testid="compare-price"]').first().waitFor({ timeout: 8000 }).catch(() => {});
        const cols = await page.locator('[data-testid="compare-column"]').evaluateAll((els) => els.map((e) => e.getAttribute('data-scenario')).join());
        if (cols !== want.join()) problems.push(`Compare shows ${cols || 'nothing'}, not ${want.join()}`);
      };
      // OF-BLD-019 §3.R (finding 2): Home's pinned card reads what is
      // pinned: two BioSTEAM scenarios are not Cost model v0, and the card
      // puts no modeled tick of its own on them.
      await page.goto(`http://localhost:${PORT}/#/`, { waitUntil: 'networkidle' });
      const pinnedLine = page.locator('[data-testid="pinned-scenarios"]');
      await pinnedLine.waitFor({ timeout: 8000 }).catch(() => {});
      const pinnedWords = await pinnedLine.innerText().catch(() => '');
      const pinnedTick = await page.locator('a:has([data-testid="pinned-scenarios"]) .tick').count();
      if (!/compared from its newest run/.test(pinnedWords) || /Cost model v0/.test(pinnedWords) || pinnedTick !== 0)
        problems.push(`Home's pinned card calls BioSTEAM scenarios Cost model v0 or ticks them modeled (${JSON.stringify(pinnedWords)}, ${pinnedTick} tick)`);
      await compared(['sc-yeast-1', made]);
      const prices = (await page.locator('[data-testid="compare-price"]').allInnerTexts()).map(Number);
      if (prices.length !== 2 || prices.some((v) => !(Math.abs(v - yeast.quantiles.p50) < 1e-3))) problems.push(`Compare does not read each price from its run (${prices.join(', ')})`);
      if (!/USD per kg of fuel-grade ethanol/.test(await page.locator('[data-testid="compare-price-row"]').innerText().catch(() => ''))) problems.push('the price is shown without its basis');
      if ((await count('[data-testid="compare-line-row"]')) !== yeast.tea.lines.length) problems.push('Compare does not list every cost line of the TEA');
      if ((await count('[data-testid="compare-input-row"]')) !== shelfEntry.inputs.length) problems.push(`Compare does not list every input the flowsheet takes (${await count('[data-testid="compare-input-row"]')})`);
      const kinds = await page.locator('[data-testid="compare-input-row"][data-input="titre"] td[data-kind], [data-testid="compare-input-row"][data-input="glucose_price"] td[data-kind]').evaluateAll((els) => els.map((e) => e.getAttribute('data-kind')).join());
      if (kinds !== 'record,record,assumption,assumption') problems.push(`Compare does not name each input's source (${kinds})`);
      // The double's run is the fixture's, so its basis names the fixture's person, not the reviewer: the column reads the run.
      const assumed = await page.locator('[data-testid="compare-input-row"][data-input="glucose_price"]').innerText().catch(() => '');
      const by = yeast.evidence.basis.inputs.find((i) => i.name === 'glucose_price')?.source.by;
      if (!by || !assumed.includes(`assumption by ${by}`)) problems.push(`an assumption is not shown with who made it, as the run's basis names them (${JSON.stringify(assumed.slice(0, 120))})`);
      if (await count('[data-testid="compare-bases-differ"]')) problems.push('two scenarios on one flowsheet are said to differ in basis');
      if (await count('[data-testid="compare-not-run"]')) problems.push('a run scenario is said not to have run');
      await page.reload({ waitUntil: 'networkidle' });
      await page.locator('[data-testid="compare-column"]').first().waitFor({ timeout: 8000 }).catch(() => {});
      if ((await count('[data-testid="compare-column"]')) !== 2) problems.push('the pins did not survive a reload');

      // The switch on: a PHA scenario not run here, and a casein example.
      if (!(await setShowArchived(page, true))) problems.push('the archive switch did not turn on');
      await page.goto(`http://localhost:${PORT}/#/proforma/scenario/sc-pha-1`, { waitUntil: 'networkidle' });
      await page.locator('[data-testid="scenario-pin"]').click();
      await page.goto(`http://localhost:${PORT}/#/proforma/scenario/sc-s1`, { waitUntil: 'networkidle' });
      await page.locator('button[title="Pin to compare (p)"]').click();
      await page.waitForTimeout(400);
      await compared(['sc-pha-1', 'sc-yeast-1', made]);
      if ((await count('[data-testid="compare-not-run"]')) !== 1) problems.push('the PHA scenario with no run does not say so');
      const differ = await page.locator('[data-testid="compare-bases-differ"]').innerText().catch(() => '');
      if (!/bases differ/i.test(differ) || !/PHA/.test(differ) || !/ethanol/i.test(differ)) problems.push(`scenarios on two flowsheets are not said to differ in basis (${JSON.stringify(differ.slice(0, 120))})`);
      if (!(await count('[data-testid="compare-authored"]'))) problems.push('the authored compare is gone for the archived example');

      // OF-BLD-019 §3.R (findings 21, 16): a run the service holds for
      // sc-pha-1, made outside this browser, joins its column; and with two
      // flowsheets on the table each cell names its own flowsheet's input,
      // in the page and in the CSV.
      const phaRun = fixture('proforma-run.json');
      doubleState.proformaRunsOnFile.set('sc-pha-1', phaRun.artifactId);
      await compared(['sc-pha-1', 'sc-yeast-1', made]);
      await page.reload({ waitUntil: 'networkidle' });
      await page.locator('[data-testid="compare-input-row"][data-input="titre"] td[data-kind="record"]').first().waitFor({ timeout: 8000 }).catch(() => {});
      if (await count('[data-testid="compare-not-run"]')) problems.push('Compare does not read the run the service holds for sc-pha-1');
      const titreCells = await page.locator('[data-testid="compare-input-row"][data-input="titre"] td[data-kind]').allInnerTexts();
      if (!/^PHA titre at harvest: /.test(titreCells[0] ?? '') || !/^ethanol titre at harvest: /.test(titreCells[1] ?? ''))
        problems.push(`with two flowsheets an input cell is not labelled by its own flowsheet (${JSON.stringify(titreCells.map((t) => t.slice(0, 40)))})`);
      const [download] = await Promise.all([page.waitForEvent('download', { timeout: 8000 }).catch(() => null), page.locator('[data-testid="compare-csv"]').click()]);
      const csvText = download ? readFileSync(await download.path(), 'utf8') : '';
      const titreLine = csvText.split('\n').find((l) => l.startsWith('Input: titre') || l.startsWith('"Input: titre')) ?? '';
      if (!/PHA titre at harvest: /.test(titreLine) || !/ethanol titre at harvest: /.test(titreLine)) problems.push(`the comparison CSV labels an input with another flowsheet's name (${JSON.stringify(titreLine.slice(0, 160))})`);
    } catch (e) {
      problems.push(String(e).slice(0, 160));
    }
    if (problems.length) {
      compareFails++;
      console.log(`✗ compare      ${problems.join('; ')}`);
    } else {
      console.log('✓ compare      sc-yeast-1 and a scenario made from ethanol_glucose_v0 run and pin, and Compare sets them side by side from their runs: the price with its basis, every TEA line, every input with its source; the pins survive a reload; a PHA scenario with no run says so under the line that their bases differ, and the authored compare stays for the casein example');
    }
    await page.close();
  }

  // ── OF-BLD-019 §5.1 — a fermOS fit feeds the fermenter.
  //
  // With the switch off, sc-yeast-1's page offers "Use a fermOS fit": with no
  // fit on file it says how one gets made (Runbooks → Depositions, fit it in
  // fermOS); with the double's stand-in fit and forecast on file it lists
  // both with what each can feed and why not, and choosing the forecast
  // binds titre, yield and productivity to it, each shown as an artifact
  // with its link, the binding asked of the service with the fits; the
  // choice survives a reload, and stopping it puts the records back.
  // OF-BLD-019 §5.R: the Ceiling check reads the yield the forecast feeds
  // (finding 7); the index says the inputs have a fit chosen, not that the
  // service bound one (8); choosing the kinetic fit for titre and yield
  // leaves the forecast's productivity beside another titre, which the
  // service refuses in words naming titre (1); and stopping the forecast
  // clears its productivity alone, the fit's titre and yield staying (6).
  let fitFails = 0;
  {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    const problems = [];
    page.on('pageerror', (e) => problems.push(`page error: ${e.message}`));
    const fixture = JSON.parse(readFileSync(join(process.cwd(), 'core/tests/fixtures/prototype/proforma-bind-fits.json'), 'utf8')).response;
    const chosen = Object.values(fixture.fits)[0];
    const slot = page.locator('[data-testid="fermos-fit-slot"]');
    try {
      doubleState.flags.fermosFitsOnFile = false;
      await page.goto(`http://localhost:${PORT}/#/proforma/scenario/sc-yeast-1`, { waitUntil: 'networkidle' });
      await page.locator('[data-testid="fermos-fit-none"]').waitFor({ timeout: 8000 }).catch(() => {});
      const none = await slot.innerText({ timeout: 3000 }).catch(() => '');
      if (!/No fermOS fit is on file yet/.test(none) || !/Runbooks → Depositions/.test(none) || !/fit it in\s+fermOS/.test(none))
        problems.push(`with no fit on file the slot does not say how one gets made: ${JSON.stringify(none.slice(0, 200))}`);

      doubleState.flags.fermosFitsOnFile = true;
      await page.reload({ waitUntil: 'networkidle' });
      await page.locator('[data-testid="fermos-fit-option"]').first().waitFor({ timeout: 8000 }).catch(() => {});
      if ((await page.locator('[data-testid="fermos-fit-option"]').count()) !== 2) problems.push('the slot does not list the fit and the forecast on file');
      const fitOption = page.locator('[data-testid="fermos-fit-option"][data-feeds="2"]');
      if (!/does not run out within/.test(await fitOption.innerText({ timeout: 3000 }).catch(() => ''))) problems.push('the fit that gives no batch time does not say why');
      const option = page.locator(`[data-testid="fermos-fit-option"][data-artifact="${chosen}"]`);
      await option.locator('[data-testid="fermos-fit-use"]').click({ timeout: 8000 });
      await page.locator('[data-testid="param-row"][data-key="productivity"] [data-testid="param-chip"][data-origin="fit"]').waitFor({ timeout: 8000 }).catch(() => {});
      const shown = async () => {
        const lacks = [];
        for (const key of ['titre', 'yield', 'productivity']) {
          const cell = page.locator(`[data-testid="param-row"][data-key="${key}"] [data-testid="param-chip"][data-origin="fit"]`);
          if (!(await cell.count())) {
            lacks.push(key);
            continue;
          }
          const text = await cell.innerText({ timeout: 3000 }).catch(() => '');
          const link = await cell.getAttribute('href', { timeout: 3000 }).catch(() => null);
          if (!/artifact/.test(text) || link !== `#/biorepo/artifacts/${chosen}`) lacks.push(key);
        }
        return lacks;
      };
      const lacks = await shown();
      if (lacks.length) problems.push(`choosing the forecast does not show these inputs as its artifact: ${lacks.join(', ')}`);
      const asked = doubleState.proformaBinds.at(-1);
      if (!asked || JSON.stringify(Object.entries(JSON.parse(asked.fits)).sort()) !== JSON.stringify(Object.entries(fixture.fits).sort()))
        problems.push(`the binding was not asked of the service with the fits chosen: ${JSON.stringify(asked)}`);
      if (/Waiting for a source: [^.]*productivity/i.test(await page.locator('[data-testid="proforma-waiting"]').innerText({ timeout: 3000 }).catch(() => '')))
        problems.push('productivity still waits with the forecast chosen');
      // §5.R (7): the Ceiling check reads the yield the forecast feeds, as the service reads it.
      const ceilingSource = page.locator('[data-testid="ceiling-yield-source"]');
      await page.locator('[data-testid="ceiling-yield-source"][data-binding="artifact"]').waitFor({ timeout: 8000 }).catch(() => {});
      if (
        (await ceilingSource.getAttribute('data-binding', { timeout: 3000 }).catch(() => null)) !== 'artifact' ||
        (await ceilingSource.getAttribute('href', { timeout: 3000 }).catch(() => null)) !== `#/biorepo/artifacts/${chosen}`
      )
        problems.push('the ceiling check does not read the yield the chosen forecast feeds');
      // OF-BLD-020 §2.R (findings 8, 12, 13): a titre a person types beside the forecast chosen for every input wins over
      // the fit there. The fit's card and the line under the panel say whose value wins, and Run waits with the service's
      // words, which are the run's (the panel binds as the run binds); Reset to source takes the fit back and Run is free.
      const heldBy = JSON.parse(readFileSync(join(process.cwd(), 'core/tests/fixtures/prototype/params-proforma-fits.json'), 'utf8')).response.resolves[0];
      await page.goto(`http://localhost:${PORT}/#/settings/corpus`, { waitUntil: 'networkidle' });
      await page.locator('input[aria-label="Reviewer name"]').fill(REVIEWER);
      await page.waitForTimeout(400);
      await page.goto(`http://localhost:${PORT}/#/proforma/scenario/sc-yeast-1`, { waitUntil: 'networkidle' });
      await page.locator('[data-testid="param-row"][data-key="titre"] [data-testid="param-chip"][data-origin="fit"]').waitFor({ timeout: 8000 }).catch(() => {});
      await typeParam(page, 'plant_scale', 100000);
      await typeParam(page, 'glucose_price', 0.4);
      await typeParam(page, 'titre', 50);
      await page.locator('[data-testid="run-held"]').waitFor({ timeout: 8000 }).catch(() => {});
      const held = await page.locator('[data-testid="run-held"]').innerText({ timeout: 3000 }).catch(() => '');
      if (heldBy.status !== 422 || !held.includes(heldBy.body.detail) || !/titre is a named person's assumption/.test(held))
        problems.push(`with titre typed beside the forecast, Run does not wait with the service's words: ${JSON.stringify(held.slice(0, 200))}`);
      if (!(await page.getByRole('button', { name: /Run the scenario/ }).isDisabled().catch(() => false))) problems.push('Run is enabled for a run the service would refuse');
      if (await page.locator('[data-testid="proforma-waiting"]').count()) problems.push('an input still waits with every value typed');
      if ((await chipOf(page, 'titre')).origin !== 'assumption') problems.push('the typed titre is not the person\u2019s assumption');
      const card = (await option.innerText({ timeout: 3000 }).catch(() => '')).replace(/\s+/g, ' ');
      if (!/In use for yield, productivity\./.test(card) || /In use for titre/.test(card) || !card.includes(`titre, where ${REVIEWER}\u2019s value wins`))
        problems.push(`the forecast's card claims it feeds titre over the person's value: ${JSON.stringify(card.slice(-220))}`);
      const titreLine = page.locator('[data-testid="fit-line"][data-key="titre"]');
      if ((await titreLine.getAttribute('data-overridden', { timeout: 3000 }).catch(() => null)) !== 'true' ||
        !(await titreLine.innerText({ timeout: 3000 }).catch(() => '')).includes(`${REVIEWER}\u2019s value replaces the fermOS fit ${chosen}`))
        problems.push('the line under the panel still says titre is from the fit');
      await page.locator('[data-testid="param-row"][data-key="titre"] [data-testid="param-reset"]').click({ timeout: 8000 });
      await page.locator('[data-testid="param-row"][data-key="titre"] [data-testid="param-chip"][data-origin="fit"]').waitFor({ timeout: 8000 }).catch(() => {});
      await page.waitForTimeout(800);
      if (await page.locator('[data-testid="run-held"]').count()) problems.push('Run still waits once titre is reset to the fit');
      if (await page.getByRole('button', { name: /Run the scenario/ }).isDisabled().catch(() => true)) problems.push('Run stays disabled once titre is reset to the fit');
      if (!/In use for titre, yield, productivity\./.test(await option.innerText({ timeout: 3000 }).catch(() => ''))) problems.push('the reset titre is not the fit\u2019s again on its card');
      for (const key of ['plant_scale', 'glucose_price']) await page.locator(`[data-testid="param-row"][data-key="${key}"] [data-testid="param-reset"]`).click({ timeout: 8000 });
      await page.waitForTimeout(700);
      await page.reload({ waitUntil: 'networkidle' });
      await page.locator('[data-testid="param-row"][data-key="titre"] [data-testid="param-chip"][data-origin="fit"]').waitFor({ timeout: 8000 }).catch(() => {});
      if ((await shown()).length) problems.push('the fit chosen does not survive a reload');
      // §5.R (8): the index binds without the fits, so it says a fit is chosen, never that one is bound.
      await page.goto(`http://localhost:${PORT}/#/proforma`, { waitUntil: 'networkidle' });
      const indexCard = page.locator('[data-testid="biosteam-card"][data-scenario="sc-yeast-1"] [data-testid="scenario-inputs"]');
      await indexCard.waitFor({ timeout: 8000 }).catch(() => {});
      const counted = await indexCard.innerText({ timeout: 3000 }).catch(() => '');
      if (!/3 with a fermOS fit chosen/.test(counted) || /from a fermOS fit/.test(counted))
        problems.push(`the index does not say the inputs have a fit chosen: ${JSON.stringify(counted.slice(0, 160))}`);
      await page.goto(`http://localhost:${PORT}/#/proforma/scenario/sc-yeast-1`, { waitUntil: 'networkidle' });
      await page.locator('[data-testid="param-row"][data-key="titre"] [data-testid="param-chip"][data-origin="fit"]').waitFor({ timeout: 8000 }).catch(() => {});
      // §5.R (1): the kinetic fit for titre and yield leaves the forecast's productivity beside another titre: refused, naming titre.
      const kinetic = await fitOption.getAttribute('data-artifact', { timeout: 3000 }).catch(() => null);
      await fitOption.locator('[data-testid="fermos-fit-use"]').click({ timeout: 8000 });
      await page.locator('[data-testid="bind-problem"]').waitFor({ timeout: 8000 }).catch(() => {});
      const refusal = await page.locator('[data-testid="bind-problem"]').innerText({ timeout: 3000 }).catch(() => '');
      if (!refusal.includes(`productivity from growth_forecast ${chosen}`) || !refusal.includes(`titre is from ${kinetic}`))
        problems.push(`the forecast's productivity beside the fit's titre is not refused naming titre: ${JSON.stringify(refusal.slice(0, 200))}`);
      if (!/In use for productivity\./.test(await option.innerText({ timeout: 3000 }).catch(() => '')))
        problems.push("the forecast's card does not say it is in use for productivity alone");
      // §5.R (6): stopping the forecast clears its productivity alone; the fit's titre and yield stay.
      await option.locator('[data-testid="fermos-fit-stop"]').click({ timeout: 8000 });
      await page.locator('[data-testid="param-row"][data-key="productivity"] [data-testid="param-chip"][data-origin="record"]').waitFor({ timeout: 8000 }).catch(() => {});
      for (const key of ['titre', 'yield']) {
        const link = await page.locator(`[data-testid="param-row"][data-key="${key}"] [data-testid="param-chip"][data-origin="fit"]`).getAttribute('href', { timeout: 3000 }).catch(() => null);
        if (link !== `#/biorepo/artifacts/${kinetic}`) problems.push(`stopping the forecast cleared the fit chosen for ${key} (${link})`);
      }
      if (!(await page.locator('[data-testid="param-row"][data-key="productivity"] [data-testid="param-chip"][data-origin="record"]').count())) problems.push('stopping the forecast does not put the records back under productivity');
      if (!/In use for titre, yield\./.test(await fitOption.innerText({ timeout: 3000 }).catch(() => ''))) problems.push("the fit's card no longer says it is in use for titre and yield");
      await fitOption.locator('[data-testid="fermos-fit-stop"]').click({ timeout: 8000 });
      await page.locator('[data-testid="param-row"][data-key="titre"] [data-testid="param-chip"][data-origin="record"]').waitFor({ timeout: 8000 }).catch(() => {});
      if ((await page.locator('[data-testid="param-chip"][data-origin="fit"]').count()) !== 0) problems.push('stopping the fit does not put the records back');
    } catch (e) {
      problems.push(String(e).slice(0, 160));
    } finally {
      doubleState.flags.fermosFitsOnFile = false;
    }
    if (problems.length) {
      fitFails++;
      console.log(`✗ fermos fit   ${problems.join('; ')}`);
    } else {
      console.log("✓ fermos fit   sc-yeast-1 with no fit on file says how one gets made; with the fit and the forecast on file each says what it can feed and why not, choosing the forecast binds titre, yield and productivity to its artifact, asked of the service with the fits, read by the ceiling check, kept across a reload and counted on the index as chosen; a titre typed beside it wins there, the card and the line under the panel say whose value wins, and Run waits with the service's words until titre is reset; the fit's titre beside the forecast's productivity is refused naming titre, stopping the forecast clears its productivity alone, and stopping the fit puts the records back");
    }
    await page.close();
  }

  // ── OF-BLD-019 §5.2 — a scenario's yield read against the geneOS ceiling.
  //
  // With the switch off, sc-yeast-1's page asks the service for its Ceiling
  // check. With no ceiling on file (a fresh install) the card shows the
  // yield and its source and says no ceiling is on file, linking to geneOS →
  // Model on the product, the sugar and a model; with the double's STAND-IN
  // ceiling on file it shows both bases (the ceiling's model, sugar, value,
  // provenance and artifact link; the scenario's yield and its source) and
  // the flag in words, with the record above it linked to a reviewer. The
  // yield shown is the binding's own: nothing is clamped.
  let ceilingFails = 0;
  {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    const problems = [];
    page.on('pageerror', (e) => problems.push(`page error: ${e.message}`));
    page.on('console', (m) => {
      if (m.type() === 'error' && !IGNORE.some((re) => re.test(m.text()))) problems.push(m.text());
    });
    const answers = JSON.parse(readFileSync(join(process.cwd(), 'core/tests/fixtures/prototype/proforma-ceiling-check.json'), 'utf8')).response;
    const none = answers.none.ethanol_glucose_v0.body;
    const onFile = answers.onFile.ethanol_glucose_v0.body;
    const card = page.locator('[data-testid="ceiling-check"]');
    const close = (text, want) => Math.abs(Number(String(text).trim()) - want) < 1e-3;
    try {
      doubleState.flags.ceilingOnFile = false;
      await page.goto(`http://localhost:${PORT}/#/proforma/scenario/sc-yeast-1`, { waitUntil: 'networkidle' });
      await page.locator('[data-testid="ceiling-empty"]').waitFor({ timeout: 8000 }).catch(() => {});
      const empty = await page.locator('[data-testid="ceiling-empty"]').innerText({ timeout: 3000 }).catch(() => '');
      if (!/No geneOS ceiling for ethanol on glucose is on file/.test(empty) || !/geneOS → Model/.test(empty))
        problems.push(`with no ceiling on file the card does not say so and where one is computed: ${JSON.stringify(empty.slice(0, 200))}`);
      const compute = await page.locator('[data-testid="ceiling-compute"]').getAttribute('href', { timeout: 3000 }).catch(() => null);
      if (compute !== `#${none.computeAt}`) problems.push(`the empty card does not link to geneOS → Model on the product, sugar and model (${compute})`);
      const yieldLine = await page.locator('[data-testid="ceiling-yield"]').innerText({ timeout: 3000 }).catch(() => '');
      if (!yieldLine.includes(String(none.yieldValue)) || !/3 records/.test(yieldLine)) problems.push(`the card does not show the yield as bound, with its source: ${JSON.stringify(yieldLine.slice(0, 160))}`);
      if (await page.locator('[data-testid="ceiling-row"]').count()) problems.push('a ceiling is drawn with none on file');
      const asked = doubleState.ceilingChecks.at(-1);
      if (!asked || asked.scenarioId !== 'sc-yeast-1' || asked.includeArchived !== 'false' || 'flowsheet' in asked)
        problems.push(`the check was not asked for the seed scenario with the switch: ${JSON.stringify(asked)}`);

      doubleState.flags.ceilingOnFile = true;
      await page.reload({ waitUntil: 'networkidle' });
      await page.locator('[data-testid="ceiling-row"]').waitFor({ timeout: 8000 }).catch(() => {});
      const want = onFile.rows[0];
      const row = page.locator(`[data-testid="ceiling-row"][data-model="${want.modelId}"]`);
      if ((await row.getAttribute('data-flag', { timeout: 3000 }).catch(() => null)) !== 'above') problems.push('the row above its ceiling is not flagged above');
      if ((await card.getAttribute('data-flagged').catch(() => null)) !== 'true') problems.push('the card is not marked flagged');
      const ceilingRow = await row.locator('[data-testid="ceiling-ceiling"]').innerText({ timeout: 3000 }).catch(() => '');
      if (!ceilingRow.includes(want.modelId) || !/glucose/.test(ceilingRow) || !close(await row.locator('[data-testid="ceiling-value"]').innerText().catch(() => ''), want.ceilingGPerG))
        problems.push(`the ceiling's basis is not shown with its model, sugar and value: ${JSON.stringify(ceilingRow.slice(0, 200))}`);
      if ((await row.locator('[data-testid="ceiling-artifact"]').getAttribute('href').catch(() => null)) !== `#/biorepo/artifacts/${want.artifactId}`)
        problems.push('the ceiling does not link to its artifact');
      if (!ceilingRow.includes(want.modelBasis)) problems.push('the ceiling does not say what its basis names it (the STAND-IN label)');
      const scenarioRow = await row.locator('[data-testid="ceiling-scenario"]').innerText({ timeout: 3000 }).catch(() => '');
      if (!scenarioRow.includes(String(want.yieldGPerG)) || !scenarioRow.includes(String(want.yieldHighGPerG)))
        problems.push(`the scenario's yield is not shown beside the ceiling as bound, unclamped: ${JSON.stringify(scenarioRow.slice(0, 160))}`);
      const words = await row.locator('[data-testid="ceiling-words"]').innerText().catch(() => '');
      if (!/reviewer should check the basis/.test(words) || !/not clamped/.test(words)) problems.push(`the flag is not said in words: ${JSON.stringify(words.slice(0, 200))}`);
      const above = await row.locator('[data-testid="ceiling-record-above"]').allInnerTexts().catch(() => []);
      if (above.length !== want.recordsAbove.length || !above.every((t, i) => t.includes(want.recordsAbove[i])))
        problems.push(`the records above the ceiling are not listed for a reviewer (${above.length})`);
      if (!(await row.locator(`a[href="#/guild?record=${want.recordsAbove[0]}"]`).count())) problems.push('a record above the ceiling does not link to its review');
    } catch (e) {
      problems.push(String(e).slice(0, 160));
    } finally {
      doubleState.flags.ceilingOnFile = false;
    }
    if (problems.length) {
      ceilingFails++;
      console.log(`✗ ceiling      ${problems.join('; ')}`);
    } else {
      console.log('✓ ceiling      sc-yeast-1 with no ceiling on file shows its yield and source and says where one is computed; with the STAND-IN ceiling on file both bases show (model, sugar, value, provenance, artifact; the yield as bound, unclamped), flagged above in words, the record above it linked to a reviewer');
    }
    await page.close();
  }

  // ── OF-BLD-012 §5.4 — the overlay reaches the reader, and unanchored
  //    quotes are listed rather than dropped.
  //
  // The fixture replaces B5's curation note with the structural document, so
  // its three curated quotes cannot anchor. Every one of them has to be on
  // screen under the pending-verification heading with a link to its review
  // card, and the curator's-note banner has to be gone.
  let overlayFails = 0;
  {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    try {
      // B5 and its candidate are casein (OF-BLD-016 B.4): this flow walks
      // them with archived programs showing, as the golden path does.
      const archivedOn = await setShowArchived(page, true);
      await page.goto(`http://localhost:${PORT}/#/biorepo/paper/B5`, { waitUntil: 'networkidle' });
      await page.waitForTimeout(1200);
      const text = await page.locator('body').innerText();
      const problems = [];
      if (!archivedOn) problems.push('the archive switch did not turn on');
      if (!/Full text from Europe PMC/.test(text)) problems.push('no full-text banner');
      if (!/The abstract comes first/.test(text)) problems.push('the overlay sections did not render');
      if (/Catalogued from OF-COR-001/.test(text)) problems.push('the curation-note banner is still showing');
      // Sentence case on purpose: the heading is the spec's own phrase, and a
      // CSS text-transform would turn it into a different sentence on screen.
      if (!/Quote not found in source text — pending verification/.test(text)) {
        problems.push('unanchored quotes are not listed as pending verification');
      }
      for (const id of ['r-B5-1', 'r-B5-2', 'r-B5-3']) {
        if (!text.includes(id)) problems.push(`${id} is not on the page`);
      }
      const links = await page.locator('a[href="#/guild?record=r-B5-1"]').count();
      if (links === 0) problems.push('no link from the pending record to its review card');
      // The board shows the fetched paper as a real fetch, not a simulation.
      await page.goto(`http://localhost:${PORT}/#/intake/ingest`, { waitUntil: 'networkidle' });
      await page.waitForTimeout(900);
      const board = await page.locator('body').innerText();
      if (!/Live — fetching through openferment-core/.test(board)) problems.push('board does not say it is live');
      if (!/sections from Europe PMC/.test(board)) problems.push('B5 is not on the board as a real fetch');
      // §6.4 — Witness scores the overlay's run. No record carries real gold,
      // so provisional mode is on by default and labelled with the spec's
      // sentence; the fixture run is one match, one mismatch, one miss over
      // B5's three curated records, so the counts are fixed.
      await page.goto(`http://localhost:${PORT}/#/biorepo/witness`, { waitUntil: 'networkidle' });
      // Wait for the run's own label rather than a guessed sleep.
      await page.locator('text=claude-1').first().waitFor({ timeout: 8000 }).catch(() => {});
      await page.waitForTimeout(150);
      const witness = await page.locator('body').innerText();
      if (!/claude-1/.test(witness)) problems.push('Witness does not show the overlay run');
      // The run names the models from its usage records; the fixture records none.
      if (/Opus 5\.5, with Sonnet 5\.5/.test(witness)) problems.push('Witness still names a model the run did not record');
      if (!/Model not recorded/.test(witness)) problems.push('Witness does not say the fixture run recorded no model');
      if (!/Provisional — curated values from OF-COR-001 standing in as gold until a reviewer flags them in Guild\./.test(witness)) {
        problems.push('Witness is not labelled provisional');
      }
      // match_run over the fixture's two candidates: one candidate scores one
      // record, so one mismatch and two misses.
      if (!/tp 0 · fp 1 · fn 3/.test(witness)) problems.push('Witness did not score the fixture run as tp 0, fp 1, fn 3');
      if (/No extractor has been run against this corpus yet/.test(witness)) problems.push('Witness still shows the empty state');
      if (!/1 candidate new to the corpus — unscored/.test(witness)) problems.push('Witness does not count the one new candidate as unscored');
      // The extractor's own candidate is a record on a fetched paper, but it
      // is not gold to score the extractor against: three curated records
      // stand in, not four, and the run is not "partial".
      if (/Partial results/.test(witness)) problems.push('Witness counts the new candidate as provisional gold and calls the run partial');

      // OF-BLD-014 §3.2 — the artifact the prototype fixture holds is listed
      // with its provenance, its page shows each input's source, and Replay
      // says it replayed identically.
      await page.goto(`http://localhost:${PORT}/#/biorepo/artifacts`, { waitUntil: 'networkidle' });
      await page.locator('[data-testid="artifact-table"]').waitFor({ timeout: 8000 }).catch(() => {});
      const shelf = await page.locator('body').innerText();
      if (!/Inputs named in this basis/.test(shelf)) problems.push('Artifacts does not list the fixture artifact');
      if (!/Computed · basis attached/.test(shelf)) problems.push('Artifacts does not show the computed provenance');
      await page.goto(`http://localhost:${PORT}/#/biorepo/artifacts/02aef8a9e9cbaf88`, { waitUntil: 'networkidle' });
      await page.locator('[data-testid="artifact-inputs"]').waitFor({ timeout: 8000 }).catch(() => {});
      if ((await page.locator('[data-testid="artifact-inputs"] tbody tr').count()) !== 2)
        problems.push('the artifact page does not list its two inputs');
      if (!/convention — TEST FIXTURE/.test(await page.locator('body').innerText()))
        problems.push('the artifact page does not show the convention input with its note');
      await page.getByRole('button', { name: 'Replay' }).click();
      await page.locator('[data-testid="replay-result"]').waitFor({ timeout: 8000 }).catch(() => {});
      if (!/Replayed identically/.test(await page.locator('body').innerText()))
        problems.push('Replay did not say it replayed identically');

      // OF-BLD-014 §4.4 — search the papers, open a hit, land on its words;
      // Witness carries the retrieval scorecard with the lane in use marked.
      await page.goto(`http://localhost:${PORT}/#/biorepo/search`, { waitUntil: 'networkidle' });
      await page.locator('input[aria-label="Question"]').waitFor({ timeout: 8000 }).catch(() => {});
      await page.locator('input[aria-label="Question"]').fill('placeholder rows in the table');
      await page.getByRole('button', { name: 'Search', exact: true }).click();
      await page.locator('[data-testid="search-hit"]').first().waitFor({ timeout: 8000 }).catch(() => {});
      if ((await page.locator('[data-testid="search-hit"]').count()) === 0) problems.push('search showed no hit');
      if (!doubleState.ragSearches.some((q) => q.question === 'placeholder rows in the table'))
        problems.push('search did not post the question to the service');
      await page.locator('[data-testid="open-in-reader"]').first().click();
      await page.locator('[data-testid="quote-mark"]').waitFor({ timeout: 8000 }).catch(() => {});
      const marked = (await page.locator('[data-testid="quote-mark"]').innerText().catch(() => '')) ?? '';
      if (!/Placeholder A \| 7 \| mg L-1/.test(marked)) problems.push('the reader did not mark the searched words');
      await page.goto(`http://localhost:${PORT}/#/biorepo/witness`, { waitUntil: 'networkidle' });
      await page.locator('[data-testid="retrieval-table"]').waitFor({ timeout: 8000 }).catch(() => {});
      const card = (await page.locator('[data-testid="retrieval-scorecard"]').innerText().catch(() => '')) ?? '';
      if (!/in use: bm25/.test(card) || !/hybrid/.test(card)) problems.push('Witness does not show the retrieval scorecard');

      // OF-BLD-014 §5.4 — Postdoc: the steps draw as the double replays the
      // stream the real loop recorded, the claim shows its record's value
      // and its quoted sentence, the footer says why the loop stopped, and
      // the quote opens the reader on the paper's words. OF-BLD-016 §3.1:
      // there is no mode to choose; the service is the only path.
      await page.goto(`http://localhost:${PORT}/#/postdoc`, { waitUntil: 'networkidle' });
      if (await page.getByRole('button', { name: 'Scripted' }).count()) problems.push('Postdoc still offers a scripted mode');
      if ((await page.locator('[data-testid="suggested-prompt"]').count()) !== 11)
        problems.push(`Postdoc's empty state does not offer the yeast five and the six cross-module questions (${await page.locator('[data-testid="suggested-prompt"]').count()} offered)`);
      await page.locator('textarea[aria-label="Ask a question"]').fill('What does the stand-in table report for placeholder A?');
      await page.locator('textarea[aria-label="Ask a question"]').press('Enter');
      await page.locator('[data-testid="trace-step"]').first().waitFor({ timeout: 8000 }).catch(() => {});
      const early = await page.locator('[data-testid="trace-step"]').count();
      await page.locator('[data-testid="passage-quote"]').waitFor({ timeout: 8000 }).catch(() => {});
      if (early < 1 || early >= 4) problems.push(`the trace did not draw step by step (saw ${early} steps before the answer)`);
      if (!doubleState.asks.some((a) => a.path === '/api/ask/stream' && a.mode === 'agent'))
        problems.push('Postdoc live did not ask the stream in agent mode');
      const steps = await page.locator('[data-testid="trace-step"]').allInnerTexts();
      if (steps.length !== 4) problems.push(`the trace shows ${steps.length} steps, not 4`);
      // OF-BLD-015 §7.1 — the coverage pass is the first line, and opens to one line a module.
      if (!/Swept the modules for what the question names · searched eleven, found in none/.test(steps[0] ?? ''))
        problems.push('the first trace line is not the coverage pass');
      await page.locator('[data-testid="trace-step"] summary').nth(0).click();
      if ((await page.locator('[data-testid="trace-coverage"] li').count()) !== 11) problems.push('the coverage line does not open to the eleven modules');
      if (!/Searched eleven, found in none/.test(await page.locator('[data-testid="plan-coverage"]').innerText().catch(() => '')))
        problems.push('the footer does not say which modules were searched');
      if (!/Looked up records of secreted titer · 1 record/.test(steps[1] ?? '')) problems.push('the second trace line is not the record search in plain words');
      if (!/Searched the papers for "placeholder rows in the table" · 2 passages/.test(steps[2] ?? '')) problems.push('the third trace line is not the passage search');
      await page.locator('[data-testid="trace-step"] summary').nth(2).click();
      if (!/"query": "placeholder rows in the table"/.test(await page.locator('[data-testid="trace-input"]').nth(1).innerText().catch(() => '')))
        problems.push('a trace line does not open to its exact input');
      const answer = await page.locator('body').innerText();
      if (!/The stand-in table reports a secreted titer for placeholder condition A\./.test(answer)) problems.push('the live claim is missing');
      if (!/cl1-B5-a07dd73c/.test(answer)) problems.push("the live claim does not render its record's value");
      if (!/Placeholder A \| 7 \| mg L-1/.test(await page.locator('[data-testid="passage-quote"]').innerText()))
        problems.push('the live claim does not show its quoted sentence');
      const footer = (await page.locator('[data-testid="plan-footer"]').innerText().catch(() => '')) ?? '';
      if (!/2 tool calls; answered when it had what it needed/.test(footer)) problems.push(`the footer does not say why the loop stopped: ${footer}`);
      await page.locator('[data-testid="quote-in-reader"]').click();
      await page.locator('[data-testid="quote-mark"]').waitFor({ timeout: 8000 }).catch(() => {});
      if (!/Placeholder A \| 7 \| mg L-1/.test((await page.locator('[data-testid="quote-mark"]').innerText().catch(() => '')) ?? ''))
        problems.push('the quoted sentence did not open the reader on its words');
      // OF-BLD-014 §6.1, OF-BLD-016 §3.2 — the figure gallery: the legend
      // names all nine classes, and the one figure drawn is the ceiling the
      // double's artifact store keeps (no frontier is kept there), and
      // nothing invented is drawn. check:figures holds the table twins.
      await page.goto(`http://localhost:${PORT}/#/settings/figures`, { waitUntil: 'networkidle' });
      await page.locator('[data-testid="figures-from-artifacts"]').waitFor({ timeout: 8000 }).catch(() => {});
      if ((await page.locator('[data-testid="encoding-legend"] li').count()) !== 9) problems.push('the figure legend does not list nine provenances');
      if ((await page.locator('[data-testid="figure"]').count()) !== 1) problems.push('the gallery does not draw the one kept ceiling');
      if (/SAMPLE: invented values/.test(await page.locator('body').innerText())) problems.push('the gallery still draws invented values');
      // OF-BLD-014 §6.4 — geneOS → Model over the toy network's fixtures: a
      // dotted ceiling labelled with its model, the envelope, what the model
      // lacks, a sugar it cannot take up said in words; and the C. necator
      // strain page's card says its file is not on this machine.
      await page.goto(`http://localhost:${PORT}/#/geneos/model`, { waitUntil: 'networkidle' });
      await page.locator('[data-testid="frontier"]').waitFor({ timeout: 10000 }).catch(() => {});
      const modelView = await page.locator('[data-testid="geneos-model"]').innerText().catch(() => '');
      if (!/toy ceiling/.test(modelView)) problems.push('the Model view draws no ceiling labelled with its model');
      if ((await page.locator('[data-testid="strip-rule"]').count()) !== 1) problems.push('the Model view does not draw one rule for the one usable model');
      if (!/Nothing on this screen predicts what a vessel will produce/.test(modelView)) problems.push('the Model view does not repeat that a ceiling is no forecast');
      if (!/toy, for the mix: this reconstruction has no uptake reaction for xylose/.test(modelView)) problems.push('the Model view does not say the toy cannot take up xylose');
      if (!/RehMBEL1391: RehMBEL1391's file is not on this machine/.test(modelView)) problems.push('the Model view does not say the C. necator file is not here');
      if (!/A ceiling from flux balance analysis/.test(modelView)) problems.push('the ceiling figure lacks its fixed sentences');
      await page.locator('select[aria-label="Sugar fed"]').selectOption('xylose');
      await page.locator('text=toy: this reconstruction has no uptake reaction for xylose').waitFor({ timeout: 8000 }).catch(() => {});
      if (!doubleState.geneosCalls.some((c) => c.path === '/api/geneos/ceiling' && c.substrate === 'xylose'))
        problems.push('choosing xylose did not ask the service for its ceiling');
      if (!/toy: this reconstruction has no uptake reaction for xylose/.test(await page.locator('body').innerText()))
        problems.push('a sugar the model cannot take up is not said in words');
      await page.goto(`http://localhost:${PORT}/#/geneos/hosts/c-necator-h16`, { waitUntil: 'networkidle' });
      await page.locator('[data-testid="host-ceiling"]').waitFor({ timeout: 8000 }).catch(() => {});
      if (!/not on this machine: run pnpm geneos:fetch/.test(await page.locator('[data-testid="host-ceiling"]').innerText().catch(() => '')))
        problems.push("the C. necator strain page has no ceiling card saying its file is not here");
      // OF-BLD-014 §7.4, OF-BLD-016 §3.2 — fermOS with no deposited run:
      // it offers no invented run, names the readings to deposit and where,
      // and asks the service for no fit; Forecast says there is no fit yet.
      await page.goto(`http://localhost:${PORT}/#/fermos`, { waitUntil: 'networkidle' });
      await page.locator('[data-testid="fermos-empty"]').waitFor({ timeout: 8000 }).catch(() => {});
      const fermosEmpty = await page.locator('[data-testid="fermos-fits"]').innerText().catch(() => '');
      if (!/No run deposited yet/.test(fermosEmpty) || !/time of each sample/.test(fermosEmpty) || !/biomass/.test(fermosEmpty) || !/product/.test(fermosEmpty) || !/substrate/.test(fermosEmpty) || !/Runbooks → Depositions/.test(fermosEmpty))
        problems.push('fermOS with no run does not name the readings to deposit and where');
      if ((await page.getByRole('button', { name: /sample run/i }).count()) !== 0) problems.push('fermOS still offers an invented run');
      if (doubleState.fermosCalls.some((c) => c.path === '/api/fermos/fit')) problems.push('fermOS asked for a fit with no run deposited');
      // OF-BLD-019 §4.2 — Properties of a broth, with no titre record of an
      // active program on file: it says what fills it and asks nothing.
      const brothCard = await page.locator('[data-testid="broth-properties-empty"]').innerText().catch(() => '');
      if (!/No ethanol titre record/.test(brothCard) || !/thread Q/.test(brothCard) || !/Intake/.test(brothCard))
        problems.push('fermOS’s Properties card with no titre record does not say what fills it');
      if (doubleState.thermoCalls.some((c) => c.preset)) problems.push('fermOS asked thermosteam about a beer with no titre record picked');
      await page.goto(`http://localhost:${PORT}/#/fermos/forecast`, { waitUntil: 'networkidle' });
      if (!/No fit to forecast from yet/.test(await page.locator('body').innerText())) problems.push('fermOS → Forecast does not say there is no fit yet');
      // OF-BLD-014 §8.2, OF-BLD-019 §3.1, §3.3 — the benchmark's reference
      // card reads its newest reference run at
      // /api/proforma/reference/cornstover_benchmark, as every reference does:
      // with the double's run on file, its price, when it ran, the price the
      // package gave when Proforma was first built and a Rerun; on a service
      // whose simulator has yet to run (the same answer with no artifact), it
      // says so, names the expected price and the package, and offers a run
      // with the simulator's status line.
      await page.goto(`http://localhost:${PORT}/#/proforma`, { waitUntil: 'networkidle' });
      const benchCard = page.locator('[data-testid="reference-card"][data-flowsheet="cornstover_benchmark"]');
      await benchCard.locator('[data-testid="reference-result"]').waitFor({ timeout: 8000 }).catch(() => {});
      const ranBench = await benchCard.innerText().catch(() => '');
      if (!/Ran\s+2026-09-15/.test(ranBench) || !/Expected 1\.968/.test(ranBench) || !(await benchCard.locator('[data-testid="reference-price"]').count()) ||
        !(await benchCard.getByRole('button', { name: 'Rerun' }).count()))
        problems.push('the benchmark\u2019s reference card does not read its newest reference run with the price its package gave');
      // OF-BLD-019 §3.R (findings 18, 29): what the package set names the simulator the run was on.
      const benchSim = await benchCard.locator('details').textContent().catch(() => '');
      const ranSim = JSON.parse(readFileSync(join(process.cwd(), 'core/tests/fixtures/prototype/proforma-reference-cornstover_benchmark.json'), 'utf8')).response.artifact.output.simulator;
      if (!benchSim.includes(`on ${ranSim}`)) problems.push(`the benchmark card's disclosure does not name the simulator its run was on (${JSON.stringify(benchSim.slice(0, 120))})`);
      const benchRef = JSON.parse(readFileSync(join(process.cwd(), 'core/tests/fixtures/prototype/proforma-reference-cornstover_benchmark.json'), 'utf8')).response;
      await page.route('**/api/proforma/reference/cornstover_benchmark', (r) =>
        r.request().method() === 'GET' ? r.fulfill({ json: { ...benchRef, artifact: null } }) : r.continue(),
      );
      await page.goto(`http://localhost:${PORT}/#/settings`, { waitUntil: 'networkidle' });
      await page.goto(`http://localhost:${PORT}/#/proforma`, { waitUntil: 'networkidle' });
      await benchCard.locator('[data-testid="reference-not-run"]').waitFor({ timeout: 8000 }).catch(() => {});
      const bench = await benchCard.innerText().catch(() => '');
      await page.unroute('**/api/proforma/reference/cornstover_benchmark');
      if (!/Not run on this service yet/.test(bench) || !/biorefineries\.cornstover@2\.35\.1/.test(bench))
        problems.push('the benchmark\u2019s reference card does not show its empty state with the package it will run');
      if (!(await benchCard.getByRole('button', { name: 'Run' }).count())) problems.push('the benchmark\u2019s reference card offers no run');
      if (!/The simulator has not started on this service yet/.test(bench)) problems.push('the benchmark\u2019s reference card has no status line');
      // OF-BLD-019 §3.R (findings 0, 15, 22): a service that holds the
      // benchmark run kept before reference runs (OF-BLD-014 §8.2,
      // proforma_benchmark) and no reference run shows that run, price only,
      // said to be what it is, on the card and on the page; Run still makes
      // the full reference run. The legacy artifact is built here from the
      // reference fixture's own output, as GET /api/proforma/benchmark keeps it.
      {
        const o = benchRef.artifact.output;
        const legacy = {
          ...benchRef.artifact,
          id: 'b0b0b0b0b0b0b0b0',
          tool: 'proforma_benchmark',
          toolVersion: 'benchmark 1',
          output: { package: o.package, biosteam: o.simulator, mespUsdPerGal: o.mespUsdPerGal, mespUsdPerKg: o.mespUsdPerKg, settings: o.settings, references: o.references },
        };
        await page.route('**/api/proforma/reference/cornstover_benchmark', (r) =>
          r.request().method() === 'GET' ? r.fulfill({ json: { ...benchRef, artifact: null } }) : r.continue(),
        );
        await page.route('**/api/proforma/benchmark', (r) =>
          r.request().method() === 'GET' ? r.fulfill({ json: { artifact: legacy, simulator: { status: 'cold', error: null } } }) : r.continue(),
        );
        await page.goto(`http://localhost:${PORT}/#/settings`, { waitUntil: 'networkidle' });
        await page.goto(`http://localhost:${PORT}/#/proforma`, { waitUntil: 'networkidle' });
        await benchCard.locator('[data-testid="reference-result"]').waitFor({ timeout: 8000 }).catch(() => {});
        const kept = await benchCard.innerText().catch(() => '');
        const keptPrice = Number(await benchCard.locator('[data-testid="reference-price"]').innerText().catch(() => 'NaN'));
        if (!(Math.abs(keptPrice - o.mespUsdPerGal) < 1e-3) || !kept.includes(legacy.id) || /Not run on this service yet/.test(kept) || !/first built on BioSTEAM/.test(kept))
          problems.push(`the benchmark card does not show the benchmark run the service kept (${JSON.stringify(kept.slice(0, 200))})`);
        if (!(await benchCard.getByRole('button', { name: 'Run', exact: true }).count())) problems.push('the benchmark card does not offer the full reference run beside the kept benchmark');
        await page.goto(`http://localhost:${PORT}/#/proforma/reference/cornstover_benchmark`, { waitUntil: 'networkidle' });
        await page.locator('[data-testid="reference-price"]').waitFor({ timeout: 8000 }).catch(() => {});
        const keptPage = await page.locator('main').innerText().catch(() => '');
        if (!(Math.abs(Number(await page.locator('[data-testid="reference-price"]').innerText().catch(() => 'NaN')) - o.mespUsdPerGal) < 1e-3) ||
          !/first built on BioSTEAM/.test(await page.locator('[data-testid="reference-note"]').innerText().catch(() => '')) ||
          (await page.locator('[data-testid="regression-summary"]').count()) || /Not run on this service yet\. A run is/.test(keptPage))
          problems.push('the benchmark page does not show the kept benchmark run, price only, without claiming it was checked against the package\u2019s test');
        await page.unroute('**/api/proforma/reference/cornstover_benchmark');
        await page.unroute('**/api/proforma/benchmark');
      }
      // OF-BLD-016 §3.1 — Postdoc speaks only through the service. With
      // nothing answering (health and the ask both refused), the page says
      // so and how to start it, keeps the conversation asked above, and
      // keeps a question typed meanwhile in the box: nothing answers in the
      // service's place, and nothing typed is lost.
      await page.route('**/api/health', (r) => r.abort());
      await page.route('**/api/ask/stream', (r) => r.abort());
      await page.goto(`http://localhost:${PORT}/#/postdoc`, { waitUntil: 'networkidle' });
      await page.locator('[data-testid="postdoc-down"]').waitFor({ timeout: 8000 }).catch(() => {});
      const downNote = (await page.locator('[data-testid="postdoc-down"]').innerText().catch(() => '')) ?? '';
      if (!/Postdoc needs the service/.test(downNote) || !/Start it with pnpm prototype:up/.test(downNote))
        problems.push(`with the service down Postdoc does not say how to start it: ${JSON.stringify(downNote.slice(0, 120))}`);
      const turnsBefore = await page.locator('[data-testid="live-turn"]').count();
      const typedDown = 'What does the stand-in table report for placeholder B?';
      await page.locator('textarea[aria-label="Ask a question"]').fill(typedDown);
      await page.locator('textarea[aria-label="Ask a question"]').press('Enter');
      await page
        .waitForFunction((t) => document.querySelector('textarea[aria-label="Ask a question"]')?.value === t, typedDown, { timeout: 5000 })
        .catch(() => {});
      if ((await page.locator('textarea[aria-label="Ask a question"]').inputValue()) !== typedDown)
        problems.push('a question asked with the service down did not stay in the box');
      const turnsAfter = await page.locator('[data-testid="live-turn"]').count();
      if (turnsBefore !== 1 || turnsAfter !== 1)
        problems.push(`the conversation did not stay as it was with the service down (${turnsBefore} turns before, ${turnsAfter} after)`);
      if (doubleState.asks.some((a) => a.question === typedDown)) problems.push('a question asked with the service down reached the double');
      await page.unroute('**/api/health');
      await page.unroute('**/api/ask/stream');

      // §7.3 — the review card. The new candidate is in the queue, labelled;
      // accepting it posts a decision to the service. The curated record on
      // the same fetched paper shows the extractor's disagreeing span, and
      // gold is unavailable with the reason, because biorepo.write would
      // refuse it.
      // Opening Guild COLD — a fresh document, not this page, whose store
      // already holds the overlay. F9: the queue waits for /api/health and
      // then seeds with the records the service can KEEP, so it is the 82
      // seeded records on identified papers plus the new candidate on B5 —
      // 83, not all 135. The other 52 sit on papers with no PMCID, DOI or
      // PMID, and `biorepo.write` refuses every decision about them.
      // (That a candidate arriving joins an ALREADY OPEN queue is
      // `pnpm check:store`, which tests it without a clock.)
      // Opened on a deep link, `?record=r-B5-1`, which the queue focuses
      // ONCE when it seeds — see the unfiltered check below.
      // A new context starts with archived programs hidden, and these are
      // casein records: the switch goes on in Settings, and the reload makes
      // the document fresh again, the switch restored from the Durable tier.
      const coldPage = await browser.newPage({ viewport: { width: 1440, height: 900 } });
      if (!(await setShowArchived(coldPage, true))) problems.push('the archive switch did not turn on for the cold queue');
      await coldPage.goto(`http://localhost:${PORT}/#/guild?record=r-B5-1`, { waitUntil: 'networkidle' });
      await coldPage.reload({ waitUntil: 'networkidle' });
      // networkidle already covers the double's 700 ms overlay; give the
      // store one tick to apply it.
      await coldPage.waitForFunction(() => /\/ 83\b/.test(document.body.innerText), null, { timeout: 4000 }).catch(() => {});
      await coldPage.waitForTimeout(300);
      const cold = (await coldPage.locator('body').innerText()).replace(/\s+/g, ' ');
      if (!/\/ 83\b/.test(cold))
        problems.push(`the queue is not the 83 records the service would keep (progress reads ${(cold.match(/\d+ \/ \d+/) ?? ['?'])[0]})`);
      if (!/hiding 52 records on papers with no PMCID, DOI or PMID/.test(cold))
        problems.push(`the filter does not say what it is hiding (${(cold.match(/hiding[^,]*/) ?? ['—'])[0]})`);
      // And it is a filter, not a wall: the refused records are still
      // reviewable in this browser, and unticking gives them back. The
      // rebuilt queue starts at its first card: the deep link above was
      // honoured once, when the queue seeded, and a queue that changes
      // length afterwards must not snap the reviewer back to `?record=` —
      // which is what an effect keyed on the queue's length did.
      await coldPage.locator('#keepable-only').uncheck();
      await coldPage.waitForTimeout(200);
      const unfiltered = (await coldPage.locator('body').innerText()).replace(/\s+/g, ' ');
      await coldPage.close();
      if (!/\/ 135\b/.test(unfiltered))
        problems.push(`unticking the filter did not give the refused records back (progress reads ${(unfiltered.match(/\d+ \/ \d+/) ?? ['?'])[0]})`);
      else if (!/\b1 \/ 135\b/.test(unfiltered))
        problems.push(`the rebuilt queue snapped back to the deep-linked record instead of starting at its first card (progress reads ${(unfiltered.match(/\d+ \/ \d+/) ?? ['?'])[0]})`);

      await page.goto(`http://localhost:${PORT}/#/guild?record=cl1-B5-a07dd73c`, { waitUntil: 'networkidle' });
      // A hash navigation on the same document returns at once; wait for the
      // card itself, not a clock.
      await page.locator('text=cl1-B5-a07dd73c').first().waitFor({ timeout: 8000 }).catch(() => {});
      await page.waitForTimeout(150);
      const newCard = await page.locator('body').innerText();
      if (!/Extracted by claude-1 — new to the corpus/.test(newCard)) problems.push('the new candidate is not labelled as new to the corpus');
      if (!/Placeholder A \| 7 \| mg L-1/.test(newCard)) problems.push('the new candidate\'s quote is not on its card');
      // Nobody can decide anything the committed file would keep until they
      // have said who they are (OF-BLD-012.1 F2) — so the card refuses first,
      // and the name set in Settings is what the decision is signed with.
      const beforeNaming = await page.locator('body').innerText();
      if (!/Set your reviewer name in Settings/.test(beforeNaming)) {
        problems.push('an unnamed reviewer is not told to set a name before deciding');
      }
      if (!(await page.locator('button:has-text("Accept")').isDisabled())) {
        problems.push('accept is enabled for a reviewer with no name');
      }
      // OF-BLD-015 §7.4 — a proposal waits on Home; unsigned, its buttons do nothing.
      await page.goto(`http://localhost:${PORT}/#/`, { waitUntil: 'networkidle' });
      await page.locator('[data-testid="home-proposals"]').waitFor({ timeout: 8000 }).catch(() => {});
      if ((await page.locator('[data-testid="home-proposal"]').count()) !== 1) problems.push('Home does not show the one proposal the service holds');
      if ((await page.locator('[data-testid="home-proposals-unsigned"]').count()) !== 1) problems.push('an unnamed reviewer is not told to set a name before acting on a proposal');
      if (!(await page.locator('[data-testid="home-proposal"] button').first().isDisabled())) problems.push('a proposal button is enabled for a reviewer with no name');
      await page.goto(`http://localhost:${PORT}/#/settings/corpus`, { waitUntil: 'networkidle' });
      await page.locator('input[aria-label="Reviewer name"]').fill(REVIEWER);
      await page.waitForTimeout(400);
      await page.goto(`http://localhost:${PORT}/#/`, { waitUntil: 'networkidle' });
      await page.locator('[data-testid="home-proposal"] button').first().waitFor({ timeout: 8000 }).catch(() => {});
      const proposalButton = (await page.locator('[data-testid="home-proposal"] button').first().innerText().catch(() => '')).trim();
      if (!/Lock predictions/.test(proposalButton)) problems.push(`the proposal's button does not say what the gate does: ${JSON.stringify(proposalButton)}`);
      await page.locator('[data-testid="home-proposal"] button').first().click();
      await page.waitForTimeout(700);
      const acted = doubleState.proposalActs[0];
      if (!acted) problems.push('pressing the proposal button posted nothing to the service');
      else if (acted.verb !== 'carry-out' || acted.person !== REVIEWER) problems.push(`the proposal was acted on as ${JSON.stringify(acted)}, not carried out by the name in Settings`);
      if (!/#\/runbooks/.test(page.url())) problems.push(`carrying out a browser-side gate did not take the person to the runbooks: ${page.url()}`);
      await page.goto(`http://localhost:${PORT}/#/`, { waitUntil: 'networkidle' });
      await page.waitForTimeout(500);
      if ((await page.locator('[data-testid="home-proposal"]').count()) !== 0) problems.push('a carried-out proposal is still on Home');
      await page.goto(`http://localhost:${PORT}/#/guild?record=cl1-B5-a07dd73c`, { waitUntil: 'networkidle' });
      await page.locator('text=cl1-B5-a07dd73c').first().waitFor({ timeout: 8000 }).catch(() => {});
      await page.waitForTimeout(700);
      await page.keyboard.press('a');
      await page.waitForTimeout(700);
      const posted = decisions.find((d) => d.recordId === 'cl1-B5-a07dd73c');
      if (!posted) problems.push('accepting the new candidate posted no decision to the service');
      else if (posted.status !== 'verified' || !posted.at) problems.push(`the posted decision is wrong: ${JSON.stringify(posted)}`);
      else if (posted.reviewer !== REVIEWER) problems.push(`the decision is signed ${JSON.stringify(posted.reviewer)}, not the name set in Settings`);

      await page.goto(`http://localhost:${PORT}/#/guild?record=r-B5-1`, { waitUntil: 'networkidle' });
      await page.locator('[data-testid="extractor-span"]').first().waitFor({ timeout: 8000 }).catch(() => {});
      // Long enough for the 300 ms debounce on POST /api/biorepo/check to
      // have asked and answered (OF-BLD-012.1 F1.5).
      await page.waitForTimeout(700);
      const curatedCard = await page.locator('body').innerText();
      if (!/what the extractor read/i.test(curatedCard)) problems.push('the curated record on a fetched paper shows no extractor block');
      if (!/Disagrees — extractor 7 d vs curated 8\.5 d \(-18 %\)/.test(curatedCard)) problems.push('the extractor\'s disagreeing span is not labelled with its delta');
      const goldDisabled = await page.locator('button:has-text("Flag for gold")').isDisabled();
      if (!goldDisabled) problems.push('gold is enabled on a record biorepo.write would refuse');
      if (!/Gold is unavailable here: Gold needs a sentence in the fetched text/.test(curatedCard)) problems.push('the gold refusal is not explained on the card');
      const askedAbout = checks.filter((c) => c.recordId === 'r-B5-1');
      if (!askedAbout.some((c) => c.gold)) problems.push('the card never asked the service whether gold would be kept');
      if (!askedAbout.some((c) => !c.gold)) problems.push('the card never asked the service whether accept would be kept');
      const reader = await page.locator('a[href="#/biorepo/paper/B5?section=t1"]').count();
      if (reader === 0) problems.push('no link from the extractor span to the reader at its section');
      if (problems.length) {
        overlayFails++;
        console.log(`✗ overlay      ${problems.join('; ')}`);
      } else {
        console.log('✓ overlay      B5 shows the fetched text; 3 unanchored quotes listed, each linked to review; Witness scores the run provisionally; Guild shows the extractor\'s span and posts the decision; Postdoc draws its steps, quotes the table row and opens the reader on it, and with the service down says how to start it and keeps the conversation and the typed question; the figure gallery draws the kept ceiling and nothing invented; geneOS draws a ceiling beside what was reported; fermOS with no run names the readings to deposit');
      }
    } catch (e) {
      overlayFails++;
      console.log(`✗ overlay      ${String(e).slice(0, 160)}`);
    }
    await page.close();
  }

  // ── OF-BLD-016 §3.2 — empty states name the next step ───────────────
  //
  // With nothing answering under /api, the app is the seed alone: Witness
  // says no extractor has run, fermOS names the readings to deposit, and
  // Guild says how to add the first person. None offers anything invented.
  let emptyFails = 0;
  {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    const problems = [];
    page.on('pageerror', (e) => problems.push(`page error: ${e.message}`));
    try {
      await page.route('**/api/**', (r) => r.abort());
      await page.goto(`http://localhost:${PORT}/#/biorepo/witness`, { waitUntil: 'networkidle' });
      await page.waitForTimeout(500);
      const witness = await page.locator('body').innerText();
      if (!/No extractor has been run against this corpus yet/.test(witness)) problems.push('Witness on the seed alone does not say no extractor has run');
      await page.goto(`http://localhost:${PORT}/#/fermos`, { waitUntil: 'networkidle' });
      await page.waitForTimeout(300);
      const fermos = await page.locator('body').innerText();
      if (!/No run deposited yet/.test(fermos) || !/time of each sample/.test(fermos)) problems.push('fermOS on the seed alone does not name the readings to deposit');
      await page.goto(`http://localhost:${PORT}/#/guild/matrix`, { waitUntil: 'networkidle' });
      await page.waitForTimeout(300);
      const guild = await page.locator('body').innerText();
      if (!/Nobody is on the ledger yet/.test(guild) || !/Add yourself below as the lead/.test(guild)) problems.push('Guild on the seed alone does not say how to add the first person');
      if (/sample team|sample run/i.test(witness + fermos + guild)) problems.push('an empty state still offers something invented');
    } catch (e) {
      problems.push(String(e).slice(0, 160));
    }
    if (problems.length) {
      emptyFails++;
      console.log(`✗ empty        ${problems.join('; ')}`);
    } else {
      console.log('✓ empty        with the service down, Witness says no extractor has run, fermOS names the readings to deposit, Guild says how to add the first person');
    }
    await page.close();
  }

  // ── OF-BLD-013 — the competence ledger, end to end in one browser ────
  //
  // OF-BLD-016 §3.2: the invented sample team left the screens. A fresh
  // browser shows the empty ledger and says how to add the first person,
  // with no invented team on offer; My path says the same; a practice
  // session runs on nobody's record. Then the real ledger: its first person
  // is its lead, posted to the service as one, and still there after a
  // reload. The ladder of levels (a suspension, a lapse, sign-offs, the
  // bench's queue) is held in memory by check:guild on the ladder team.
  let guildFails = 0;
  {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    const problems = [];
    page.on('pageerror', (e) => problems.push(`page error: ${e.message}`));
    try {
      await page.goto(`http://localhost:${PORT}/#/guild/matrix`, { waitUntil: 'networkidle' });
      await page.waitForTimeout(500);
      const emptyLedger = await page.locator('body').innerText();
      if (!/Nobody is on the ledger yet/.test(emptyLedger)) problems.push('a fresh browser does not show the empty ledger');
      if (!/Add yourself below as the lead/.test(emptyLedger)) problems.push('the empty ledger does not say how to add the first person');
      if ((await page.locator('#person-name').count()) !== 1) problems.push('the empty ledger offers no form for the first person');
      if (/sample team/i.test(emptyLedger)) problems.push('Guild still offers an invented team');
      // OF-BLD-014 §8.4 — the BioSTEAM scenario. Four inputs arrive bound to
      // (stand-in) records; the three that wait are typed as assumptions under
      // the reviewer's name, kept, and posted with the run; the run draws a
      // distribution with its infeasible count, a tornado, the sliders and the
      // questions for a process modeller, strongest mover first.
      await page.goto(`http://localhost:${PORT}/#/proforma/scenario/sc-pha-1`, { waitUntil: 'networkidle' });
      await page.locator('[data-testid="proforma-inputs"]').waitFor({ timeout: 8000 }).catch(() => {});
      await page.locator('[data-testid="param-row"]').first().waitFor({ timeout: 8000 }).catch(() => {});
      if (!/Set a reviewer name in Settings/.test(await page.locator('body').innerText()) ||
        !(await page.locator('[data-testid="param-row"][data-key="recovery"] [data-testid="param-value-input"]').isDisabled().catch(() => false)))
        problems.push('an unnamed person is offered a value to type');
      await page.goto(`http://localhost:${PORT}/#/settings/corpus`, { waitUntil: 'networkidle' });
      await page.locator('input[aria-label="Reviewer name"]').fill(REVIEWER);
      await page.waitForTimeout(400);
      await page.goto(`http://localhost:${PORT}/#/proforma/scenario/sc-pha-1`, { waitUntil: 'networkidle' });
      await page.locator('[data-testid="proforma-inputs"]').waitFor({ timeout: 8000 }).catch(() => {});
      const pf = await page.locator('[data-testid="proforma-biosteam"]').innerText().catch(() => '');
      if (!/BioSTEAM flowsheet, draft v0 — fermentation, harvest and drying only/.test(pf)) problems.push('sc-pha-1 does not carry its draft header');
      if (!/Waiting for a source: solids recovered at harvest, price of fermentable sugar, sugar fed/.test(pf)) problems.push('the inputs waiting for a source are not named');
      if (!(await page.getByRole('button', { name: 'Run the scenario' }).isDisabled())) problems.push('the run is offered while inputs wait for a source');
      for (const [key, value, low, high] of [['recovery', 0.95, 0.9, 0.98], ['sugarPrice', 0.4, 0.3, 0.5], ['sugarFeed', 10000, null, null]])
        await typeParam(page, key, value, { low, high });
      if ((await page.locator('[data-testid="param-chip"][data-origin="assumption"]').count()) !== 3) problems.push('three typed values do not each show who made them');
      await page.getByRole('button', { name: 'Run the scenario' }).click();
      await page.locator('[data-testid="distribution"]').waitFor({ timeout: 8000 }).catch(() => {});
      if ((await page.locator('[data-testid="distribution-bin"]').count()) !== 20) problems.push('the distribution does not draw twenty bins');
      if ((await page.locator('[data-testid="distribution-quantile"]').count()) !== 5) problems.push('the distribution does not draw five percentile rules');
      if (!/490 of 500 samples ran; 10 left no sugar for respiration/.test(await page.locator('body').innerText())) problems.push('the infeasible count is not printed beside the distribution');
      if ((await page.locator('[data-testid="tornado-row"]').count()) !== 6) problems.push('the tornado does not draw a row per varying input');
      if (!(await page.locator('[data-testid="slider-price"]').count())) problems.push('the sliders do not read the run\'s grid');
      const qs = await page.locator('[data-testid="modeller-questions"] li').allInnerTexts();
      if (!/^price of fermentable sugar/.test(qs[0] ?? '')) problems.push('the questions do not lead with the input that moves the price most');
      const posted = doubleState.proformaRuns.at(-1);
      if (!posted || posted.overrides?.length !== 3 || posted.overrides.some((o) => o.by !== REVIEWER))
        problems.push('the run did not post the three overrides signed with the reviewer\'s name');
      // OF-BLD-014 §9.2 and §9.4 — Postdoc drafts a runbook from a forecast,
      // a price and a record; the service wrote every number; adopting it
      // opens an unlocked research runbook whose page draws its predictions
      // and the chain behind them, forecast then price, with the seam between.
      await page.goto(`http://localhost:${PORT}/#/postdoc`, { waitUntil: 'networkidle' });
      await page.locator('textarea[aria-label="Ask a question"]').fill('Draft a runbook for the stand-in run.');
      await page.locator('textarea[aria-label="Ask a question"]').press('Enter');
      await page.locator('[data-testid="runbook-draft"]').waitFor({ timeout: 10000 }).catch(() => {});
      const draftCard = await page.locator('[data-testid="runbook-draft"]').innerText().catch(() => '');
      if (!/The stand-in run, forecast and priced/.test(draftCard) || !/Range of 1 reported value: cl1-B5-a07dd73c/.test(draftCard))
        problems.push('the plan does not show the drafted runbook with the basis the service wrote');
      await page.getByRole('button', { name: 'Turn into a runbook' }).click();
      await page.locator('[data-testid="dossier-link"]').first().waitFor({ timeout: 10000 }).catch(() => {});
      if (!/#\/runbooks\/rb-draft-/.test(page.url())) problems.push('adopting the draft did not open its runbook');
      if (!/not yet locked/.test(await page.locator('body').innerText())) problems.push('an adopted draft is not unlocked');
      if ((await page.locator('[data-testid="ledger-row"]').count()) !== 4) problems.push('the adopted runbook does not draw its four predictions');
      const tools = await page.locator('[data-testid="dossier-link"]').evaluateAll((els) => els.map((e) => e.getAttribute('data-tool')).join());
      if (tools !== 'geneos.ceiling,growth_forecast,proforma.run') problems.push(`the dossier does not draw the ceiling, the forecast, then the price: ${tools}`);
      const seams = (await page.locator('[data-testid="dossier-seam"]').allInnerTexts()).join(' | ');
      if (!/stoichiometry/.test(seams) || !/harvest step/.test(seams)) problems.push(`the dossier's two seams are not both there: ${seams}`);
      // The ceiling is drawn as a rule from its artifact, beside the records of its sugar.
      if ((await page.locator('[data-testid="dossier-link"][data-tool="geneos.ceiling"] [data-testid="strip-rule"]').count()) !== 1)
        problems.push('the dossier does not draw the ceiling as a rule');
      if (!/Stands behind the prediction Final product/.test(await page.locator('[data-testid="dossier"]').innerText().catch(() => '')))
        problems.push('a dossier figure does not name the prediction it stands behind');
      // My path reads the same ledger, and says how to start it.
      await page.evaluate(() => (location.hash = '#/primer/path'));
      await page.waitForTimeout(400);
      const pathEmpty = await page.locator('main').innerText();
      if (!/Nobody is on Guild’s ledger yet/.test(pathEmpty) || !/Add the first person/.test(pathEmpty))
        problems.push('My path does not say how to start the ledger');
      // §4 — practice: a draft, three answers to the tutor, and the close, on nobody's record
      // while nobody is on the ledger.
      await page.evaluate(() => (location.hash = '#/primer/practice?skill=SK-OD'));
      await page.waitForTimeout(500);
      await page.locator('button:has-text("Draft a scenario")').first().click();
      await page.waitForTimeout(600);
      let player = await page.locator('main').innerText();
      if (!/A reading above the linear range[\s\S]*Evidence[\s\S]*The blank medium[\s\S]*250[\s\S]*mL/.test(player))
        problems.push('a drafted scenario does not show its evidence pane with the value from its source');
      if ((await page.locator('button.chip:has-text("Step o4 of PR-OD-01")').count()) < 1)
        problems.push('a [v1] mark in the situation is not shown as its evidence item');
      for (const said of ['I would dilute it and read again', 'Because above the range it stops tracking biomass', 'Into the same spent medium']) {
        await page.fill('#practice-answer', said);
        await page.locator('button:has-text("Send answer")').click();
        await page.waitForTimeout(500);
      }
      player = await page.locator('main').innerText();
      if (!/Tutor · Asks why[\s\S]*Tutor · Closes[\s\S]*What the tutor observed[\s\S]*Chose to dilute/.test(player))
        problems.push('the tutor did not question and then close with what it observed');
      if (!/On nobody’s record: nobody was chosen as learning/.test(player))
        problems.push('a closed session with nobody learning does not say it is on nobody\u2019s record');
      if (practicePosts.some((x) => x.body.personId != null)) problems.push('a person was named to the service in Practice with nobody learning');
      await page.evaluate(() => (location.hash = '#/guild/matrix'));
      await page.waitForTimeout(300);
      if (guildPosts.length) problems.push(`the browser sent ${guildPosts.length} Guild write(s) before anyone was added`);
      await page.fill('#person-name', 'Smoke Lead');
      await page.locator('button:has-text("Start the ledger as its lead")').click();
      await page.waitForTimeout(800);
      const first = guildPosts.find((x) => x.url === '/api/guild/people');
      if (!first || first.body.role !== 'lead' || first.body.addedBy !== null) problems.push('the first person was not posted as the lead, added by nobody');
      await page.reload({ waitUntil: 'networkidle' });
      await page.waitForTimeout(1200);
      const after = await page.locator('body').innerText();
      if (!/Smoke Lead/.test(after)) problems.push('the first person did not come back from the service after a reload');
      if (/kept in this browser/.test(after)) problems.push('a change the service stored is still said to be waiting');
    } catch (e) {
      problems.push(String(e).slice(0, 160));
    }
    if (problems.length) {
      guildFails++;
      console.log(`✗ guild        ${problems.join('; ')}`);
    } else {
      console.log('✓ guild        the empty ledger says how to add the first person and offers no invented team; My path says the same; a practice session closes on nobody\u2019s record; the first person is posted as lead and comes back after a reload');
    }
    await page.close();
  }

  // ── OF-BLD-019 §4.1 — pureOS reads the train from the run Proforma priced.
  //
  // With the switch off the front page lists no train and says whose it hides
  // and how a run gets there. The train of sc-pha-1 (the double's run, PHA's)
  // opens by link under its banner: three units in run order, the first
  // forming the product and drawing no bar, the centrifuge's recovery as the
  // service read it; a click cuts the stream table to that unit's streams,
  // and a vocabulary step linked by ?op= is outlined on the front page.
  // §7.R: with the double's yeast run on file the list holds the yeast
  // train (the empty list is drawn with flags.pureosYeastOnFile off), and
  // sc-yeast-1's page links to its run's train: R1, D302, U301 in run
  // order, Properties on the beer and the ethanol.
  let trainFails = 0;
  {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    const problems = [];
    page.on('pageerror', (e) => problems.push(`page error: ${e.message}`));
    const fixture = (name) => JSON.parse(readFileSync(join(process.cwd(), 'core/tests/fixtures/prototype', name), 'utf8')).response;
    try {
      // §7.R: with no yeast run on file the list for the active program is
      // empty and says so; with the double's yeast run it lists that train
      // and says it hides PHA's.
      doubleState.flags.pureosYeastOnFile = false;
      await page.goto(`http://localhost:${PORT}/#/pureos`, { waitUntil: 'networkidle' });
      await page.locator('[data-testid="pureos-trains-empty"]').waitFor({ timeout: 8000 }).catch(() => {});
      const empty = await page.locator('[data-testid="pureos-trains-empty"]').innerText().catch(() => '');
      if (!/No train for an active program/.test(empty) || !/Proforma/.test(empty)) problems.push(`the empty list does not say how a train gets there: ${JSON.stringify(empty.slice(0, 160))}`);
      if (!/PHA/.test(empty)) problems.push('the empty list does not say it hides a PHA train');
      doubleState.flags.pureosYeastOnFile = true;
      await page.reload({ waitUntil: 'networkidle' });
      await page.locator('[data-testid="pureos-train-row"]').first().waitFor({ timeout: 8000 }).catch(() => {});
      const rows = await page.locator('[data-testid="pureos-train-row"]').allInnerTexts();
      const yeastName = fixture('pureos-train-yeast.json').scenarioName;
      if (rows.length !== 1 || !rows[0].includes(yeastName)) problems.push(`the active program's list is not the yeast train alone: ${JSON.stringify(rows)}`);
      if (await page.locator('[data-testid="pureos-trains-empty"]').count()) problems.push('the empty list shows beside the yeast train');
      if (!/PHA/.test(await page.locator('[data-testid="pureos-trains"]').innerText().catch(() => ''))) problems.push('the list does not say it hides a PHA train');
      await page.goto(`http://localhost:${PORT}/#/pureos/train/sc-pha-1`, { waitUntil: 'networkidle' });
      await page.locator('[data-testid="train-unit"]').first().waitFor({ timeout: 8000 }).catch(() => {});
      if ((await page.locator('[role="note"][data-archived-program="pha"]').count()) !== 1) problems.push('the train of a PHA scenario does not open under its banner');
      const units = await page.locator('[data-testid="train-unit"]').evaluateAll((els) => els.map((e) => e.getAttribute('data-unit')).join());
      if (units !== 'R1,C1,D1') problems.push(`the units are not listed in run order: ${units}`);
      const bars = await page.locator('[data-testid="recovery-row"]').evaluateAll((els) => els.map((e) => `${e.getAttribute('data-unit')}:${e.getAttribute('data-bar')}`).join());
      if (bars !== 'R1:none,C1:drawn,D1:drawn') problems.push(`the recovery figure draws ${bars}`);
      const body = await page.locator('main').innerText();
      if (!/no PHB enters R1: the product is formed here/.test(body)) problems.push('a unit no product enters does not say so');
      if (!/95\.0%/.test(body)) problems.push("the centrifuge's recovery is not shown as the service read it");
      await page.locator('[data-testid="train-unit"][data-unit="C1"] button').first().click();
      await page.waitForTimeout(300);
      const cut = await page.locator('[data-testid="train-stream"]').evaluateAll((els) => els.map((e) => e.getAttribute('data-stream')).join());
      if (cut !== 'broth,spent_medium,wet_solids') problems.push(`clicking C1 shows the streams ${cut}`);
      await page.locator('[data-testid="train-streams-all"]').click();
      await page.waitForTimeout(300);
      if ((await page.locator('[data-testid="train-stream"]').count()) !== 6) problems.push('Show every stream does not bring the whole table back');
      // OF-BLD-019 §4.2 — the Properties card opens on the broth and the
      // product, reads what is stored for each (nothing yet) and asks on a
      // press: the double's stand-in refuses the PHA broth's chemicals in
      // words, as thermosteam refuses one its library lacks. Another stream
      // picked is answered with the library's name and its artifact, and on
      // the next visit it is read back from what is stored without asking.
      const panels = await page.locator('[data-testid="thermo-panel"]').evaluateAll((els) => els.map((e) => e.getAttribute('data-stream')).join());
      if (panels !== 'broth,product') problems.push(`the Properties card opens on ${panels}`);
      const broth = page.locator('[data-testid="thermo-panel"][data-stream="broth"]');
      await broth.getByRole('button', { name: 'Ask thermosteam' }).click();
      await broth.locator('[data-testid="thermo-refused"]').waitFor({ timeout: 8000 }).catch(() => {});
      if (!/it has no Cells, PHB/.test(await broth.innerText().catch(() => ''))) problems.push('a chemical the library lacks is not refused in words');
      await page.locator('select[aria-label="Another stream"]').selectOption('process_water');
      const water = page.locator('[data-testid="thermo-panel"][data-stream="process_water"]');
      await water.getByRole('button', { name: 'Ask thermosteam' }).click();
      await water.locator('[data-testid="thermo-props"]').waitFor({ timeout: 8000 }).catch(() => {});
      const answer = await water.innerText().catch(() => '');
      if (!/Density/.test(answer) || !/kg\/m\^3/.test(answer) || !/Bubble point/.test(answer) || !/Computed by STAND-IN/.test(answer) || !/Artifact\s+[0-9a-f]{16}/.test(answer))
        problems.push(`the answer for a stream does not show its properties, library and artifact: ${JSON.stringify(answer.slice(-260))}`);
      const asked = doubleState.thermoCalls.filter((c) => c.method === 'POST').length;
      await page.reload({ waitUntil: 'networkidle' });
      await page.locator('[data-testid="train-unit"]').first().waitFor({ timeout: 8000 }).catch(() => {});
      await page.locator('select[aria-label="Another stream"]').selectOption('process_water');
      await water.locator('[data-testid="thermo-props"]').waitFor({ timeout: 8000 }).catch(() => {});
      if ((await water.locator('[data-testid="thermo-props"]').count()) !== 1) problems.push('a stored answer is not read back on the next visit');
      if (doubleState.thermoCalls.filter((c) => c.method === 'POST').length !== asked) problems.push('reading a stored answer asked thermosteam again');
      // §7.R (finding 0): Appendix 1's last step. The yeast scenario's run
      // on file, its page links to pureOS's train of that run; the train
      // opens with the run's units in run order, and its Properties card
      // opens on the beer and the ethanol and answers on a press.
      const yeastRun = fixture('proforma-run-yeast.json');
      doubleState.proformaRunsOnFile.set('sc-yeast-1', yeastRun.artifactId);
      await page.goto(`http://localhost:${PORT}/#/proforma/scenario/sc-yeast-1`, { waitUntil: 'networkidle' });
      await page.locator('[data-testid="train-link"]').waitFor({ timeout: 8000 }).catch(() => {});
      const yeastLink = await page.locator('[data-testid="train-link"]').getAttribute('href').catch(() => null);
      if (yeastLink !== `#/pureos/train/${yeastRun.artifactId}`) problems.push(`sc-yeast-1's page does not link to its run's train (${yeastLink})`);
      else {
        await page.locator('[data-testid="train-link"]').click();
        await page.locator('[data-testid="train-unit"]').first().waitFor({ timeout: 8000 }).catch(() => {});
        if (await page.locator('[data-testid="train-none"]').count()) problems.push('the yeast run\'s train is said not to be on file');
        const yeastUnits = await page.locator('[data-testid="train-unit"]').evaluateAll((els) => els.map((e) => e.getAttribute('data-unit')).join());
        if (yeastUnits !== yeastRun.unitOrder.join()) problems.push(`the yeast train's units are not the run's, in run order: ${yeastUnits}`);
        const yeastPanels = await page.locator('[data-testid="thermo-panel"]').evaluateAll((els) => els.map((e) => e.getAttribute('data-stream')).join());
        if (yeastPanels !== 'beer,ethanol') problems.push(`the yeast train's Properties card opens on ${yeastPanels}`);
        const ethanol = page.locator('[data-testid="thermo-panel"][data-stream="ethanol"]');
        await ethanol.getByRole('button', { name: 'Ask thermosteam' }).click().catch(() => {});
        await ethanol.locator('[data-testid="thermo-props"]').waitFor({ timeout: 8000 }).catch(() => {});
        if (!/Density/.test(await ethanol.innerText().catch(() => ''))) problems.push('the ethanol stream of the yeast train is not answered');
      }
      doubleState.proformaRunsOnFile.delete('sc-yeast-1');
      await page.goto(`http://localhost:${PORT}/#/pureos?op=molecular-sieve`, { waitUntil: 'networkidle' });
      await page.waitForTimeout(400);
      if ((await page.locator('#op-molecular-sieve[data-focused="true"]').count()) !== 1) problems.push('a step linked by ?op= is not outlined');
      await page.goto(`http://localhost:${PORT}/#/pureos/train/sc-nothing`, { waitUntil: 'networkidle' });
      await page.locator('[data-testid="train-none"]').waitFor({ timeout: 8000 }).catch(() => {});
      if (!/no Proforma run of sc-nothing is on file/.test(await page.locator('[data-testid="train-none"]').innerText().catch(() => ''))) problems.push('a scenario with no run does not say how a run gets there');
    } catch (e) {
      problems.push(String(e).slice(0, 160));
    }
    if (problems.length) {
      trainFails++;
      console.log(`✗ train        ${problems.join('; ')}`);
    } else {
      console.log('✓ train        no train for an active program, and whose is hidden; the yeast train listed once its run is on file; sc-pha-1 under its banner, three units in order, a unit no product enters drawn as words, a click cuts the streams; Properties on the broth and the product, a chemical the library lacks refused in words, another stream answered with its library and artifact and read back from what is stored; sc-yeast-1\u2019s page links to its run\u2019s train, three units in run order, Properties on the beer and the ethanol, answered; ?op= outlines a step, a scenario with no run says how one gets there');
    }
    await page.close();
  }

  // ── OF-BLD-020 §7.2 — pureOS proposes a train by rules that each name the
  // property they read.
  //
  // Propose a train opens the chooser on pureOS's index: ethanol, the yeast
  // program's product, made in S288C, no inlet. The double answers with what
  // the real proposer gave the same ask (pureos-propose.json, thermosteam's
  // volatility a stand-in there): a column then a molecular sieve, each unit's
  // reason beside it naming its rule, the property it read (the boiling point,
  // the azeotrope) and the volatility artifact that holds it, words with no
  // number, and the train kept under a new id for the Builder. A protein the
  // seed gives no sequence and no location proposes nothing and names both.
  let proposeFails = 0;
  {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    const problems = [];
    page.on('pageerror', (e) => problems.push(`page error: ${e.message}`));
    const recorded = JSON.parse(readFileSync(join(process.cwd(), 'core/tests/fixtures/prototype/pureos-propose.json'), 'utf8')).response.entries;
    try {
      await page.goto(`http://localhost:${PORT}/#/pureos`, { waitUntil: 'networkidle' });
      await page.locator('[data-testid="pureos-propose-open"]').click();
      await page.locator('[data-testid="pureos-propose-chooser"]').waitFor({ timeout: 8000 }).catch(() => {});
      const chosen = await page.locator('[data-testid="propose-product"]').inputValue().catch(() => '');
      if (chosen !== 'ethanol') problems.push(`the chooser does not start on the program's product, ethanol (${chosen})`);
      const hostIds = await page.locator('[data-testid="propose-host"] option').evaluateAll((els) => els.map((e) => e.getAttribute('value')));
      if (!hostIds.includes('s-cerevisiae-s288c') || hostIds.includes('c-necator-h16')) problems.push(`the hosts are not the shown programs' strains: ${hostIds.join()}`);
      await page.locator('[data-testid="propose-host"]').selectOption('s-cerevisiae-s288c');
      const before = doubleState.pureosProposals.length;
      await page.locator('[data-testid="propose-submit"]').click();
      await page.locator('[data-testid="pureos-proposal"]').waitFor({ timeout: 8000 }).catch(() => {});
      const sent = doubleState.pureosProposals.slice(before);
      if (sent.length !== 1 || JSON.stringify(sent[0]) !== JSON.stringify({ product: 'ethanol', host: 's-cerevisiae-s288c', inletRef: null, includeArchived: false }))
        problems.push(`the chooser posted ${JSON.stringify(sent)}, not ids and words alone`);
      const answer = recorded.find((e) => e.request.product === 'ethanol' && e.request.host === 's-cerevisiae-s288c').body;
      const units = await page.locator('[data-testid="proposal-unit"]').evaluateAll((els) => els.map((e) => `${e.getAttribute('data-unit')}:${e.getAttribute('data-type')}`).join());
      if (units !== 'D1:distillation,MS1:molecular-sieve') problems.push(`the proposed units are ${units}`);
      const reasons = await page.locator('[data-testid="proposal-reason"]').evaluateAll((els) =>
        els.map((e) => [e.getAttribute('data-unit'), e.getAttribute('data-rule'), e.getAttribute('data-property'), e.getAttribute('data-artifact')].join(':')).join());
      const expected = answer.reasons.map((r) => [r.unitId, r.rule, r.property, r.artifactId].join(':')).join();
      if (reasons !== expected) problems.push(`the reasons beside the units are ${reasons}, not the service's ${expected}`);
      const [vol] = answer.artifacts;
      if (!vol || answer.reasons.map((r) => r.property).join() !== 'boilingPoint,azeotrope') problems.push('the recorded proposal does not read the boiling point, then the azeotrope');
      if ((await page.locator(`[data-testid="proposal-artifact"][href="#/biorepo/artifacts/${vol}"]`).count()) !== 2) problems.push('each reason does not link the volatility artifact it read');
      const words = await page.locator('[data-testid="proposal-words"]').allInnerTexts();
      if (words.length !== 2 || words.some((w) => /\d/.test(w))) problems.push(`a reason's words carry a number, or are missing: ${JSON.stringify(words)}`);
      if (!/minimum-boiling azeotrope of Ethanol and Water/.test(words[1] ?? '')) problems.push("the sieve's reason does not say thermosteam finds the azeotrope");
      if (await page.locator('[data-testid="proposal-missing"]').count()) problems.push('ethanol names a missing property');
      const link = await page.locator('[data-testid="proposal-open-builder"]').getAttribute('href').catch(() => null);
      const trainId = await page.locator('[data-testid="pureos-proposal"]').getAttribute('data-train').catch(() => null);
      if (!trainId || !/^tr-/.test(trainId) || link !== `#/pureos/build/${encodeURIComponent(trainId)}`) problems.push(`the proposal does not open in the Builder under its new train id (${link}, ${trainId})`);
      // A protein the seed gives neither a sequence nor a location proposes nothing, and names both.
      await page.locator('[data-testid="propose-product"]').selectOption('taq-dna-polymerase');
      await page.locator('[data-testid="propose-submit"]').click();
      await page.locator('[data-testid="proposal-none"]').waitFor({ timeout: 8000 }).catch(() => {});
      const missing = await page.locator('[data-testid="proposal-missing"]').evaluateAll((els) => els.map((e) => e.getAttribute('data-property')).join());
      if (missing !== 'location,sequence') problems.push(`a protein with no sequence names ${missing} missing`);
      if (await page.locator('[data-testid="proposal-unit"], [data-testid="proposal-open-builder"]').count()) problems.push('a proposal of nothing shows units or a Builder link');
    } catch (e) {
      problems.push(String(e).slice(0, 160));
    }
    if (problems.length) {
      proposeFails++;
      console.log(`✗ propose      ${problems.join('; ')}`);
    } else {
      console.log('✓ propose      Propose a train for ethanol in S288C posts ids and words; a column then a molecular sieve, each reason beside its unit naming the rule, the property (boiling point, azeotrope) and the volatility artifact, words with no number; kept under a new train id for the Builder; a protein with no sequence or location proposes nothing and names both');
    }
    await page.close();
  }

  // ── OF-BLD-019 §4.R — the fermOS Properties card answers the record it names.
  //
  // Two ethanol titre candidates on a thread Q paper join the overlay (TEST
  // STAND-INs added in this page alone; no number here is a result), so the
  // card has records to pick. Record A's answer is held back until the card
  // has moved on to record B, as a first ask waits while the Proforma
  // simulator starts: A's late answer must never show under B's title. Then
  // B's first ask answers 503, as a simulator still starting does, and the
  // card keeps its button, so a second ask gets B's answer.
  let brothFails = 0;
  {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    const problems = [];
    page.on('pageerror', (e) => problems.push(`page error: ${e.message}`));
    try {
      const entries = JSON.parse(readFileSync(join(process.cwd(), 'core/tests/fixtures/prototype/thermo-props.json'), 'utf8')).response.entries;
      const beer = entries.find((e) => e.request.preset === 'beer-at-titre-of' && e.status === 200).body;
      const [A, B] = ['cl1-Q1-smoke4ra', 'cl1-Q1-smoke4rb'];
      const answerOf = { [A]: { ...beer, id: 'aaaaaaaaaaaaaaaa' }, [B]: { ...beer, id: 'bbbbbbbbbbbbbbbb' } };
      const titre = (id, value) => ({
        id, paperId: 'Q1', sectionId: 'abstract', quote: `a test stand-in titre of ${value} g/L`, field: 'ethanol_titre', value,
        unit: 'g/L', confidence: 0.8, status: 'unverified', provenance: 'unverified', extractorRun: 'claude-1', isPrimary: true,
        valueBasis: 'exact',
      });
      await page.route('**/api/biorepo/overlay', async (route) => {
        const response = await route.fetch();
        const body = await response.json();
        body.candidates = [...(body.candidates ?? []), titre(A, 40), titre(B, 60)];
        await route.fulfill({ response, json: body });
      });
      let releaseA;
      const heldA = new Promise((r) => (releaseA = r));
      let asksOfB = 0;
      await page.route('**/api/thermo/props**', async (route) => {
        const rq = route.request();
        if (rq.method() !== 'POST') return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ artifact: null }) });
        const { recordId } = rq.postDataJSON();
        if (recordId === A) await heldA;
        if (recordId === B && ++asksOfB === 1)
          return route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ detail: 'the Proforma simulator, where thermosteam runs, could not answer: the Proforma simulator could not start: it is still starting' }) });
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(answerOf[recordId]) });
      });
      await page.goto(`http://localhost:${PORT}/#/fermos`, { waitUntil: 'networkidle' });
      const pick = page.locator('select[aria-label="Titre record"]');
      await pick.waitFor({ timeout: 8000 });
      const panel = page.locator('[data-testid="broth-properties"] [data-testid="thermo-panel"]');
      await pick.selectOption(A);
      await panel.getByRole('button', { name: 'Ask thermosteam' }).click();
      await panel.getByText('Asking thermosteam').waitFor({ timeout: 4000 });
      await pick.selectOption(B);
      await panel.getByText('Not asked here yet').waitFor({ timeout: 4000 });
      releaseA();
      await page.waitForTimeout(800);
      const afterA = await panel.innerText();
      if ((await panel.locator('[data-testid="thermo-props"]').count()) !== 0 || /aaaaaaaaaaaaaaaa/.test(afterA))
        problems.push(`record A's late answer shows under record B's title: ${JSON.stringify(afterA.slice(0, 160))}`);
      if (!new RegExp(`titre of\\s*${B}`).test(afterA)) problems.push('the card does not name record B after the switch');
      await panel.getByRole('button', { name: 'Ask thermosteam' }).click({ timeout: 4000 });
      await panel.getByText(/could not start/).waitFor({ timeout: 4000 }).catch(() => {});
      if (!/could not start/.test(await panel.innerText())) problems.push("a 503 is not said in the service's words");
      if ((await panel.getByRole('button', { name: 'Ask thermosteam' }).count()) !== 1) problems.push('after a 503 the card leaves no way to ask again');
      else {
        await panel.getByRole('button', { name: 'Ask thermosteam' }).click({ timeout: 4000 });
        await panel.locator('[data-testid="thermo-props"]').waitFor({ timeout: 4000 }).catch(() => {});
        if (!/bbbbbbbbbbbbbbbb/.test(await panel.innerText())) problems.push("asking again after a 503 does not show B's answer");
      }
    } catch (e) {
      problems.push(String(e).slice(0, 200));
    }
    if (problems.length) {
      brothFails++;
      console.log(`✗ broth        ${problems.join('; ')}`);
    } else {
      console.log("✓ broth        fermOS's Properties card drops a late answer for the record it left, and after a 503 asks again");
    }
    await page.close();
  }
  // ── end §4.R

  // ── OF-BLD-020 §4.2 — fermOS → Vessel against the double.
  //
  // The chooser lists the kept simulations; the aerobic one's scope is the
  // parameter panel in Appendix 2 §C's six groups, each value with its
  // source (the harvest hour and the oxygen uptake the simulation's), and
  // the scale waits: Design says the service's words for it. A plant scale
  // typed under the reviewer name is that person's assumption; Design posts
  // the scope's overrides, signed, and shows the design table with where
  // BioSTEAM put each row, the oxygen balance through the grammar, the heat
  // line with its convention labelled, the cost line with BioSTEAM's cost
  // index and the basis naming the person. Price this in Proforma says what
  // Phase 6 adds and makes nothing. A bubble column chosen in the panel's
  // vessel type refetches the scope (Dewes) and designs it; the anaerobic
  // simulation designs the NREL fermenter, with no compressor and no
  // oxygen balance, said so.
  //
  // §4.R (the Phase 4 review): the heat line says how BioSTEAM found its
  // duty, and a person's heat per oxygen is said as forced, never as the
  // heats of formation; a vessel type changed clears the design shown; a
  // design in flight when the source changes never lands under the new
  // one; the anaerobic line above Design names no batch volume; and with
  // no simulation kept the chooser opens on no source, so a kept fit can be
  // chosen and its panel loads.
  let vesselFails = 0;
  {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    const problems = [];
    page.on('pageerror', (e) => problems.push(`page error: ${e.message}`));
    const fx = JSON.parse(readFileSync(join(process.cwd(), 'core/tests/fixtures/prototype/fermos-vessel.json'), 'utf8')).response;
    const row = (key) => page.locator(`[data-testid="param-row"][data-key="${key}"]`);
    const recorded = (sim, vesselType) =>
      fx.designs.find((d) => d.status === 200 && d.request.simulation === sim && (d.request.vesselType ?? null) === vesselType)?.body;
    const design = async () => {
      const before = doubleState.vesselPosts.length;
      await page.locator('[data-testid="vessel-design"]').click();
      for (let i = 0; i < 40 && doubleState.vesselPosts.length === before; i++) await page.waitForTimeout(100);
      await page.waitForTimeout(400);
      return doubleState.vesselPosts.at(-1);
    };
    // The double lists the fixture's two simulations for this flow alone; the
    // Simulate flow below starts, as a fresh install does, with none.
    doubleState.flags.vesselSimulationsOnFile = true;
    try {
      await page.goto(`http://localhost:${PORT}/#/settings/corpus`, { waitUntil: 'networkidle' });
      await page.locator('input[aria-label="Reviewer name"]').fill(REVIEWER);
      await page.waitForTimeout(400);
      await page.goto(`http://localhost:${PORT}/#/fermos/vessel`, { waitUntil: 'networkidle' });
      await page.locator('[data-testid="vessel-source"]').waitFor({ timeout: 8000 }).catch(() => {});
      const options = await page.locator('[data-testid="vessel-source"] option').evaluateAll((els) => els.map((e) => e.value));
      if (!options.includes(`simulation:${fx.aerobic}`) || !options.includes(`simulation:${fx.anaerobic}`))
        problems.push(`the chooser does not list the kept simulations (${options.join(', ')})`);
      // §8.R (finding 15): while the scope's first read is in hand (a cold service starts BioSTEAM), the page
      // says it is asking, and shows no Scale line and no Design until the panel answers. A page of its own,
      // opened on the anaerobic simulation with its scope's answer held, so the flow below is untouched.
      doubleState.flags.vesselScopeDelayMs = 4000;
      const cold = await browser.newPage({ viewport: { width: 1440, height: 900 } });
      cold.on('pageerror', (e) => problems.push(`page error: ${e.message}`));
      try {
        await cold.goto(`http://localhost:${PORT}/#/fermos/vessel?simulation=${encodeURIComponent(fx.anaerobic)}`, { waitUntil: 'domcontentloaded' });
        await cold.locator('[data-testid="vessel-panel-asking"]').waitFor({ timeout: 3500 }).catch(() => {});
        if (!(await cold.locator('[data-testid="vessel-panel-asking"]').count())) problems.push('while the vessel scope is read the page does not say it is asking');
        if (await cold.locator('[data-testid="vessel-scale"]').count()) problems.push('the Scale line shows before the panel that holds Scale');
        if (await cold.locator('[data-testid="vessel-design"]').count()) problems.push('Design shows before the panel has answered');
        doubleState.flags.vesselScopeDelayMs = 0;
        await cold.locator('[data-testid="vessel-design"]').waitFor({ timeout: 10000 }).catch(() => {});
        if (await cold.locator('[data-testid="vessel-panel-asking"]').count()) problems.push('the asking line stays after the panel answered');
        if (!(await cold.locator('[data-testid="vessel-design"]').count())) problems.push('Design does not show once the panel has answered');
      } finally {
        doubleState.flags.vesselScopeDelayMs = 0;
        await cold.close();
      }
      await page.locator('[data-testid="vessel-source"]').selectOption(`simulation:${fx.aerobic}`);
      await row('plant_scale').waitFor({ timeout: 8000 }).catch(() => {});
      const groups = await page.locator('[data-testid="param-group"]').evaluateAll((els) => els.map((e) => e.getAttribute('data-group')).join());
      if (groups !== 'Scale,Vessel,Schedule,Aeration,Agitation,Heat') problems.push(`the vessel panel's groups are ${groups}`);
      const served = fx.scopes.find((sc) => sc.simulation === fx.aerobic && sc.vesselType === null).body;
      const rows = await page.locator('[data-testid="param-row"]').evaluateAll((els) => els.map((e) => `${e.getAttribute('data-key')}:${e.getAttribute('data-origin')}`).join());
      const want = served.values.map((v) => `${v.key}:${v.origin}`).join();
      if (rows !== want) problems.push(`the vessel panel does not show each parameter with the source the service served (${rows}; the service: ${want})`);
      for (const key of ['tau', 'our_peak']) if ((await chipOf(page, key)).origin !== 'simulation') problems.push(`${key} is not shown as the simulation's`);
      if ((await chipOf(page, 'plant_scale')).origin !== 'waiting') problems.push('the plant scale does not wait');
      if ((await page.locator('[data-testid="vessel-scale"]').getAttribute('data-scale')) !== 'none') problems.push('Design does not say a scale is needed');
      // Design with no scale: the service's words.
      await design();
      const refusedWords = fx.designs.find((d) => d.status === 422).body.detail;
      if ((await page.locator('[data-testid="vessel-refused"]').innerText().catch(() => '')) !== refusedWords) problems.push("Design with no scale does not say the service's words");

      // A plant scale typed under the reviewer name.
      await typeParam(page, 'plant_scale', fx.plantScale);
      await row('plant_scale').locator('[data-testid="param-chip"][data-origin="assumption"]').waitFor({ timeout: 8000 }).catch(() => {});
      const typed = await chipOf(page, 'plant_scale');
      if (typed.origin !== 'assumption' || !typed.text.includes(`assumption by ${REVIEWER}`)) problems.push(`the plant scale's chip does not say assumption by ${REVIEWER} (${JSON.stringify(typed)})`);
      if ((await page.locator('[data-testid="vessel-scale"]').getAttribute('data-scale')) !== 'one') problems.push('Design does not see the scale typed');
      const posted = await design();
      await page.locator('[data-testid="vessel-result"]').waitFor({ timeout: 8000 }).catch(() => {});
      const scaleSent = (posted?.overrides ?? []).find((o) => o.key === 'plant_scale');
      if (posted?.simulation !== fx.aerobic || scaleSent?.value !== fx.plantScale || scaleSent?.by !== REVIEWER || scaleSent?.scope !== `fermos:vessel:${fx.aerobic}` || posted.vesselType)
        problems.push(`Design did not post the scope's override, signed: ${JSON.stringify(posted).slice(0, 200)}`);
      const stirred = recorded(fx.aerobic, null);
      const labels = await page.locator('[data-testid="vessel-design-row"]').evaluateAll((els) => els.map((e) => e.getAttribute('data-label')));
      if (labels.join('|') !== stirred.design.map((r) => r.label).join('|')) problems.push(`the design table is not the design's rows (${labels.length} of ${stirred.design.length})`);
      const vessels = await page.locator('[data-testid="vessel-design-row"][data-label="Vessels"] td').nth(1).innerText().catch(() => '');
      if (!vessels || vessels === '—') problems.push('the design table does not show the number of vessels');
      if (!(await page.locator('[data-testid="oxygen-balance"]').count()) || !(await page.locator('[data-testid="oxygen-otr"]').count()) || !(await page.locator('[data-testid="oxygen-our"]').count()))
        problems.push('the oxygen balance is not drawn, its transfer as a rule and its uptake as a curve');
      const heat = await page.locator('[data-testid="vessel-heat"]').innerText().catch(() => '');
      if (!/BioSTEAM.s duty/.test(heat) || !/a convention/.test(heat)) problems.push(`the heat line does not set BioSTEAM's duty beside the convention, labelled (${heat.slice(0, 120)})`);
      if (!heat.includes(stirred.heat.dutyNote) || !/the simulation took up/.test(heat) || !heat.includes(stirred.heat.conventionNote.slice(-60)))
        problems.push(`the heat line does not say how BioSTEAM found its duty and what the cross-check rests on (${heat.slice(0, 160)})`);
      const cost = await page.locator('[data-testid="vessel-cost"]').innerText().catch(() => '');
      if (!/plant cost index/.test(cost)) problems.push("the cost line does not name BioSTEAM's cost index");
      await page.locator('[data-testid="vessel-basis"] summary').click();
      const basis = await page.locator('[data-testid="vessel-basis"]').innerText().catch(() => '');
      if (!basis.includes(`plant_scale: ${fx.plantScale}`) || !basis.includes(`assumption by ${REVIEWER}`)) problems.push("the design's basis does not name the person's plant scale");
      // Price this in Proforma: words, and nothing made.
      await page.locator('[data-testid="vessel-price"]').click();
      const words = await page.locator('[data-testid="vessel-price-words"]').innerText().catch(() => '');
      if (!/custom_train_v1/.test(words) || !/no scenario is created/.test(words)) problems.push(`Price this in Proforma does not say what Phase 6 adds (${words.slice(0, 120)})`);
      if (!page.url().includes('/fermos/vessel')) problems.push('Price this in Proforma left the page');

      // §4.R (findings 2, 7, 13): a person's heat per oxygen forces BioSTEAM's duty, and the heat line says so.
      const forcedAsk = fx.designs.find((d) => d.status === 200 && (d.request.overrides ?? []).some((o) => o.key === 'Q_O2_consumption'));
      const q = forcedAsk.request.overrides.find((o) => o.key === 'Q_O2_consumption').value;
      await typeParam(page, 'Q_O2_consumption', q);
      await page.waitForTimeout(400);
      const forcedPost = await design();
      await page.waitForFunction(() => document.querySelector('[data-testid="vessel-heat"]')?.getAttribute('data-method') === 'forced-per-oxygen', null, { timeout: 8000 }).catch(() => {});
      const forcedHeat = await page.locator('[data-testid="vessel-heat"]').innerText().catch(() => '');
      if (!(forcedPost?.overrides ?? []).some((o) => o.key === 'Q_O2_consumption' && o.value === q && o.by === REVIEWER)) problems.push("the heat per oxygen was not posted as the person's");
      if ((await page.locator('[data-testid="vessel-heat"]').getAttribute('data-method').catch(() => null)) !== 'forced-per-oxygen' || /heats of formation/.test(forcedHeat) || !/forced: Q_O2_consumption/.test(forcedHeat))
        problems.push(`with a person's heat per oxygen the heat line still claims the heats of formation (${forcedHeat.slice(0, 160)})`);
      await row('Q_O2_consumption').locator('[data-testid="param-reset"]').click();
      await page.waitForTimeout(400);

      // A bubble column, chosen as the panel's vessel type: the stirred tank's design is cleared (§4.R, finding 15).
      await row('design').locator('[data-testid="param-choice"]').selectOption('Bubble column');
      await page.waitForTimeout(300);
      if (await page.locator('[data-testid="vessel-result"]').count()) problems.push("the stirred tank's design stays on screen after the vessel type changed");
      await page.waitForFunction(() => document.querySelector('[data-testid="param-row"][data-key="method"] [data-testid="param-value"]')?.textContent?.includes('Dewes'), null, { timeout: 8000 }).catch(() => {});
      if (!doubleState.paramScopes.some((q) => q.scope === `fermos:vessel:${fx.aerobic}` && q.vesselType === 'bubble-column')) problems.push("choosing a bubble column does not ask for the bubble column's scope");
      if (!(await row('method').locator('[data-testid="param-value"]').innerText().catch(() => '')).includes('Dewes')) problems.push("the bubble column's kLa correlation is not Dewes");
      const bubblePost = await design();
      await page.waitForFunction(() => /bubble column/.test(document.querySelector('[data-testid="vessel-result"]')?.textContent ?? ''), null, { timeout: 8000 }).catch(() => {});
      if (bubblePost?.vesselType !== 'bubble-column' || !(bubblePost.overrides ?? []).some((o) => o.key === 'design' && o.value === 'Bubble column' && o.by === REVIEWER))
        problems.push(`the bubble column was not posted as the person's choice: ${JSON.stringify(bubblePost).slice(0, 200)}`);
      if (!/bubble column/.test(await page.locator('[data-testid="vessel-result"]').innerText().catch(() => ''))) problems.push('the bubble column is not designed');

      // §4.R (finding 15): a design in flight when the source changes never lands under the new source.
      doubleState.flags.vesselDelayMs = 1500;
      const inFlight = doubleState.vesselPosts.length;
      await page.locator('[data-testid="vessel-design"]').click();
      for (let i = 0; i < 40 && doubleState.vesselPosts.length === inFlight; i++) await page.waitForTimeout(50);
      await page.locator('[data-testid="vessel-source"]').selectOption(`simulation:${fx.anaerobic}`);
      await page.waitForTimeout(2200);
      doubleState.flags.vesselDelayMs = 0;
      if (doubleState.vesselPosts.length === inFlight) problems.push('the design in flight was never posted');
      if (await page.locator('[data-testid="vessel-result"]').count()) problems.push("a design in flight for the aerobic simulation landed under the anaerobic one");
      if (/Designing/.test(await page.locator('[data-testid="vessel-design"]').innerText().catch(() => ''))) problems.push('Design still says it is designing after the source changed');

      // The anaerobic simulation: the NREL fermenter, no compressor, no oxygen balance.
      await page.locator('[data-testid="vessel-source"]').selectOption(`simulation:${fx.anaerobic}`);
      await row('plant_scale').waitFor({ timeout: 8000 }).catch(() => {});
      if (await row('batch_volume').count()) problems.push('an anaerobic vessel offers a batch volume');
      // §4.R (finding 14): the line above Design names only the scale the panel offers.
      const anaerobicScale = await page.locator('[data-testid="vessel-scale"]').innerText().catch(() => '');
      if (/batch volume/i.test(anaerobicScale) || !/A plant scale is needed/.test(anaerobicScale)) problems.push(`the anaerobic line above Design asks for a scale the panel does not offer (${anaerobicScale})`);
      await typeParam(page, 'plant_scale', fx.plantScale);
      await page.waitForTimeout(500);
      await design();
      await page.locator('[data-testid="vessel-anaerobic"]').waitFor({ timeout: 8000 }).catch(() => {});
      const result = await page.locator('[data-testid="vessel-result"]').innerText().catch(() => '');
      if (!result.includes('Anaerobic: no compressor, no oxygen balance') || (await page.locator('[data-testid="oxygen-balance"]').count()))
        problems.push('the anaerobic design does not say it has no compressor and no oxygen balance');
      if ((await page.locator('[data-testid="vessel-result"]').getAttribute('data-unit-class')) !== 'NRELAnaerobicBatchBioreactor') problems.push('the anaerobic simulation is not designed as the NREL fermenter');

      // §4.R (finding 12): no simulation kept, a fit on file. The chooser opens on no source, so the fit can be
      // chosen; its panel loads, the anaerobic NREL fermenter's.
      const fitScope = fx.scopes.find((sc) => sc.fit && sc.status === 200);
      doubleState.flags.vesselSimulationsOnFile = false;
      doubleState.flags.fermosFitsOnFile = true;
      const fresh = await browser.newPage({ viewport: { width: 1440, height: 900 } });
      fresh.on('pageerror', (e) => problems.push(`page error: ${e.message}`));
      try {
        await fresh.goto(`http://localhost:${PORT}/#/fermos/vessel`, { waitUntil: 'networkidle' });
        await fresh.locator(`[data-testid="vessel-source"] option[value="fit:${fitScope.fit}"]`).waitFor({ state: 'attached', timeout: 8000 }).catch(() => {});
        const first = await fresh.locator('[data-testid="vessel-source"] option').first().evaluate((o) => ({ value: o.value, disabled: o.disabled })).catch(() => null);
        const value = await fresh.locator('[data-testid="vessel-source"]').inputValue().catch(() => null);
        if (first?.value !== '' || !first?.disabled || value !== '') problems.push(`with no simulation kept the chooser does not open on no source (${JSON.stringify(first)}, ${value})`);
        if (await fresh.locator('[data-testid="vessel-empty"]').count()) problems.push('with a fit kept the page says nothing is kept');
        if (!(await fresh.locator('[data-testid="vessel-choose"]').count())) problems.push('with no simulation kept the page does not say a fit can be chosen');
        const asked = doubleState.paramScopes.length;
        await fresh.locator('[data-testid="vessel-source"]').selectOption(`fit:${fitScope.fit}`);
        await fresh.locator('[data-testid="param-row"][data-key="plant_scale"]').waitFor({ timeout: 8000 }).catch(() => {});
        if (!fresh.url().includes(`fit=${fitScope.fit}`)) problems.push(`choosing the fit did not open it (${fresh.url()})`);
        if (!doubleState.paramScopes.slice(asked).some((q2) => q2.scope === `fermos:vessel:${fitScope.fit}`)) problems.push("choosing the fit did not ask for the fit's vessel scope");
        if (!/NRELAnaerobicBatchBioreactor/.test(await fresh.locator('#vessel-panel-title').innerText().catch(() => ''))) problems.push("the fit's panel is not the NREL fermenter's");
        const fitScale = await fresh.locator('[data-testid="vessel-scale"]').innerText().catch(() => '');
        if (/batch volume/i.test(fitScale)) problems.push(`a fit's line above Design asks for a batch volume (${fitScale})`);
      } finally {
        doubleState.flags.vesselSimulationsOnFile = true;
        doubleState.flags.fermosFitsOnFile = false;
        await fresh.close();
      }
    } catch (e) {
      problems.push(String(e).slice(0, 200));
    }
    doubleState.flags.vesselSimulationsOnFile = false;
    if (problems.length) {
      vesselFails++;
      console.log(`✗ vessel       ${problems.join('; ')}`);
    } else {
      console.log(`✓ vessel       fermOS → Vessel (${fx.worker.kind}): the kept simulations chosen; every design parameter in six groups with its source; the scale waits and Design says the service's words; a plant scale typed is the reviewer's assumption, posted signed; the design table, the oxygen balance as a rule and a curve, heat with how BioSTEAM found it and its convention on the simulated uptake, cost with BioSTEAM's index, the basis naming the person; Price this in Proforma says what Phase 6 adds; a person's heat per oxygen said as forced; a vessel type changed clears the design; a bubble column chosen in the panel designs by Dewes; a design in flight dropped when the source changes; the anaerobic batch is the NREL fermenter with no compressor and asks for a plant scale alone; with no simulation kept a fit is chosen from a chooser that opens on no source`);
    }
    await page.close();
  }
  // ── end §4.2

  // ── OF-BLD-020 §3.3 — fermOS → Simulate, against the double.
  //
  // With the switch off and a reviewer name: the families the service lists
  // are offered with their equations, the light socket listed and not
  // choosable; the strain chooser offers every strain of the program first;
  // choosing CEN.PK113-7D binds the panel over the double's recorded scope,
  // and what waits is said above Simulate, which is disabled. Typing each
  // waiting value (the fixture's STAND-INs) under the reviewer name makes
  // each an assumption by that name and nothing waits; Simulate posts the
  // scope's overrides, signed; the result draws the time course from the
  // artifact (its curves the simulation's provenance), the end state, the
  // ceiling card, the parameters and what it was built from; Design the
  // vessel, Fit this family and Send to Proforma point where they should;
  // the kept simulation is offered to start from; Reset one override and it
  // waits again, and Simulate says so.
  let simulateFails = 0;
  {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    const problems = [];
    page.on('pageerror', (e) => problems.push(`page error: ${e.message}`));
    const fixture = (name) => JSON.parse(readFileSync(join(process.cwd(), 'core/tests/fixtures/prototype', name), 'utf8')).response;
    const sim = fixture('fermos-simulate.json');
    const families = fixture('fermos-families.json').off;
    const want = sim.simulate.request;
    const result = sim.simulate.body;
    const key = `${want.family}|${want.strain}`;
    const served = sim.scopes[key].body;
    const waiting = sim.bind[key].body.waiting;
    const row = (k) => page.locator(`[data-testid="simulate-panel"] [data-testid="param-row"][data-key="${k}"]`);
    try {
      if (!(await setShowArchived(page, false))) problems.push('the archive switch is not off');
      await page.goto(`http://localhost:${PORT}/#/settings/corpus`, { waitUntil: 'networkidle' });
      await page.locator('input[aria-label="Reviewer name"]').fill(REVIEWER);
      await page.waitForTimeout(400);
      await page.goto(`http://localhost:${PORT}/#/fermos/simulate`, { waitUntil: 'networkidle' });
      await page.locator('[data-testid="simulate-family"]').first().waitFor({ timeout: 8000 }).catch(() => {});
      const listed = await page.locator('[data-testid="simulate-family"]').evaluateAll((els) => els.map((e) => e.getAttribute('data-family')).join());
      if (listed !== families.map((f) => f.id).join()) problems.push(`the families offered are ${listed}, not the service's ${families.map((f) => f.id).join()}`);
      const socket = page.locator('[data-testid="simulate-family"][data-socket="true"]');
      if (!(await socket.count()) || !(await socket.locator('button[role="radio"]').isDisabled())) problems.push('the light socket is choosable');
      if (!(await socket.innerText().catch(() => '')).includes(families.find((f) => f.socket).what)) problems.push('the light socket does not say what it is in its own words');
      if (!/dX\/dt = μ·X − kd·X/.test(await page.locator('[data-testid="simulate-family"][data-family="batch_v1"] [data-testid="simulate-equations"]').innerText().catch(() => '')))
        problems.push("batch_v1's equations are not shown in plain Unicode");
      const firstStrain = await page.locator('[data-testid="simulate-strain"] option').first().innerText().catch(() => '');
      if (firstStrain !== 'Every strain of the program') problems.push(`the strain chooser offers "${firstStrain}" first`);
      await page.locator('[data-testid="simulate-strain"]').selectOption(want.strain);
      if ((await page.locator('[data-testid="simulate-product"]').inputValue()) !== want.product || (await page.locator('[data-testid="simulate-sugar"]').inputValue()) !== want.sugar)
        problems.push('the product and sugar do not open on ethanol and glucose');
      await row('mu_max').waitFor({ timeout: 8000 }).catch(() => {});
      if ((await page.locator('[data-testid="simulate-panel"] [data-testid="param-row"]').count()) !== served.specs.length)
        problems.push(`the panel shows ${await page.locator('[data-testid="simulate-panel"] [data-testid="param-row"]').count()} rows for the scope's ${served.specs.length}`);
      const groups = await page.locator('[data-testid="simulate-panel"] [data-testid="param-group"]').evaluateAll((els) => els.map((e) => e.getAttribute('data-group')).join());
      if (groups !== 'Growth,Product,Inhibition,Oxygen,Start values,Run length') problems.push(`the panel's groups are ${groups}`);
      if ((await chipOf(page, 'yps')).origin !== 'record') problems.push('Yp/s is not bound to the records');
      await page.locator('[data-testid="simulate-waiting"]').waitFor({ timeout: 8000 }).catch(() => {});
      if ((await page.locator('[data-testid="simulate-waiting"]').getAttribute('data-keys').catch(() => null)) !== waiting.join(','))
        problems.push(`what waits is not said above Simulate as the service binds it (${waiting.join(',')})`);
      if (!(await page.locator('[data-testid="simulate-button"]').isDisabled())) problems.push('Simulate is enabled while parameters wait');
      for (const o of sim.typed) await typeParam(page, o.key, o.value);
      await page.locator('[data-testid="simulate-ready"]').waitFor({ timeout: 8000 }).catch(() => {});
      if (!(await page.locator('[data-testid="simulate-ready"]').count()) || (await page.locator('[data-testid="simulate-button"]').isDisabled()))
        problems.push('with every waiting value typed, Simulate is still disabled');
      const typedChip = await chipOf(page, 'mu_max');
      if (typedChip.origin !== 'assumption' || !typedChip.text.includes(`assumption by ${REVIEWER}`)) problems.push(`a typed value is not an assumption by the reviewer (${JSON.stringify(typedChip)})`);
      await page.locator('[data-testid="simulate-button"]').click();
      await page.locator('[data-testid="simulation-result"]').waitFor({ timeout: 8000 }).catch(() => {});
      const posted = doubleState.fermosSimulates.at(-1);
      if (!posted || posted.family !== want.family || posted.strain !== want.strain || posted.product !== want.product || posted.sugar !== want.sugar)
        problems.push(`Simulate did not post the family, strain, product and sugar chosen (${JSON.stringify(posted ?? {}).slice(0, 160)})`);
      else if (
        posted.overrides.length !== sim.typed.length ||
        posted.overrides.some((o) => o.scope !== `fermos:family:${want.family}` || o.by !== REVIEWER || !sim.typed.some((t) => t.key === o.key && t.value === o.value))
      )
        problems.push("Simulate did not post the scope's overrides, each signed by the reviewer");
      if ((await page.locator('[data-testid="simulation-result"]').getAttribute('data-artifact').catch(() => null)) !== result.artifactId) problems.push('the result is not the simulation the service kept');
      const curves = await page.locator('[data-testid="timecourse-curve"]').evaluateAll((els) => els.map((e) => e.getAttribute('data-provenance')));
      if (curves.length !== 3 || curves.some((p) => p !== result.provenance)) problems.push(`the time course draws ${curves.length} curves as ${curves.join()}, not X, S and P as ${result.provenance}`);
      const titre = Number.parseFloat(await page.locator('[data-testid="simulation-titre"]').innerText().catch(() => 'NaN'));
      if (!(Math.abs(titre - result.finalTitre) <= 1e-3 * Math.abs(result.finalTitre))) problems.push(`the end state shows a titre of ${titre}, not the artifact's ${result.finalTitre}`);
      if (!(await page.locator('[data-testid="simulation-runs-out"]').innerText().catch(() => '')).includes('The sugar runs out at')) problems.push('the end state does not give the hour the sugar runs out');
      const ceilingRow = page.locator(`[data-testid="simulation-ceiling-row"][data-model="${result.ceiling.rows[0].modelId}"]`);
      if (!(await ceilingRow.count()) || (await ceilingRow.getAttribute('data-above')) !== String(result.ceiling.rows[0].above)) problems.push('the ceiling card does not set Yp/s beside the ceiling the service read');
      if ((await page.locator('[data-testid="simulation-built-from"]').getAttribute('data-provenance').catch(() => null)) !== result.provenance) problems.push('the card does not say what the simulation was built from, with its provenance');
      if (!/not a measurement/.test(await page.locator('[data-testid="simulation-built-from"]').innerText().catch(() => ''))) problems.push('the simulation does not say it is not a measurement');
      if ((await page.locator('[data-testid="simulation-param"]').count()) !== result.parameters.length + result.start.length) problems.push("the parameter table does not list every parameter and start value");
      if ((await page.locator('[data-testid="simulation-vessel-link"]').getAttribute('href')) !== `#/fermos/vessel?simulation=${result.artifactId}`) problems.push('Design the vessel does not name the simulation');
      if ((await page.locator('[data-testid="simulation-fit-link"]').getAttribute('href')) !== `#/fermos?family=${want.family}`) problems.push('Fit this family does not open Fits with the family');
      await page.locator('[data-testid="simulation-result"] [data-testid="send-to-proforma"] button').first().click();
      const to = await page.locator('[data-testid="send-to-proforma-scenario"]').first().getAttribute('data-to', { timeout: 3000 }).catch(() => null);
      if (to !== `/proforma/scenario/sc-yeast-1?fit=${result.artifactId}`) problems.push(`Send to Proforma offers ${to}`);
      // §3.R (findings 1, 17): a chemostat's end-state card shows its steady
      // state, the service's X, S, P and D·P, and says the run-hours
      // productivity is a batch's measure; no note points at a field name.
      // kinetics.py's own chemostat simulation (fermos-chemostat.json, which
      // demo.py --prototype writes) answers Simulate once.
      const chemo = fixture('fermos-chemostat.json').body;
      await page.route('**/api/fermos/simulate', (route) => route.fulfill({ json: chemo }));
      await page.locator('[data-testid="simulate-button"]').click();
      await page.locator(`[data-testid="simulation-result"][data-artifact="${chemo.artifactId}"]`).waitFor({ timeout: 8000 }).catch(() => {});
      const steady = page.locator('[data-testid="simulation-steady"]');
      if ((await steady.getAttribute('data-washout').catch(() => null)) !== String(chemo.steadyState.washout) || (await steady.getAttribute('data-reached').catch(() => null)) !== chemo.steadyState.reached)
        problems.push("a chemostat's end-state card does not show its steady state as the service found it");
      const shownSteady = Object.fromEntries(
        await steady.locator('[data-testid="steady-value"]').evaluateAll((els) => els.map((e) => [e.getAttribute('data-key'), Number(e.getAttribute('data-value'))])),
      );
      for (const k of ['X', 'S', 'P', 'productivity'])
        if (shownSteady[k] !== chemo.steadyState[k]) problems.push(`the steady state's ${k} on the card is ${shownSteady[k]}, not the service's ${chemo.steadyState[k]}`);
      if (!(await steady.innerText().catch(() => '')).includes(chemo.steadyState.words)) problems.push("the steady state's words are not on the card");
      if (!/a batch's measure/.test(await page.locator('[data-testid="simulation-productivity"]').innerText().catch(() => '')))
        problems.push("a chemostat's run-hours productivity is not said to be a batch's measure");
      if ((await page.locator('[data-testid="simulation-result"]').innerText().catch(() => '')).includes('steadyState.')) problems.push('a note on the page names a field instead of a number');
      await page.unroute('**/api/fermos/simulate');
      // Reset one override: it waits again, and Simulate says so.
      await row('p0').locator('[data-testid="param-reset"]').click();
      await page.locator('[data-testid="simulate-waiting"][data-keys="p0"]').waitFor({ timeout: 8000 }).catch(() => {});
      if (!(await page.locator('[data-testid="simulate-waiting"][data-keys="p0"]').count()) || !(await page.locator('[data-testid="simulate-button"]').isDisabled()))
        problems.push('a reset override does not wait again with Simulate disabled');
      // The kept simulation is offered to start from.
      await page.locator('[data-testid="simulate-start"]').selectOption('simulation');
      await page.locator('[data-testid="simulate-kept"]').waitFor({ timeout: 8000 }).catch(() => {});
      if (!(await page.locator(`[data-testid="simulate-kept"] option[value="${result.artifactId}"]`).count())) problems.push('the kept simulation is not offered to start from');
      await page.goto(`http://localhost:${PORT}/#/fermos/vessel?simulation=${result.artifactId}`, { waitUntil: 'networkidle' });
      await page.locator('[data-testid="vessel-source"]').waitFor({ timeout: 8000 }).catch(() => {});
      if ((await page.locator('[data-testid="vessel-source"]').inputValue().catch(() => '')) !== `simulation:${result.artifactId}`)
        problems.push('/fermos/vessel?simulation= does not land on fermOS → Vessel with the simulation chosen');
      await page.goto(`http://localhost:${PORT}/#/fermos?family=batch_v1`, { waitUntil: 'networkidle' });
      if ((await page.locator('[data-testid="fit-family"]').inputValue().catch(() => '')) !== 'batch_v1') problems.push('Fits does not open with the family chosen');
    } catch (e) {
      problems.push(String(e).slice(0, 200));
    }
    if (problems.length) {
      simulateFails++;
      console.log(`✗ simulate     ${problems.join('; ')}`);
    } else {
      console.log("✓ simulate     fermOS → Simulate offers the service's families with their equations and the light socket not choosable; every strain of the program first; the panel binds as the service does and what waits is said above a disabled Simulate; the waiting values typed are assumptions by the reviewer, Simulate posts them signed, and the time course, the end state, the ceiling card, the parameters and what it was built from are the artifact's; Design the vessel, Fit this family and Send to Proforma point at it; a chemostat's card shows the service's steady state, X, S, P and D·P, and calls the run-hours productivity a batch's measure; it is offered to start from; a reset override waits again");
    }
    await page.close();
  }
  // ── end §3.3

  await browser.close();
  server.close();

  console.log(`\n${ROUTES.length - failures.length}/${ROUTES.length} routes clean`);
  console.log(`${SHELVES.length - shelfFails}/${SHELVES.length} reference shelves render beneath a "not built" statement`);
  console.log(`${SEEDED.length - seededFails}/${SEEDED.length} seeded subsystems carry reference without a "not built" claim`);
  console.log(`${1 - programFails}/1 programs — archived hidden by default, a deep link under its banner, the switch brings them back`);
  console.log(`${1 - proformaFails}/1 Proforma index — the shelf, the reference runs, New scenario makes one that opens and survives a reload`);
  console.log(`${1 - scenarioPageFails}/1 Proforma scenario page — a seed and a made scenario run, every section read from the run`);
  console.log(`${1 - panelFails}/1 parameter panel — every input with its source, a change a named assumption the run carries, Reset to source`);
  console.log(`${1 - referenceFails}/1 Proforma reference pages — each held to its package's own test, every section read from its run`);
  console.log(`${1 - compareFails}/1 Compare — BioSTEAM scenarios side by side from their newest runs, pins kept`);
  console.log(`${1 - fitFails}/1 fermOS fit — the slot says how a fit gets made, and a chosen forecast feeds titre, yield and productivity`);
  console.log(`${1 - ceilingFails}/1 ceiling check — a scenario's yield beside the geneOS ceiling, flagged above in words, never clamped`);
  console.log(`${REDIRECTS.length - redirectFails}/${REDIRECTS.length} redirects land on the new screen`);
  console.log(`${1 - overlayFails}/1 overlay applied — fetched text in the reader, unanchored quotes listed, run scored`);
  console.log(`${OUTSIDE.length - confineFails}/${OUTSIDE.length} requests outside dist/ refused`);
  console.log(`${1 - guildFails}/1 Guild ledger flow — empty ledger, My path, practice on nobody's record, first person, reload`);
  console.log(`${1 - emptyFails}/1 empty states — Witness, fermOS and Guild name the next step with the service down`);
  console.log(`${1 - trainFails}/1 pureOS train — read from the run, unit by unit, a click cuts the streams`);
  console.log(`${1 - proposeFails}/1 pureOS propose — a train proposed by rules, each reason naming the property it read`);
  console.log(`${1 - brothFails}/1 fermOS Properties — the card answers the record it names, and asks again after a 503`);
  console.log(`${1 - vesselFails}/1 fermOS Vessel — every design parameter in the panel, a scale a named assumption, the design and its oxygen balance read from the service`);
  console.log(`${1 - simulateFails}/1 fermOS Simulate — a family simulated from its sources, what waits typed under a name, the result read from the artifact`);
  if (failures.length || redirectFails || shelfFails || seededFails || programFails || proformaFails || scenarioPageFails || panelFails || referenceFails || compareFails || fitFails || overlayFails || confineFails || guildFails || emptyFails || trainFails || proposeFails || brothFails || ceilingFails || vesselFails || simulateFails) process.exit(1);
}

main();
