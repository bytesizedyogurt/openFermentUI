/**
 * Route smoke test. Serves the production build, visits every route in the map,
 * and fails on console errors, uncaught exceptions, or an empty render.
 *
 *   pnpm build && node scripts/smoke.mjs
 */
import { chromium } from 'playwright';
import { request as httpRequest } from 'node:http';
import { existsSync } from 'node:fs';
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
  ['/proforma', 'Proforma'],
  ['/proforma/scenario/sc-s1', 'Proforma — scenario S1'],
  ['/proforma/scenario/sc-s2', 'Proforma — scenario S2'],
  ['/proforma/scenario/sc-s3', 'Proforma — scenario S3 (the incumbent)'],
  ['/proforma/scenario/sc-pha-1', 'Proforma — BioSTEAM scenario (draft PHA flowsheet)'],
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
  ['/settings/units', 'Settings — units'],
  ['/settings/corpus', 'Settings — corpus'],
  ['/settings/figures', 'Settings — the figure grammar over its sample'],
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
      await page.goto(`http://localhost:${PORT}/#/biorepo/paper/B5`, { waitUntil: 'networkidle' });
      await page.waitForTimeout(1200);
      const text = await page.locator('body').innerText();
      const problems = [];
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
      // Witness renders a skeleton for a simulated 200–450 ms before its
      // numbers; wait for the run's own label rather than a guessed sleep.
      await page.locator('text=claude-1').first().waitFor({ timeout: 8000 }).catch(() => {});
      await page.waitForTimeout(150);
      const witness = await page.locator('body').innerText();
      if (!/claude-1/.test(witness)) problems.push('Witness does not show the overlay run');
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

      // OF-BLD-014 §5.4 — Postdoc live: the steps draw as the double replays
      // the stream the real loop recorded, the claim shows its record's value
      // and its quoted sentence, the footer says why the loop stopped, and
      // the quote opens the reader on the paper's words.
      await page.goto(`http://localhost:${PORT}/#/postdoc`, { waitUntil: 'networkidle' });
      await page.getByRole('button', { name: 'Live (Postdoc service)' }).click();
      await page.locator('textarea[aria-label="Ask a question"]').fill('What does the stand-in table report for placeholder A?');
      await page.locator('textarea[aria-label="Ask a question"]').press('Enter');
      await page.locator('[data-testid="trace-step"]').first().waitFor({ timeout: 8000 }).catch(() => {});
      const early = await page.locator('[data-testid="trace-step"]').count();
      await page.locator('[data-testid="passage-quote"]').waitFor({ timeout: 8000 }).catch(() => {});
      if (early < 1 || early >= 3) problems.push(`the trace did not draw step by step (saw ${early} steps before the answer)`);
      if (!doubleState.asks.some((a) => a.path === '/api/ask/stream' && a.mode === 'agent'))
        problems.push('Postdoc live did not ask the stream in agent mode');
      const steps = await page.locator('[data-testid="trace-step"]').allInnerTexts();
      if (steps.length !== 3) problems.push(`the trace shows ${steps.length} steps, not 3`);
      if (!/Looked up records of secreted titer · 1 record/.test(steps[0] ?? '')) problems.push('the first trace line is not the record search in plain words');
      if (!/Searched the papers for "placeholder rows in the table" · 2 passages/.test(steps[1] ?? '')) problems.push('the second trace line is not the passage search');
      await page.locator('[data-testid="trace-step"] summary').nth(1).click();
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
      // OF-BLD-014 §6.1 — the figure gallery: the legend names all nine
      // classes, three figures draw over the labelled sample, and a figure's
      // table twin holds one row per mark.
      await page.goto(`http://localhost:${PORT}/#/settings/figures`, { waitUntil: 'networkidle' });
      await page.locator('[data-testid="figure-gallery"]').waitFor({ timeout: 8000 }).catch(() => {});
      if ((await page.locator('[data-testid="encoding-legend"] li').count()) !== 9) problems.push('the figure legend does not list nine provenances');
      if ((await page.locator('[data-testid="figure"]').count()) !== 3) problems.push('the gallery does not draw three figures');
      if (!/SAMPLE: invented values/.test(await page.locator('body').innerText())) problems.push('the gallery does not say its values are a sample');
      await page.locator('[data-testid="figure"]').nth(1).getByRole('button', { name: 'View as table' }).click();
      if ((await page.locator('[data-testid="figure-table"] tbody tr').count()) !== 12) problems.push('the ceiling figure\'s table does not hold one row per mark');
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
      // OF-BLD-014 §7.4 — fermOS over the sample run: it loads labelled, the
      // fit draws through the points with its parameter table, and Forecast
      // draws a band from that fit; both are asked of the service as sample.
      await page.goto(`http://localhost:${PORT}/#/fermos`, { waitUntil: 'networkidle' });
      await page.getByRole('button', { name: 'Load a sample run' }).click();
      await page.locator('[data-testid="fit-params"]').waitFor({ timeout: 10000 }).catch(() => {});
      const fits = await page.locator('[data-testid="fermos-fits"]').innerText().catch(() => '');
      if (!/SAMPLE: an invented time course/.test(fits)) problems.push('the sample run is not labelled as sample');
      if ((await page.locator('[data-testid="fit-params"] tbody tr').count()) !== 9) problems.push('the fit does not list nine parameters');
      if ((await page.locator('[data-testid="trajectory-fit"]').count()) !== 3) problems.push('the fit does not draw a curve through each of the three series');
      if (!/constant amount/.test(fits)) problems.push('the fit does not state its noise assumption');
      if (!doubleState.fermosCalls.some((c) => c.path === '/api/fermos/fit' && c.sample === true)) problems.push('the sample fit was not asked of the service as sample');
      await page.goto(`http://localhost:${PORT}/#/fermos/forecast`, { waitUntil: 'networkidle' });
      await page.getByRole('button', { name: 'Forecast', exact: true }).click();
      await page.locator('[data-testid="trajectory-forecast"]').first().waitFor({ timeout: 10000 }).catch(() => {});
      if ((await page.locator('[data-testid="trajectory-forecast"]').count()) !== 3) problems.push('the forecast does not draw a band for each series');
      const fc = await page.locator('[data-testid="fermos-forecast"]').innerText().catch(() => '');
      if (!/Variation from run to run is absent/.test(fc)) problems.push('the forecast does not say run-to-run variation is absent');
      if (!/Final biomass/.test(fc)) problems.push('the forecast does not give final values as intervals');
      // OF-BLD-014 §8.2 — the Benchmark card, on a service whose simulator
      // has yet to run: it says so, names the expected price and offers a run.
      await page.goto(`http://localhost:${PORT}/#/proforma`, { waitUntil: 'networkidle' });
      await page.locator('[data-testid="benchmark-empty"]').waitFor({ timeout: 8000 }).catch(() => {});
      const bench = await page.locator('[data-testid="benchmark-card"]').innerText().catch(() => '');
      if (!/Not run on this service yet/.test(bench) || !/biorefineries\.cornstover@2\.35\.1/.test(bench))
        problems.push('the Benchmark card does not show its empty state with the package it will run');
      if (!(await page.getByRole('button', { name: 'Run the benchmark' }).count())) problems.push('the Benchmark card offers no run');
      await page.goto(`http://localhost:${PORT}/#/postdoc`, { waitUntil: 'networkidle' });
      // Back to scripted, which the live panel leaves untouched.
      await page.goto(`http://localhost:${PORT}/#/postdoc`, { waitUntil: 'networkidle' });
      await page.getByRole('button', { name: 'Scripted' }).click();

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
      const coldPage = await browser.newPage({ viewport: { width: 1440, height: 900 } });
      await coldPage.goto(`http://localhost:${PORT}/#/guild?record=r-B5-1`, { waitUntil: 'networkidle' });
      // networkidle already covers the double's 700 ms overlay; give the
      // store one tick to apply it.
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
      await page.goto(`http://localhost:${PORT}/#/settings/corpus`, { waitUntil: 'networkidle' });
      await page.locator('input[aria-label="Reviewer name"]').fill(REVIEWER);
      await page.waitForTimeout(400);
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
        console.log('✓ overlay      B5 shows the fetched text; 3 unanchored quotes listed, each linked to review; Witness scores the run provisionally; Guild shows the extractor\'s span and posts the decision; Postdoc live draws its steps, quotes the table row and opens the reader on it; the figure gallery draws its sample; geneOS draws a ceiling beside what was reported; fermOS fits and forecasts the sample run');
      }
    } catch (e) {
      overlayFails++;
      console.log(`✗ overlay      ${String(e).slice(0, 160)}`);
    }
    await page.close();
  }

  // ── OF-BLD-013 — the competence ledger, end to end in one browser ────
  //
  // The sample team loads, a level is computed from it, an assessor's
  // sign-off moves a cell, and the sample sends nothing to the service and
  // leaves nothing behind. Then the real ledger: its first person is its
  // lead, posted to the service as one, and still there after a reload.
  let guildFails = 0;
  {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    const problems = [];
    page.on('pageerror', (e) => problems.push(`page error: ${e.message}`));
    try {
      await page.goto(`http://localhost:${PORT}/#/guild/matrix`, { waitUntil: 'networkidle' });
      await page.waitForTimeout(500);
      if (!/Nobody is on the ledger yet/.test(await page.locator('body').innerText())) problems.push('a fresh browser does not show the empty ledger');
      await page.locator('button:has-text("Show a sample team")').click();
      await page.waitForTimeout(300);
      const body = await page.locator('body').innerText();
      if (!/Sample team: invented people/.test(body)) problems.push('the sample is not labelled as invented');
      const suspended = await page.locator('button[aria-label="Patrick Mugisha, OD750 reading: Qualified, suspended"]').count();
      if (suspended !== 1) problems.push('the sample does not show its suspension on the matrix');
      const cell = page.locator('button[aria-label="Aline Uwase, OD750 reading: Not started"]');
      if ((await cell.count()) !== 1) problems.push('the cell to sign is missing');
      else {
        await cell.click();
        await page.waitForTimeout(200);
        if (!/Record what you saw/.test(await page.locator('[role="dialog"]').innerText())) problems.push('an assessor is not offered a sign-off');
        await page.fill('#signoff-note', 'Briefed on PR-OD-01 and talked it back');
        await page.locator('[role="dialog"] button:has-text("Sign as Eric Habimana")').click();
        await page.waitForTimeout(300);
        await page.keyboard.press('Escape');
        await page.waitForTimeout(200);
        const moved = await page.locator('button[aria-label="Aline Uwase, OD750 reading: Supervised"]').count();
        if (moved !== 1) problems.push('a training sign-off did not move the cell to Supervised');
      }
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
      await page.getByRole('button', { name: 'Live (Postdoc service)' }).click();
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
      // §2 — run mode reads the same ledger and writes to it as steps complete.
      await page.evaluate(() => (location.hash = '#/runbooks/protocols/PR-OD-01'));
      await page.waitForTimeout(400);
      await page.locator('button:has-text("Start run at")').first().click();
      await page.waitForTimeout(500);
      let bench = await page.locator('body').innerText();
      if (!/Eric Habimana holds every skill this step needs/.test(bench)) problems.push('run mode does not start with the acting assessor cleared');
      await page.locator('button:has-text("Hand over")').click();
      await page.locator('button:has-text("Patrick Mugisha")').first().click();
      await page.waitForTimeout(200);
      bench = await page.locator('body').innerText();
      if (!/Cosign needed/.test(bench)) problems.push('a Supervised operator is not asked for a cosigner');
      await page.locator('button:has-text("Record cosigner")').click();
      await page.locator('button:has-text("Eric Habimana")').first().click();
      await page.waitForTimeout(200);
      if (!/Cosigned by Eric Habimana/.test(await page.locator('body').innerText())) problems.push('the cosigner is not shown');
      await page.locator('button:has-text("Mark step complete")').click();
      await page.waitForTimeout(400);
      await page.evaluate(() => (location.hash = '#/guild/people/p-sample-patrick'));
      await page.waitForTimeout(400);
      const ledger = await page.locator('body').innerText();
      if (!/Supervised run[\s\S]{0,200}PR-OD-01 · step o1 · cosigned by Eric Habimana/.test(ledger))
        problems.push('completing a cosigned step did not write a supervised run to the ledger');
      // §5.1 — enforce mode: a critical skill holds the step until a cosigner is recorded.
      await page.evaluate(() => (location.hash = '#/runbooks/protocols/PR-CIP-01'));
      await page.waitForTimeout(400);
      await page.locator('button:has-text("Start run at")').first().click();
      await page.waitForTimeout(500);
      await page.locator('button:has-text("Hand over")').click();
      await page.locator('button:has-text("Grace Ingabire")').first().click();
      await page.waitForTimeout(200);
      for (let i = 0; i < 2; i++) await page.getByRole('button', { name: 'Next step' }).click();
      await page.waitForTimeout(300);
      const held = page.locator('button:has-text("Waits for a cosigner")');
      if ((await held.count()) !== 1 || !(await held.isDisabled()))
        problems.push('a Supervised operator on a critical skill is not held for a cosigner in enforce mode');
      // §5.5 — a held step can be skipped, and the skip says it goes on the record.
      await page.locator('footer button:has-text("Skip")').click();
      await page.waitForTimeout(150);
      if (!/Skipping it is kept with the run, and goes on the operator’s ledger as a deviation/.test(await page.locator('[role="dialog"]').innerText()))
        problems.push('skipping a held step does not say it goes on the record');
      await page.keyboard.press('Escape');
      await page.waitForTimeout(150);
      await page.locator('button:has-text("Record cosigner")').click();
      await page.locator('button:has-text("Eric Habimana")').first().click();
      await page.waitForTimeout(200);
      if ((await page.locator('button:has-text("Mark step complete")').count()) !== 1)
        problems.push('recording a cosigner does not release the held step');
      // §3 — a lesson passed in Primer moves its learner from Not started to Learning.
      await page.evaluate(() => (location.hash = '#/primer/l6-3'));
      await page.waitForTimeout(400);
      await page.selectOption('#lesson-learning-as', 'p-sample-olivier');
      for (const answer of [
        'Step c2: strip the vessel and find the ingress point',
        'Clear hold water, a negative spore strip, and both results on the vessel log',
        'A biological indicator spore strip',
      ]) {
        await page.locator('button', { hasText: answer }).first().click();
        await page.getByRole('button', { name: 'Check answer' }).first().click();
        await page.waitForTimeout(150);
      }
      if (!/On Olivier Ndayisaba’s ledger as a lesson passed/.test(await page.locator('main').innerText()))
        problems.push('a passed lesson does not say it is on the learner’s ledger');
      await page.evaluate(() => (location.hash = '#/guild/matrix'));
      await page.waitForTimeout(400);
      await page.selectOption('#matrix-protocol', 'PR-CIP-01');
      await page.waitForTimeout(200);
      if ((await page.locator('button[aria-label="Olivier Ndayisaba, Vessel sterilisation: Learning"]').count()) !== 1)
        problems.push('a passed lesson did not move its learner to Learning on the Matrix');
      await page.evaluate(() => (location.hash = '#/primer/path'));
      await page.waitForTimeout(400);
      const path = await page.locator('main').innerText();
      if (!/Vessel sterilisation[\s\S]{0,200}Waits for Pressure and heat safety to reach Supervised/.test(path))
        problems.push('My path does not say a passed lesson waits on its prerequisite');
      if (!/Next up[\s\S]*Open the lesson/.test(path)) problems.push('My path offers no lesson to take next');
      // §4 — practice: a draft, three answers to the tutor, and the close on the learner's record.
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
      if (!/Recorded for Olivier Ndayisaba in the sample team alone/.test(player))
        problems.push('a closed session with the sample shown does not say it went on the sample learner alone');
      if (practicePosts.some((x) => x.body.personId != null)) problems.push('a sample person was named to the service in Practice');
      await page.evaluate(() => (location.hash = '#/guild/people/p-sample-olivier'));
      await page.waitForTimeout(400);
      if (!/Practice[\s\S]{0,300}Practice transcript pt-smoke-/.test(await page.locator('main').innerText()))
        problems.push('the closed session is not on the learner\u2019s ledger with a link to its transcript');
      // §5.4 — a check from the queue, run at the bench, signed, and on the ledger.
      await page.evaluate(() => (location.hash = '#/guild/checks'));
      await page.waitForTimeout(400);
      await page.selectOption('#guild-acting-as', 'p-sample-eric');
      await page.waitForTimeout(200);
      const card = page.locator('.card', { hasText: 'Patrick Mugisha' }).filter({ hasText: 'Run now at the bench' }).first();
      if (!/Did not meet every criterion at the witnessed check/.test(await card.innerText())) problems.push('the queue does not say why the suspended trainee is proposed');
      await card.locator('a:has-text("Run now at the bench")').click();
      await page.waitForTimeout(400);
      if ((await page.locator('nav').count()) !== 0) problems.push('the bench check is not a full-screen takeover');
      // The bench's own targets, buttons and links alike; a toast from earlier in the flow is the shell's, as it is in Deposition.
      const short = await page.locator('header button, main button, main a, header a').evaluateAll((bs) => bs.filter((b) => b.getBoundingClientRect().height > 0 && b.getBoundingClientRect().height < 44).map((b) => b.innerText || b.getAttribute('aria-label')));
      if (short.length) problems.push(`bench buttons under 44px: ${short.join(', ')}`);
      await page.locator('button:has-text("Begin with the first criterion")').click();
      let calls = 0;
      for (let guard = 0; guard < 60; guard++) {
        const bench = await page.locator('main').innerText();
        if (/Sign the check on Patrick Mugisha/.test(bench)) break;
        if (/What did you see Patrick Mugisha do/.test(bench)) await page.locator('textarea[id^="bench-words-"]').fill('Worked through it at the bench and said each step aloud');
        else {
          await page.locator(`button:has-text("${calls === 0 ? 'Needs work' : 'Meets'}")`).click();
          calls++;
        }
        await page.locator('button:has-text("Next"), button:has-text("To the sign step")').first().click();
        await page.waitForTimeout(60);
      }
      if (!/1 need work[\s\S]*every criterion met/.test(await page.locator('main').innerText())) problems.push('the sign step does not sum up each skill');
      const shortSign = await page.locator('header button, main button, main a, header a').evaluateAll((bs) => bs.filter((b) => b.getBoundingClientRect().height > 0 && b.getBoundingClientRect().height < 44).map((b) => b.innerText || b.getAttribute('aria-label')));
      if (shortSign.length) problems.push(`sign-step targets under 44px: ${shortSign.join(', ')}`);
      await page.locator('button:has-text("Sign as Eric Habimana")').click();
      await page.waitForTimeout(400);
      if (!/Signed by Eric Habimana/.test(await page.locator('main').innerText())) problems.push('signing the check did not finish it');
      await page.locator('button:has-text("Open Patrick Mugisha’s ledger")').click();
      await page.waitForTimeout(400);
      const signedLedger = await page.locator('main').innerText();
      if (!/Witnessed check[\s\S]{0,40}not met[\s\S]{0,200}Bench check ck-sample-\d+ · observed by Eric Habimana/.test(signedLedger))
        problems.push('the check is not on the ledger as a witnessed entry naming its assessor and its check');
      const checkLink = await page.locator('a:has-text("Bench check ck-sample-")').first().getAttribute('href');
      await page.evaluate((h) => (location.hash = h), checkLink);
      await page.waitForTimeout(300);
      if (!/run and signed by Eric Habimana/.test(await page.locator('main').innerText())) problems.push('the check\u2019s record does not say who signed it');
      await page.selectOption('#guild-acting-as', 'p-sample-claudine');
      await page.evaluate(() => (location.hash = '#/guild/matrix'));
      await page.waitForTimeout(300);
      if ((await page.locator('[role="tablist"] [role="tab"]:has-text("Checks")').count()) !== 0) problems.push('a member who assesses nothing is shown the Checks tab');
      await page.locator('button:has-text("Hide the sample")').click();
      await page.waitForTimeout(200);
      await page.evaluate(() => (location.hash = '#/guild/matrix'));
      await page.waitForTimeout(300);
      if (!/Nobody is on the ledger yet/.test(await page.locator('body').innerText())) problems.push('hiding the sample left something behind');
      if (guildPosts.length) problems.push(`the sample sent ${guildPosts.length} write(s) to the service`);
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
      console.log('✓ guild        sample loads labelled; a suspension shows; a sign-off moves a cell; run mode asks for a cosigner and writes the cosigned step; a critical skill holds its step until a cosigner is recorded; a passed lesson makes Learning and My path names what it waits on; a practice session closes onto the learner\u2019s record; a check is run at the bench, signed, and read back with its assessor; the sample sends and leaves nothing; the first person is posted as lead and comes back after a reload');
    }
    await page.close();
  }

  await browser.close();
  server.close();

  console.log(`\n${ROUTES.length - failures.length}/${ROUTES.length} routes clean`);
  console.log(`${SHELVES.length - shelfFails}/${SHELVES.length} reference shelves render beneath a "not built" statement`);
  console.log(`${SEEDED.length - seededFails}/${SEEDED.length} seeded subsystems carry reference without a "not built" claim`);
  console.log(`${REDIRECTS.length - redirectFails}/${REDIRECTS.length} redirects land on the new screen`);
  console.log(`${1 - overlayFails}/1 overlay applied — fetched text in the reader, unanchored quotes listed, run scored`);
  console.log(`${OUTSIDE.length - confineFails}/${OUTSIDE.length} requests outside dist/ refused`);
  console.log(`${1 - guildFails}/1 Guild ledger flow — sample, sign-off, a cosigned run, a lesson and the path, practice, a bench check, first person, reload`);
  if (failures.length || redirectFails || shelfFails || seededFails || overlayFails || confineFails || guildFails) process.exit(1);
}

main();
