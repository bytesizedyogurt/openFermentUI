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
                 '/repo', '/proforma/screen/PLT-KGL-01', '/parchment/families', '/notary/disclosures']) {
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

// fermOS is a plant now, not a cost curve. The checks below are the ones that
// would have caught the old model pretending to be one: an equipment list, a
// cash flow that reaches zero at the quoted price, and the split between
// bioSTEAM's correlations and ours stated rather than blended.
await go('/fermos/s/sc-s2/plant');
const plant = await p.locator('#of-main').innerText();
ck('The plant view lists sized equipment', /Bioreactor/i.test(plant) && /Centrifuge/i.test(plant));
ck('...with a capital ladder that names each step',
   /Direct permanent investment/i.test(plant) && /Total capital investment/i.test(plant));
ck('...and a discounted cash flow', /Cumulative NPV/i.test(plant) && /Discount factor/i.test(plant));
ck('MSP is stated as solved at NPV = 0, not summed', /NPV\s*=\s*0/i.test(plant));
ck('ThermoSTEAM is declared as not ported', /ThermoSTEAM is not ported/i.test(plant));
const equipRows = await p.locator('#of-main table[data-table="equipment"] tbody tr').count();
const cashRows = await p.locator('#of-main table[data-table="cashflow"] tbody tr').count();
ck('The equipment and cash-flow tables have rows', equipRows > 5 && cashRows > 10,
   equipRows + ' units, ' + cashRows + ' years');

// A design result behind a purchase cost, one click away.
const firstUnit = p.locator('#of-main table[data-table="equipment"] tbody tr').first();
await firstUnit.click(); await p.waitForTimeout(400);
ck('A unit opens to its design results', /Design results/i.test(await p.locator('#of-main').innerText()));

// The authored-versus-bioSTEAM split has to be visible on the algal route,
// where it is the whole caveat.
await go('/fermos/s/sc-s1/plant');
const s1 = await p.locator('#of-main').innerText();
ck('The algal plant declares how much capital is an authored correlation',
   /authored/i.test(s1) && /photobioreactor/i.test(s1));

// Uncertainty is work, not decoration: nothing runs until it is asked for.
ck('Monte Carlo does not run on arrival', /No Monte Carlo has been run/i.test(s1));
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

const unitNode = p.locator('#of-main svg [role="button"], #of-main svg button').first();
if (await unitNode.count()) {
  await unitNode.click();
  await p.waitForTimeout(600);
  const opened = await p.locator('#of-main').innerText();
  ck('Clicking a unit in the diagram opens its bioSTEAM attributes',
     /tau|V_wf|vessel_material|heat_exchanger_type|split/.test(opened));
} else ck('Clicking a unit in the diagram opens its bioSTEAM attributes', false, 'no clickable unit node');

// The decisive one: an edited attribute has to move the number.
const before = await p.locator('#of-main').innerText();
const mspBefore = (before.match(/([\d,]+\.?\d*)\s*USD\s*kg/) || [])[1];
const sel = p.locator('#of-main select').first();
if (await sel.count()) {
  const opts = await sel.locator('option').allTextContents();
  if (opts.length > 1) {
    await sel.selectOption({ index: opts.length - 1 });
    await p.waitForTimeout(1200);
    const after = await p.locator('#of-main').innerText();
    const mspAfter = (after.match(/([\d,]+\.?\d*)\s*USD\s*kg/) || [])[1];
    ck('Editing a bioSTEAM attribute re-solves the plant', !!mspBefore && mspBefore !== mspAfter,
       `${mspBefore} -> ${mspAfter}`);
    ck('...and the screen says the plant no longer matches the scenario',
       /modified|edited|no longer matches/i.test(after));
  } else ck('Editing a bioSTEAM attribute re-solves the plant', false, 'select had one option');
} else ck('Editing a bioSTEAM attribute re-solves the plant', false, 'no select control found');

// The tornado in the workspace is derived now, so it must say so rather than
// claiming a fixed ±20% swing it never performed.
await go('/fermos/s/sc-s2');
const ws = await p.locator('#of-main').innerText();
ck('The workspace tornado states it re-solves the plant', /re-solving the plant/i.test(ws));
ck('...and no longer claims a ±20% perturbation', !/±20%/.test(ws));

await b.close(); server.close();
console.log(`\n${res.filter(Boolean).length}/${res.length} extra checks passed`);
if(errs.length){console.log('errors:'); [...new Set(errs)].slice(0,6).forEach(e=>console.log('  - '+e));}
