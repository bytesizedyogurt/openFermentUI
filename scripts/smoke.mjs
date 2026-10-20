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
    ['/fermos', 'fermOS subsystems', 'Oxygen transfer'],
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
      await page.locator('[data-testid="scenario-not-run"]').waitFor({ timeout: 8000 }).catch(() => {});
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
      // §3.2: the page lists the inputs the service bound for its flowsheet; wait for its rows.
      await page.locator('[data-testid="proforma-inputs"] tbody tr').first().waitFor({ timeout: 8000 }).catch(() => {});
      const pageRows = await page.locator('[data-testid="proforma-inputs"] tbody tr').count();
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
  // as GET /api/proforma/bind binds it) each take the three assumptions that
  // wait, under the reviewer's name, and run against the double. After Run
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
      for (const [key, vals] of [['recovery', ['0.95', '0.9', '0.98']], ['sugarPrice', ['0.4', '0.3', '0.5']], ['sugarFeed', ['10000', '10000', '10000']]]) {
        const form = page.locator(`[data-testid="assume-${key}"]`);
        await form.waitFor({ timeout: 8000 }).catch(() => {});
        const boxes = form.locator('input');
        for (let i = 0; i < 3; i++) await boxes.nth(i).fill(vals[i]);
        await form.locator('button:has-text("Keep assumption")').click();
        await page.waitForTimeout(150);
      }
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
      if (!/computed \d{4}-\d\d-\d\d \d\d:\d\d in [\d.]+ s/.test(await page.locator('[data-testid="run-result"]').innerText().catch(() => '')))
        problems.push('after a reload sc-pha-1 does not read its newest run back from the artifact');

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
      if ((await count('[data-testid^="input-"]')) !== 7 || (await count('[data-testid="source-records"]')) !== 4)
        problems.push('the made scenario does not list its seven inputs with four bound to records');
      if (!(await count('[data-testid="scenario-not-run"]'))) problems.push('the made scenario does not say it has not run');
      if (!(await page.getByRole('button', { name: 'Run the scenario' }).isDisabled())) problems.push('the made scenario is offered a run while inputs wait');
      await typeAssumptions();
      await page.getByRole('button', { name: 'Run the scenario' }).click();
      await sections('a scenario made from pha_sugar_v0');
      const madePost = doubleState.proformaRuns.at(-1);
      if (madePost?.scenarioId !== made || madePost?.flowsheet !== 'pha_sugar_v0' || madePost?.assumptions?.length !== 3 || madePost.assumptions.some((a) => a.by !== REVIEWER))
        problems.push(`the made scenario was not run by its flowsheet with three signed assumptions: ${JSON.stringify(madePost).slice(0, 160)}`);
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
      if ((await count('[data-testid^="input-"]')) !== 7) problems.push('with the switch off the made PHA scenario does not bind its own program\u2019s inputs');
      await sections('the made PHA scenario with the switch off');
    } catch (e) {
      problems.push(String(e).slice(0, 160));
    }
    if (problems.length) {
      scenarioPageFails++;
      console.log(`✗ scenario     ${problems.join('; ')}`);
    } else {
      console.log('✓ scenario     sc-pha-1 by its id and a scenario made from pha_sugar_v0 by its flowsheet each take three signed assumptions and run; the price, the base case, the cost breakdown, the sensitivity, the distribution, the streams, the equipment, the utilities and the ordered units are each as long as the stored run, each table with its CSV, with pin, Compare and pureOS\u2019s train; the newest run reads back from its artifact after a reload and gives the index its price; with the switch off a scenario the double cannot bind says the service\u2019s words and that it has not run, and the made PHA scenario opens its own program under the banner');
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
      // The index's reference cards link to their pages.
      await page.goto(`http://localhost:${PORT}/#/proforma`, { waitUntil: 'networkidle' });
      const link = page.locator('[data-testid="reference-card"][data-flowsheet="corn_drygrind"] [data-testid="reference-title"]');
      await link.waitFor({ timeout: 8000 }).catch(() => {});
      await link.click().catch(() => {});
      await page.locator('[data-testid="proforma-reference"]').waitFor({ timeout: 8000 }).catch(() => {});
      if (!/#\/proforma\/reference\/corn_drygrind$/.test(page.url())) problems.push(`the corn reference card does not open its page (${page.url()})`);
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
      for (const [key, vals] of [['plant_scale', ['100000', '100000', '100000']], ['glucose_price', ['0.4', '0.3', '0.5']]]) {
        const form = page.locator(`[data-testid="assume-${key}"]`);
        await form.waitFor({ timeout: 8000 }).catch(() => {});
        const boxes = form.locator('input');
        for (let i = 0; i < 3; i++) await boxes.nth(i).fill(vals[i]);
        await form.locator('button:has-text("Keep assumption")').click();
        await page.waitForTimeout(150);
      }
    };
    const runAndPin = async (who) => {
      await page.getByRole('button', { name: 'Run the scenario' }).click();
      await page.locator('[data-testid="run-result"]').waitFor({ timeout: 8000 }).catch(() => {});
      if (!(await count('[data-testid="run-result"] [data-testid="scenario-price"]'))) problems.push(`${who} did not run`);
      await page.locator('[data-testid="scenario-pin"]').click();
      if ((await page.locator('[data-testid="scenario-pin"]').getAttribute('aria-pressed')) !== 'true') problems.push(`${who} did not pin`);
    };
    try {
      if (!(await setShowArchived(page, false))) problems.push('the archive switch is not off');
      await page.goto(`http://localhost:${PORT}/#/settings/corpus`, { waitUntil: 'networkidle' });
      await page.locator('input[aria-label="Reviewer name"]').fill(REVIEWER);
      await page.waitForTimeout(400);

      await page.goto(`http://localhost:${PORT}/#/proforma/scenario/sc-yeast-1`, { waitUntil: 'networkidle' });
      await page.locator('[data-testid="proforma-inputs"]').waitFor({ timeout: 8000 }).catch(() => {});
      await typeYeast();
      await runAndPin('sc-yeast-1');
      // §2.R: after a reload the yeast scenario reads its newest run back from its artifact, as sc-pha-1 does.
      await page.waitForTimeout(700);
      await page.reload({ waitUntil: 'networkidle' });
      await page.locator('[data-testid="run-result"]').waitFor({ timeout: 8000 }).catch(() => {});
      if (!/computed \d{4}-\d\d-\d\d \d\d:\d\d in [\d.]+ s/.test(await page.locator('[data-testid="run-result"]').innerText().catch(() => '')))
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
      await page.locator('[data-testid="input-productivity"] [data-testid="source-artifact"]').waitFor({ timeout: 8000 }).catch(() => {});
      const shown = async () => {
        const lacks = [];
        for (const key of ['titre', 'yield', 'productivity']) {
          const cell = page.locator(`[data-testid="input-${key}"] [data-testid="source-artifact"]`);
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
      await page.waitForTimeout(700);
      await page.reload({ waitUntil: 'networkidle' });
      await page.locator('[data-testid="input-titre"] [data-testid="source-artifact"]').waitFor({ timeout: 8000 }).catch(() => {});
      if ((await shown()).length) problems.push('the fit chosen does not survive a reload');
      // §5.R (8): the index binds without the fits, so it says a fit is chosen, never that one is bound.
      await page.goto(`http://localhost:${PORT}/#/proforma`, { waitUntil: 'networkidle' });
      const indexCard = page.locator('[data-testid="biosteam-card"][data-scenario="sc-yeast-1"] [data-testid="scenario-inputs"]');
      await indexCard.waitFor({ timeout: 8000 }).catch(() => {});
      const counted = await indexCard.innerText({ timeout: 3000 }).catch(() => '');
      if (!/3 with a fermOS fit chosen/.test(counted) || /from a fermOS fit/.test(counted))
        problems.push(`the index does not say the inputs have a fit chosen: ${JSON.stringify(counted.slice(0, 160))}`);
      await page.goto(`http://localhost:${PORT}/#/proforma/scenario/sc-yeast-1`, { waitUntil: 'networkidle' });
      await page.locator('[data-testid="input-titre"] [data-testid="source-artifact"]').waitFor({ timeout: 8000 }).catch(() => {});
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
      await page.locator('[data-testid="input-productivity"] [data-testid="source-records"]').waitFor({ timeout: 8000 }).catch(() => {});
      for (const key of ['titre', 'yield']) {
        const link = await page.locator(`[data-testid="input-${key}"] [data-testid="source-artifact"]`).getAttribute('href', { timeout: 3000 }).catch(() => null);
        if (link !== `#/biorepo/artifacts/${kinetic}`) problems.push(`stopping the forecast cleared the fit chosen for ${key} (${link})`);
      }
      if (!(await page.locator('[data-testid="input-productivity"] [data-testid="source-records"]').count())) problems.push('stopping the forecast does not put the records back under productivity');
      if (!/In use for titre, yield\./.test(await fitOption.innerText({ timeout: 3000 }).catch(() => ''))) problems.push("the fit's card no longer says it is in use for titre and yield");
      await fitOption.locator('[data-testid="fermos-fit-stop"]').click({ timeout: 8000 });
      await page.locator('[data-testid="input-titre"] [data-testid="source-records"]').waitFor({ timeout: 8000 }).catch(() => {});
      if ((await page.locator('[data-testid="source-artifact"]').count()) !== 0) problems.push('stopping the fit does not put the records back');
    } catch (e) {
      problems.push(String(e).slice(0, 160));
    } finally {
      doubleState.flags.fermosFitsOnFile = false;
    }
    if (problems.length) {
      fitFails++;
      console.log(`✗ fermos fit   ${problems.join('; ')}`);
    } else {
      console.log("✓ fermos fit   sc-yeast-1 with no fit on file says how one gets made; with the fit and the forecast on file each says what it can feed and why not, choosing the forecast binds titre, yield and productivity to its artifact, asked of the service with the fits, read by the ceiling check, kept across a reload and counted on the index as chosen; the fit's titre beside the forecast's productivity is refused naming titre, stopping the forecast clears its productivity alone, and stopping the fit puts the records back");
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
      if (!/An assumption carries a person's name: set yours in/.test(await page.locator('body').innerText()))
        problems.push('an unnamed person is offered an assumption to type');
      await page.goto(`http://localhost:${PORT}/#/settings/corpus`, { waitUntil: 'networkidle' });
      await page.locator('input[aria-label="Reviewer name"]').fill(REVIEWER);
      await page.waitForTimeout(400);
      await page.goto(`http://localhost:${PORT}/#/proforma/scenario/sc-pha-1`, { waitUntil: 'networkidle' });
      await page.locator('[data-testid="proforma-inputs"]').waitFor({ timeout: 8000 }).catch(() => {});
      const pf = await page.locator('[data-testid="proforma-biosteam"]').innerText().catch(() => '');
      if (!/BioSTEAM flowsheet, draft v0 — fermentation, harvest and drying only/.test(pf)) problems.push('sc-pha-1 does not carry its draft header');
      if (!/Waiting for a source: solids recovered at harvest, price of fermentable sugar, sugar fed/.test(pf)) problems.push('the inputs waiting for a source are not named');
      if (!(await page.getByRole('button', { name: 'Run the scenario' }).isDisabled())) problems.push('the run is offered while inputs wait for a source');
      for (const [key, vals] of [['recovery', ['0.95', '0.9', '0.98']], ['sugarPrice', ['0.4', '0.3', '0.5']], ['sugarFeed', ['10000', '10000', '10000']]]) {
        const form = page.locator(`[data-testid="assume-${key}"]`);
        const boxes = form.locator('input');
        for (let i = 0; i < 3; i++) await boxes.nth(i).fill(vals[i]);
        await form.locator('button:has-text("Keep assumption")').click();
        await page.waitForTimeout(150);
      }
      if ((await page.locator('[data-testid="assumption-chip"]').count()) !== 3) problems.push('three typed assumptions do not each show who made them');
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
      if (!posted || posted.assumptions?.length !== 3 || posted.assumptions.some((a) => a.by !== REVIEWER))
        problems.push('the run did not post the three assumptions signed with the reviewer\'s name');
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
  let trainFails = 0;
  {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    const problems = [];
    page.on('pageerror', (e) => problems.push(`page error: ${e.message}`));
    try {
      await page.goto(`http://localhost:${PORT}/#/pureos`, { waitUntil: 'networkidle' });
      await page.locator('[data-testid="pureos-trains-empty"]').waitFor({ timeout: 8000 }).catch(() => {});
      const empty = await page.locator('[data-testid="pureos-trains-empty"]').innerText().catch(() => '');
      if (!/No train for an active program/.test(empty) || !/Proforma/.test(empty)) problems.push(`the empty list does not say how a train gets there: ${JSON.stringify(empty.slice(0, 160))}`);
      if (!/PHA/.test(empty)) problems.push('the empty list does not say it hides a PHA train');
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
      console.log('✓ train        no train for an active program, and whose is hidden; sc-pha-1 under its banner, three units in order, a unit no product enters drawn as words, a click cuts the streams; Properties on the broth and the product, a chemical the library lacks refused in words, another stream answered with its library and artifact and read back from what is stored; ?op= outlines a step, a scenario with no run says how one gets there');
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

  await browser.close();
  server.close();

  console.log(`\n${ROUTES.length - failures.length}/${ROUTES.length} routes clean`);
  console.log(`${SHELVES.length - shelfFails}/${SHELVES.length} reference shelves render beneath a "not built" statement`);
  console.log(`${SEEDED.length - seededFails}/${SEEDED.length} seeded subsystems carry reference without a "not built" claim`);
  console.log(`${1 - programFails}/1 programs — archived hidden by default, a deep link under its banner, the switch brings them back`);
  console.log(`${1 - proformaFails}/1 Proforma index — the shelf, the reference runs, New scenario makes one that opens and survives a reload`);
  console.log(`${1 - scenarioPageFails}/1 Proforma scenario page — a seed and a made scenario run, every section read from the run`);
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
  console.log(`${1 - brothFails}/1 fermOS Properties — the card answers the record it names, and asks again after a 503`);
  if (failures.length || redirectFails || shelfFails || seededFails || programFails || proformaFails || scenarioPageFails || referenceFails || compareFails || fitFails || overlayFails || confineFails || guildFails || emptyFails || trainFails || brothFails || ceilingFails) process.exit(1);
}

main();
