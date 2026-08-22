/**
 * Deep-path checks (OF-DES-001 §8.5, §8.11, §8.13): the scripted ingest failure
 * and both its recovery routes, the protocol version diff, and scenario compare.
 * These are the paths the golden-path walk does not touch.
 */
import { chromium } from 'playwright';
import { createServer } from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { join, extname } from 'node:path';
const DIST = join(process.cwd(), 'dist');
const MIME={'.html':'text/html','.js':'text/javascript','.css':'text/css','.woff':'font/woff','.woff2':'font/woff2'};
const server=createServer(async(rq,rs)=>{try{const u=decodeURIComponent((rq.url??'/').split('?')[0]);let f=join(DIST,u==='/'?'index.html':u);try{if((await stat(f)).isDirectory())f=join(f,'index.html');}catch{f=join(DIST,'index.html');}const body=await readFile(f);rs.writeHead(200,{'Content-Type':MIME[extname(f)]??'application/octet-stream'});rs.end(body);}catch{if(!rs.headersSent)rs.writeHead(404);rs.end('nf');}});
await new Promise(r=>server.listen(4324,r));
const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium-1194/chrome-linux/chrome'});
const p=await b.newPage({viewport:{width:1600,height:1000}});
const errs=[];
p.on('pageerror',e=>errs.push(String(e).slice(0,200)));
p.on('console',m=>{if(m.type()==='error'&&!/DevTools|favicon/i.test(m.text()))errs.push(m.text().slice(0,200));});
const go=async h=>{await p.goto('http://localhost:4324/#'+h,{waitUntil:'networkidle'});await p.waitForTimeout(600);};
const res=[];
const ck=(n,ok,d='')=>{res.push(ok);console.log((ok?'✓ ':'✗ ')+n+(d?' — '+d:''));};

// Ingest: the scripted SP-020 parse failure and its recovery
await go('/trawl/ingest');
const shelfBtns = p.locator('button[aria-label*="to the ingest pipeline"]');
const n = await shelfBtns.count();
ck('Ingest queue lists tranche-1 entries', n>0, n+' entries');
const addBtn = shelfBtns.first();
if (await addBtn.count()) { await addBtn.click(); } else { await shelfBtns.last().click(); }
await p.waitForTimeout(6000);
const ingestTxt = await p.locator('body').innerText();
ck('Fetch failure names why the source could not be retrieved', /Source not retrieved/i.test(ingestTxt));
ck('Failure offers a recovery path', /Retry/i.test(ingestTxt));
// The corpus stays catalogued: nothing was fetched, so nothing joins as full text.
await go('/trawl');
const lib = await p.locator('body').innerText();
ck('Corpus still reports entries as catalogued', /catalogued/i.test(lib) || /curation note/i.test(lib));

// Correction propagation (OF-FE-003 §5.3). r-M8-3 is bound as a material source
// on PR-TAP-01, so editing it must visibly age that protocol with a numeric
// before/after — "stale" without the numbers tells a reader to redo work
// without telling them whether it matters.
await go('/ledger/records?record=r-M8-3');
await p.waitForTimeout(600);
await go('/trawl/review');
await p.waitForTimeout(800);
const staleBefore = await p.locator('body').innerText();
ck('Review queue reachable for the edit path', staleBefore.length > 200);

await p.evaluate(() => {
  // Drive the store directly: the point under test is propagation, not the
  // edit affordance, which the golden path already covers.
  const s = window.__ofStore?.getState?.();
  if (s) s.editRecord('r-M8-3', 4.2, s.records.find((r) => r.id === 'r-M8-3').unit);
});
await p.waitForTimeout(400);
await go('/runbook/PR-TAP-01');
await p.waitForTimeout(900);
const afterEdit = await p.locator('body').innerText();
ck('Editing a source record ages the protocol that consumed it', /Stale/i.test(afterEdit), afterEdit.match(/Stale[^\n]*/)?.[0] ?? 'no stale banner');
ck('Staleness carries the numeric before and after', /4\.2/.test(afterEdit) && /changed from/i.test(afterEdit));

// The joint (OF-FE-004 §1). Before assumptions carried an AssumptionBasis, no
// scenario bound a record and a correction could not reach an MSP. r-M5-1 is
// bound to sc-s1's biomass density, so editing it must age that scenario.
await p.evaluate(() => {
  const s = window.__ofStore?.getState?.();
  if (s) s.editRecord('r-M5-1', 1.9, s.records.find((r) => r.id === 'r-M5-1').unit);
});
await p.waitForTimeout(400);
const staleState = await p.evaluate(() => {
  const s = window.__ofStore?.getState?.();
  const patch = s.stale.find((x) => x.recordId === 'r-M5-1');
  return patch ? { scenarios: patch.dependents.scenarios, diff: patch.diff } : null;
});
ck('Correcting a bound record ages the scenario that consumed it',
   Boolean(staleState && staleState.scenarios.includes('sc-s1')),
   staleState ? staleState.scenarios.join(', ') : 'no patch');
ck('Scenario staleness carries the numeric before and after',
   Boolean(staleState && staleState.diff && staleState.diff.before === 1.23 && staleState.diff.after === 1.9));

// The unsourced assumption must be visible, not averaged away (§7.5).
await go('/fermos/s/sc-s2');
await p.waitForTimeout(900);
const s2 = await p.locator('body').innerText();
ck('An unsourced assumption is surfaced rather than suppressed', /no record and no declared justification/i.test(s2));

// Bench states the executable-layer coverage (§1.2).
await go('/');
await p.waitForTimeout(800);
const bench = await p.locator('body').innerText();
ck('Bench states how much of the corpus is wired to something executable', /feed something\s+executable|of 24 parameters are wired/i.test(bench.replace(/\s+/g,' ')));

// Route-rename regressions. Both of these survived 48 golden-path checks because
// the suite navigates to canonical routes and never exercises a legacy deep link
// or asserts on the shell chrome.
await go('/extract?paper=H4');
await p.waitForTimeout(700);
const aliasHash = await p.evaluate(() => location.hash);
const aliasTxt = await p.locator('body').innerText();
ck('A legacy /extract deep link lands on the record table, not the parameter index',
   /#\/ledger\/records/.test(aliasHash), aliasHash);
ck('...and keeps its ?paper= filter', /paper=H4/.test(aliasHash) && !/The 24 ontology fields/.test(aliasTxt));

// Run Mode takes the whole screen (§8.12): no left rail, no top bar.
await go('/runbook/PR-TAP-01');
await p.waitForTimeout(600);
const startBtn = p.locator('button', { hasText: /Start run/i }).first();
if (await startBtn.count()) {
  await startBtn.click();
  await p.waitForTimeout(900);
  const chrome = await p.evaluate(() => ({
    hash: location.hash,
    rail: Boolean(document.querySelector('a[href="#/ledger"]')),
    search: Boolean(document.querySelector('input[placeholder*="Search"]')),
  }));
  ck('Run Mode is reachable', /\/run\//.test(chrome.hash), chrome.hash);
  ck('Run Mode takes over the screen — rail and top bar are gone',
     !chrome.rail && !chrome.search,
     `rail=${chrome.rail} search=${chrome.search}`);
} else {
  ck('Run Mode is reachable', false, 'no Start run button');
}

// openLab deposit (OF-FE-003 §8.7). The argument of the part is that a failure
// counts the same, so the check is that it deposits at all and renders in the
// feed rather than being filtered, greyed or sorted away.
await go('/openlab');
await p.waitForTimeout(700);
const emptyLab = await p.locator('body').innerText();
ck('openLab starts empty and says why nothing was seeded', /No deposits yet/i.test(emptyLab));

await p.evaluate(() => {
  const s = window.__ofStore?.getState?.();
  if (!s) return;
  s.depositRun({
    runId: 'run-probe',
    outcome: 'failure',
    failureReason: 'Contamination in the 5 L flask at 18 h; culture discarded before induction.',
    results: {},
    operator: 'harness',
    producedRecordIds: [],
  });
});
await p.waitForTimeout(400);
const withDeposit = await p.locator('body').innerText();
ck('A failure deposits and appears in the feed', /Failure/.test(withDeposit) && /Contamination/.test(withDeposit));
ck('Failure rate is reported rather than hidden', /failure rate/i.test(withDeposit));

// Protocol version diff
await go('/runbook/PR-TAP-01');
const cmp = p.locator('button',{hasText:/compare version/i}).first();
if (await cmp.count()){
  await cmp.click(); await p.waitForTimeout(800);
  const d = await p.locator('body').innerText();
  ck('Version diff shows real changes', /1\.0/.test(d) && /1\.1/.test(d) && /(acetate|changed|→)/i.test(d));
} else ck('Version diff shows real changes', false, 'compare button missing');

// Compare: pin two scenarios and read the auto-summary
await go('/fermos');
const pins = p.locator('button[aria-pressed]');
const pc = await pins.count();
for (let i=0;i<Math.min(2,pc);i++){ const el=pins.nth(i); if((await el.getAttribute('aria-pressed'))!=='true'){ await el.click(); await p.waitForTimeout(200);} }
await go('/fermos/compare');
const cmpTxt = await p.locator('body').innerText();
ck('Compare renders pinned scenarios', /Minimum selling price/i.test(cmpTxt));
ck('Compare generates an auto-summary sentence', /(undercuts|within a cent)/i.test(cmpTxt));

// ?record= is a scope, not decoration. Two screens link here with it, and for a
// while nothing read it: the link opened 134 unfiltered rows and left the
// reader to find one id by eye.
await go('/ledger/records?record=r-M8-3');
const scoped = await p.locator('#of-main').innerText();
const scopedRows = await p.locator('#of-main tbody tr').count();
ck('?record= narrows the table to that record', scopedRows === 1, scopedRows + ' rows');
ck('...and names the scope with a way out', /Scoped to/.test(scoped) && /Show every record/.test(scoped));
await go('/ledger/records?record=r-not-a-record');
ck('An id from a dead session is explained, not shown as an empty grid',
   /No record r-not-a-record/.test(await p.locator('#of-main').innerText()));

// Dense mode has to save vertical space, not just repaint the tokens. One
// wrapping cell pins a row open and the whole setting becomes decorative — the
// record table sat at 69px rows while --row-h said 30.
await go('/ledger/records');
const rowH = async () => p.evaluate(() => {
  const tr = document.querySelector('#of-main tbody tr');
  const t = document.querySelector('#of-main table');
  return { row: tr ? Math.round(tr.getBoundingClientRect().height) : 0,
           table: t ? Math.round(t.getBoundingClientRect().height) : 0 };
});
const comfy = await rowH();
await p.keyboard.press('Shift+D'); await p.waitForTimeout(500);
const dense = await rowH();
ck('Dense mode actually shortens the record table',
   dense.row < comfy.row && dense.table < comfy.table,
   `row ${comfy.row}→${dense.row}px, table ${comfy.table}→${dense.table}px`);
await p.keyboard.press('Shift+D'); await p.waitForTimeout(400);

// MOBILE NAVIGATION. Below `md` the rail is `hidden md:flex`, and the only
// control used to be a SEARCH icon labelled "Menu" that opened the command
// palette — the label was a lie and the thirteen parts were reachable on a
// phone only by typing their names.
{
  const phone = await b.newPage({ viewport: { width: 390, height: 844 } });
  await phone.goto('http://localhost:4324/#/', { waitUntil: 'networkidle' });
  await phone.waitForTimeout(700);
  const nav = phone.locator('button[aria-label="Open navigation"]');
  const hasNav = (await nav.count()) > 0;
  ck('A phone has a navigation control', hasNav);
  if (hasNav) {
    await nav.click();
    await phone.waitForTimeout(500);
    const names = await phone.evaluate(() => {
      const d = document.querySelector('[role="dialog"]');
      return d ? [...d.querySelectorAll('a')].map((a) => a.getAttribute('aria-label') ?? a.textContent.trim()) : [];
    });
    ck('...reaching all thirteen parts', names.length === 13, `${names.length}: ${names.slice(0, 3).join(' / ')}`);
    // A visual gap is not a textual one: without an explicit label the name
    // reads "Intakeg t".
    ck('...each with a legible accessible name', names.every((n) => /shortcut g then \w/.test(n)), names[0] ?? '');
    await phone.locator('[role="dialog"] a').first().click();
    await phone.waitForTimeout(700);
    const closed = (await phone.locator('[role="dialog"]').count()) === 0;
    const moved = await phone.evaluate(() => location.hash);
    ck('...and tapping one navigates and closes the sheet', closed && moved !== '#/', `${moved} sheet=${closed ? 'closed' : 'OPEN'}`);
  }
  await phone.close();
}

// ROUTE-CHANGE ACCESSIBILITY. None of this existed: no skip link, no focus
// management, no announcement. A keyboard reader tabbed the whole rail on every
// navigation and a screen-reader user was told nothing had happened.
// A genuine ARRIVAL, not a navigation. `go()` cannot produce one here: two
// URLs differing only in the hash are a same-document fragment navigation, so
// `p.goto('…/#/')` from another route never reloads and the app correctly
// treats it as a route change. Forcing a reload is what makes this an arrival.
await go('/');
await p.reload({ waitUntil: 'networkidle' });
await p.waitForTimeout(700);
{
  await p.keyboard.press('Tab');
  await p.waitForTimeout(320);
  const first = await p.evaluate(() => {
    const a = document.activeElement;
    const r = a?.getBoundingClientRect();
    return {
      text: a?.textContent?.trim() ?? '',
      onScreen: r ? r.top >= 0 && r.bottom <= innerHeight : false,
    };
  });
  ck('The first tab stop is a skip link', /skip to the main content/i.test(first.text), first.text.slice(0, 40));
  ck('...and it is visible once focused', first.onScreen);

  // The trap: `href="#of-main"` is the CONVENTIONAL skip link and it breaks a
  // hash router — the fragment is the route, so it navigates to a path called
  // `of-main` and lands the reader on "Route not found". Written that way once.
  await p.keyboard.press('Enter');
  await p.waitForTimeout(350);
  const after = await p.locator('#of-main').innerText();
  ck(
    '...and activating it does not navigate away from the page',
    !/Route not found/i.test(after),
    after.trim().slice(0, 50).replace(/\s+/g, ' '),
  );
}

for (const [route, expect] of [['/ledger', /Parameters/i], ['/repo', /BioRepo/i]]) {
  await go(route);
  await p.waitForTimeout(600);
  // Arriving is not navigating: focus must NOT be taken on first paint, or the
  // skip link is unreachable. So navigate once more within the SPA and check.
  await p.evaluate((h) => { location.hash = h; }, route === '/ledger' ? '/repo' : '/ledger');
  await p.waitForTimeout(700);
  await p.evaluate((h) => { location.hash = h; }, route);
  await p.waitForTimeout(700);
  const st = await p.evaluate(() => ({
    tag: document.activeElement?.tagName ?? '',
    focused: document.activeElement?.textContent?.trim().slice(0, 40) ?? '',
    live: document.querySelector('[aria-live="polite"]')?.textContent?.trim() ?? '',
  }));
  ck(`Navigating to ${route} moves focus to the heading`, st.tag === 'H1' && expect.test(st.focused), `${st.tag} "${st.focused}"`);
  ck('...and announces it', expect.test(st.live), st.live.slice(0, 40));
}

// MOTION. Two properties, both invisible to a typecheck and both the kind of
// thing that rots quietly: nothing animates longer than the slow token, and
// EVERY animation is inert under reduced motion. The second matters more —
// `reducedMotion` is a setting a person turns on because motion makes them
// unwell, and an animation that ignores it is not a polish bug.
for (const route of ['/', '/ledger/p/titer_intracellular', '/repo']) {
  await go(route);
  await p.waitForTimeout(500);
  const long = await p.evaluate(() => {
    // CSS time values come back normalised — `320ms` computes to `.32s` — so a
    // bare parseFloat reads 0.32 and every animation looks over budget. Parse
    // the unit, both here and for animationDuration.
    const ms = (v) => {
      const n = parseFloat(v);
      if (Number.isNaN(n)) return NaN;
      return v.trim().endsWith('ms') ? n : n * 1000;
    };
    const slow = ms(getComputedStyle(document.documentElement).getPropertyValue('--motion-slow')) || 320;
    const over = [];
    for (const el of document.querySelectorAll('*')) {
      for (const pseudo of [null, '::before', '::after']) {
        const cs = getComputedStyle(el, pseudo);
        if (cs.animationName === 'none') continue;
        const durs = cs.animationDuration.split(',').map(ms);
        const worst = Math.max(...durs.filter((n) => !Number.isNaN(n)), 0);
        if (worst > slow + 1) over.push(`${cs.animationName} ${worst}ms`);
      }
    }
    return [...new Set(over)];
  });
  ck(`No animation outruns --motion-slow on ${route}`, long.length === 0, long.join(', '));

  // Now with the setting on. The attribute is what App.tsx stamps.
  const moving = await p.evaluate(() => {
    document.documentElement.dataset.reducedMotion = 'true';
    const bad = [];
    for (const el of document.querySelectorAll('*')) {
      for (const pseudo of [null, '::before', '::after']) {
        const cs = getComputedStyle(el, pseudo);
        if (cs.animationName === 'none') continue;
        const durs = cs.animationDuration
          .split(',')
          .map((d) => (d.trim().endsWith('ms') ? parseFloat(d) : parseFloat(d) * 1000));
        if (Math.max(...durs.filter((n) => !Number.isNaN(n)), 0) > 1) bad.push(cs.animationName);
      }
    }
    delete document.documentElement.dataset.reducedMotion;
    return [...new Set(bad)];
  });
  ck(`Reduced motion stills every animation on ${route}`, moving.length === 0, moving.join(', '));
}

// The trace gesture (§the 2030 pass, workstream 1). Any provenance-bearing
// value can unfold its own address in place. Two things must hold, and neither
// is visible to a typecheck: the gesture must actually open, and its third step
// — the check that has not happened — must be in it. A trace that quietly
// dropped that step when it had nothing to show would turn the product's
// central admission into a footnote, which is the failure this exists to
// prevent.
for (const [route, idRe, poolName] of [
  ['/ledger/p/titer_intracellular', /Where r-[\w-]+ comes from/i, 'corpus record'],
  ['/notary/disclosures', /Where OF-A-\d+ comes from/i, 'demo Accession'],
]) {
  // eslint-disable-next-line no-unused-vars
  await go(route);
  await p.waitForTimeout(500);
  const trigger = p.locator('button[title*="press t to follow"]').first();
  const n = await p.locator('button[title*="press t to follow"]').count();
  if (!n) {
    ck(`A ${poolName} offers the trace gesture`, false, `no trigger on ${route}`);
    continue;
  }
  ck(`A ${poolName} offers the trace gesture`, true, `${n} on ${route}`);
  // Keyboard, not click: the gesture has to work without a mouse.
  await trigger.focus();
  await p.keyboard.press('t');
  await p.waitForTimeout(350);
  // Scoped to the PANEL, not the body. Against the body these assertions
  // passed even with the missing step deleted from the renderer — the words
  // appear elsewhere on both screens. A gate that cannot fail is not a gate.
  const panel = p.locator('[role="dialog"][aria-label^="Where "]');
  const opened = (await panel.count()) > 0;
  ck(`...and \`t\` opens the chain on a ${poolName}`, opened);
  if (!opened) continue;
  const inside = await panel.first().innerText();
  ck(`...labelled with the id it traces (${poolName})`, idRe.test(await panel.first().getAttribute('aria-label') ?? ''));
  // All four steps, by ORDINAL rather than by keyword. Keyword matching passed
  // with the step deleted, because "Held" and "Standing" appear on both screens
  // anyway; the ordinals only exist inside the chain.
  const ordinals = ['01', '02', '03', '04'].filter((n) => inside.includes(n));
  ck(
    `...with all four steps (${poolName})`,
    ordinals.length === 4,
    `found ${ordinals.join(' ')} — ${inside.replace(/\s+/g, ' ').slice(0, 80)}`,
  );
  await p.keyboard.press('Escape');
}

// Nothing in this corpus is verified, so a corpus trace must ALWAYS carry the
// missing-check step. This is the assertion the whole gesture exists for, and
// it is stated separately from the four-step check because the two fail for
// different reasons: one means the chain is broken, the other means the
// product stopped admitting what it has not done.
await go('/ledger/p/titer_intracellular');
await p.waitForTimeout(500);
{
  const trig = p.locator('button[title*="press t to follow"]').first();
  await trig.focus();
  await p.keyboard.press('t');
  await p.waitForTimeout(350);
  const panel = p.locator('[role="dialog"][aria-label^="Where "]');
  const inside = (await panel.count()) ? await panel.first().innerText() : '';
  ck(
    'An unverified corpus record admits nobody has checked it',
    /THE MISSING CHECK/i.test(inside) && /Nobody has checked/i.test(inside),
    inside.replace(/\s+/g, ' ').slice(0, 100),
  );
  await p.keyboard.press('Escape');
}

// The seed disclaimer must survive the error paths. `check:demo-seed` proves
// the string says what it must; this proves a reader actually reaches it. Nine
// demo screens used to early-return a bare EmptyState with no footer, so the
// one sentence saying the patent numbers are synthetic vanished on exactly the
// path a reader hits by following a stale link — when they are most likely to
// be looking at an id and wondering whether it is real.
const deadDemoIds = [
  '/fermos/runs/RUN-NOPE',
  '/geneos/routes/not-a-product',
  '/proforma/screen/PLT-KGL-01/c/NOPE',
  '/postdoc/tree/DLV-NOPE',
  '/runbook/design/RB-NOPE',
];
let missingDisclaimer = [];
for (const r of deadDemoIds) {
  await go(r);
  await p.waitForTimeout(300);
  const txt = await p.locator('#of-main').innerText();
  if (!/all citation identifiers, author names, patent numbers and assignees are synthetic/i.test(txt)) {
    missingDisclaimer.push(r);
  }
}
ck('A dead demo id still carries the seed disclaimer',
   missingDisclaimer.length === 0, missingDisclaimer.join(', '));

// The page never scrolls sideways. A table may scroll inside its own card; the
// main region may not, and a shrink-0 action slot beside a long title is the
// usual way that breaks.
const narrow = await b.newPage({ viewport: { width: 420, height: 900 } });
let overflow = [];
// The demo pool had never been measured narrow — every route here was a
// casein screen, and the demo suite's tables and chip rows are the widest
// things in the build.
for (const r of ['/ledger/records', '/fermos/s/sc-s1', '/runbook/PR-PHOS-01', '/trawl/ingest', '/',
                 '/repo', '/proforma/screen/PLT-KGL-01', '/proforma/price/sc-s2', '/parchment/families',
                 '/notary/disclosures']) {
  await narrow.goto('http://localhost:4324/#' + r, { waitUntil: 'networkidle' });
  await narrow.waitForTimeout(400);
  const over = await narrow.evaluate(() => {
    const el = document.getElementById('of-main');
    return el ? el.scrollWidth - el.clientWidth : 0;
  });
  if (over > 2) overflow.push(`${r} +${over}px`);
}
await narrow.close();
ck('No page-level horizontal overflow at 420px', overflow.length === 0, overflow.join(', '));

// fermOS owns the plant; Proforma owns the price. These checks walk both
// halves and, between them, the seam: an equipment list and a mass balance on
// one screen, a capital ladder and a cash flow that reaches zero at the quoted
// price on the other, and the split between bioSTEAM's correlations and ours
// stated rather than blended.
await go('/fermos/s/sc-s2/plant');
const plant = await p.locator('#of-main').innerText();
ck('The plant view lists sized equipment', /Bioreactor/i.test(plant) && /Centrifuge/i.test(plant));
ck('ThermoSTEAM is declared as not ported', /ThermoSTEAM is not ported/i.test(plant));
ck('MSP is stated as solved at NPV = 0, not summed', /NPV\s*=\s*0/i.test(plant));
// The seam: fermOS quotes Proforma's price rather than computing one, and says so.
ck('The plant names Proforma as the part that priced it',
   /Priced by Proforma/i.test(plant));
ck('...and links to where the price is argued',
   (await p.locator('#of-main a[href$="/proforma/price/sc-s2"]').count()) > 0);
// The economics is NOT here any more. A capital ladder on the process screen
// would mean the split had been announced and not performed.
ck('The plant screen no longer holds the capital ladder',
   !/Direct permanent investment/i.test(plant) && !/Cumulative NPV/i.test(plant));

const equipRows = await p.locator('#of-main table[data-table="equipment"] tbody tr').count();
ck('The equipment table has rows', equipRows > 5, equipRows + ' units');

// A design result behind a unit, one click away.
const firstUnit = p.locator('#of-main table[data-table="equipment"] tbody tr').first();
await firstUnit.click(); await p.waitForTimeout(400);
ck('A unit opens to its design results', /Design results/i.test(await p.locator('#of-main').innerText()));

// ── Proforma's corpus half ───────────────────────────────────────────────
await go('/proforma/price/sc-s2');
const price = await p.locator('#of-main').innerText();
ck('Proforma has a corpus surface at all', /β-casein corpus/i.test(price));
ck('...with a capital ladder that names each step',
   /Direct permanent investment/i.test(price) && /Total capital investment/i.test(price));
ck('...and a discounted cash flow', /Cumulative NPV/i.test(price) && /Discount factor/i.test(price));
ck('...solved at NPV = 0, not summed', /NPV\s*=\s*0/i.test(price));
const cashRows = await p.locator('#of-main table[data-table="cashflow"] tbody tr').count();
ck('The cash-flow table has rows', cashRows > 10, cashRows + ' years');
const costRows = await p.locator('#of-main table[data-table="equipment-cost"] tbody tr').count();
ck('The same equipment appears again, costed', costRows > 5, costRows + ' units');

// ── The cross-part round trip ────────────────────────────────────────────
//
// `screens/demo/Proforma.tsx`'s header calls the rescue link "the argument for
// the shared object pool": a candidate that fails Proforma's envelope at its
// naive operating point and survives at a de-rating fermOS worked out. The link
// existed in the markup and was unreachable in a browser, because nothing
// applied the rescue outside a gate. So this walks it.
await go('/proforma/screen/PLT-KGL-01');
const cap = await p.locator('#of-main').innerText();
ck('The capacity screen shows a promoted candidate, not just viable and excluded',
   /promoted/i.test(cap));
ck('...and marks the rescued one as rescued', /rescued/i.test(cap));

await go('/proforma/screen/PLT-KGL-01/c/CND-001');
const cand = await p.locator('#of-main').innerText();
ck('A rescued candidate explains what was changed and what it cost', /Rescued/i.test(cand));
const backToFermos = p.locator('#of-main a[href$="/fermos/gap/DLV-AR1-001"]');
ck('...and links back to the fermOS factor map that produced the de-rating',
   (await backToFermos.count()) > 0);
if (await backToFermos.count()) {
  await backToFermos.first().click();
  await p.waitForTimeout(500);
  ck('...and that link actually lands on the factor map',
     /factor map|gap map|Lysine process-space/i.test(await p.locator('#of-main').innerText()));
}

// The authored-versus-bioSTEAM split has to be visible on the algal route,
// where it is the whole caveat. Capital is Proforma's, so the callout is too —
// but fermOS still has to say the photobioreactor is unmodelled.
await go('/proforma/price/sc-s1');
const s1price = await p.locator('#of-main').innerText();
ck('The algal price declares how much capital is an authored correlation',
   /authored/i.test(s1price) && /photobioreactor/i.test(s1price));

await go('/fermos/s/sc-s1/plant');
const s1 = await p.locator('#of-main').innerText();
ck('...and the algal plant still states what it does not model',
   /authored/i.test(s1) && /photobioreactor/i.test(s1));

// Uncertainty is work, not decoration: nothing runs until it is asked for.
await go('/proforma/price/sc-s1');
const s1u = await p.locator('#of-main').innerText();
ck('Monte Carlo does not run on arrival', /No Monte Carlo has been run/i.test(s1u));
const mc = p.locator('button', { hasText: /Run the samples|Run 200 samples/ }).first();
if (await mc.count()) {
  await mc.click();
  await p.waitForTimeout(9000);
  const after = await p.locator('#of-main').innerText();
  ck('Monte Carlo reports percentiles and a rank correlation',
     /percentile/i.test(after) && /Spearman/i.test(after));
} else ck('Monte Carlo reports percentiles and a rank correlation', false, 'run button missing');

// The workbench: a flowsheet diagram, a stream table, and equipment attributes
// that actually re-simulate. These are the checks that would catch a control
// which changes a label and nothing else.
await go('/fermos/s/sc-s2/plant');
const wb = await p.locator('#of-main').innerText();
ck('The plant renders a flowsheet diagram', (await p.locator('#of-main svg[role="img"]').count()) > 0);
ck('...with a stream table beside it', /Source/.test(wb) && /Composition/i.test(wb));
ck('The powder’s purity is stated, not just its price', /purity/i.test(wb));

const unitNodes = p.locator('#of-main svg [role="button"], #of-main svg button');
if (await unitNodes.count()) {
  await unitNodes.first().click();
  await p.waitForTimeout(600);
  const opened = await p.locator('#of-main').innerText();
  ck('Clicking a unit in the diagram opens its bioSTEAM attributes',
     /tau|V_wf|vessel_material|heat_exchanger_type|split/.test(opened));
} else ck('Clicking a unit in the diagram opens its bioSTEAM attributes', false, 'no clickable unit node');

// THE DECISIVE ONE: an edited equipment attribute has to move Proforma's price,
// on fermOS's screen, without a navigation.
//
// This used to read `#of-main select` and take the first hit. That was not
// testing what its name said: the plant screen also carried the financial
// settings panel, whose CEPCI dropdown sits in the DOM whether or not a unit is
// selected, so the check passed by changing the COST INDEX — a basis change,
// not an equipment change. Splitting the screens moved the settings panel to
// Proforma and the assertion went red, which is how the substitution surfaced.
//
// Now it walks the diagram until it finds a unit that actually exposes an enum
// attribute (vessel_material, centrifuge_type, heat_exchanger_type), and edits
// that. Not every unit has one, and depending on which node the layout happens
// to place first is what made this fragile in the first place.
const before = await p.locator('#of-main').innerText();
const mspBefore = (before.match(/([\d,]+\.?\d*)\s*USD\s*kg/) || [])[1];
let sel = null;
const nodeCount = await unitNodes.count();
for (let i = 0; i < nodeCount; i += 1) {
  await unitNodes.nth(i).click();
  await p.waitForTimeout(350);
  const candidate = p.locator('#of-main select').first();
  if ((await candidate.count()) && (await candidate.locator('option').count()) > 1) {
    sel = candidate;
    break;
  }
}
if (sel) {
  const opts = await sel.locator('option').allTextContents();
  await sel.selectOption({ index: opts.length - 1 });
  await p.waitForTimeout(1200);
  const after = await p.locator('#of-main').innerText();
  const mspAfter = (after.match(/([\d,]+\.?\d*)\s*USD\s*kg/) || [])[1];
  ck('Editing a bioSTEAM attribute moves the price fermOS quotes from Proforma',
     !!mspBefore && mspBefore !== mspAfter, `${mspBefore} -> ${mspAfter}`);
  ck('...and the screen says the plant no longer matches the scenario',
     /modified|edited|no longer matches/i.test(after));
  // And the same edit has to be there when Proforma is asked directly — one
  // solve, two screens. Two copies of the overrides would show up exactly here.
  await go('/proforma/price/sc-s2');
  const priced = await p.locator('#of-main').innerText();
  const mspOnProforma = (priced.match(/([\d,]+\.?\d*)\s*USD\s*kg/) || [])[1];
  ck('...and Proforma quotes that same edited price, not the declared one',
     mspOnProforma === mspAfter, `fermOS ${mspAfter} vs Proforma ${mspOnProforma}`);
} else {
  ck('Editing a bioSTEAM attribute moves the price fermOS quotes from Proforma', false,
     'no unit in the diagram exposed an enum attribute');
}

// The tornado is derived, so it must say so rather than claiming a fixed ±20%
// swing it never performed. It sits on Proforma now: a chart whose bars are
// "what this does to the price" is economics, not process.
await go('/proforma/price/sc-s2');
const ws = await p.locator('#of-main').innerText();
ck('The tornado states it re-solves the plant', /re-solving the plant/i.test(ws));
ck('...and no longer claims a ±20% perturbation', !/±20%/.test(ws));

// And fermOS's workspace is a process screen again: it quotes the price and
// shows what the point BUILDS, rather than decomposing, ranking and sweeping it.
await go('/fermos/s/sc-s2');
const wsp = await p.locator('#of-main').innerText();
ck('The workspace shows what the point builds', /What this point builds/i.test(wsp));
ck('...and names Proforma as the part that priced it', /Priced by Proforma/i.test(wsp));
ck('...and no longer holds the cost build-up',
   !/Cost build-up/i.test(wsp) && !/Sensitivity/i.test(wsp));


// ── Going back means going back to where you were ────────────────────────
//
// Browser back returned to the right route at scroll position zero, so a reader
// two thousand pixels down a six-thousand-pixel statement came back to the top
// with no idea where they had been. And inside the published artifact the
// visible back button belongs to the HOST page, not to this app in its iframe,
// so there was no back at all for anybody reading the shared build.
await go('/proforma');
// A RELOAD, not just a `go`. The trail is in-memory and per-document, and
// `p.goto` between two URLs differing only by hash is a fragment navigation —
// the document survives, so this block would otherwise inherit the trail left
// by every test above it and "cold arrival" would be a lie.
await p.reload({ waitUntil: 'networkidle' });
await p.waitForTimeout(700);
const coldBack = await p.locator('#of-main a[data-back]').count();
ck('A cold arrival offers no back link', coldBack === 0);

await p.locator('#of-main a[href$="/proforma/price/sc-s2"]').first().click();
await p.waitForTimeout(1100);
const named = await p.locator('#of-main a[data-back]').first().innerText();
ck('...and one screen in, the back link NAMES where it goes', /Proforma/i.test(named), named);

await p.evaluate(() => document.getElementById('of-main').scrollTo({ top: 2200 }));
await p.waitForTimeout(250);
await p.locator('#of-main a[href$="/fermos/s/sc-s2/plant"]').first().click();
await p.waitForTimeout(1100);
const freshTop = await p.evaluate(() => document.getElementById('of-main').scrollTop);
ck('A screen you have not seen opens at its top', freshTop < 40, String(freshTop));

await p.keyboard.press('Escape');
await p.waitForTimeout(1200);
const returned = await p.evaluate(() => ({
  hash: location.hash,
  top: document.getElementById('of-main').scrollTop,
}));
ck('Escape goes back to the screen you were on', /proforma\/price\/sc-s2/.test(returned.hash), returned.hash);
ck('...and to WHERE you were on it', Math.abs(returned.top - 2200) < 60, String(returned.top));

// An overlay owns the key first. Written the obvious way this was wrong: the
// shortcut sheet's Escape closed the sheet AND navigated, because its focus is
// on a button rather than in a field.
await p.keyboard.press('?');
await p.waitForTimeout(500);
await p.keyboard.press('Escape');
await p.waitForTimeout(900);
ck('An open overlay takes Escape before the router does',
   /proforma\/price\/sc-s2/.test(await p.evaluate(() => location.hash)));

await b.close(); server.close();
console.log(`\n${res.filter(Boolean).length}/${res.length} extra checks passed`);
if(errs.length){console.log('errors:'); [...new Set(errs)].slice(0,6).forEach(e=>console.log('  - '+e));}
