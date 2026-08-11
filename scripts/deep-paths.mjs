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
const server=createServer(async(rq,rs)=>{try{const u=decodeURIComponent((rq.url??'/').split('?')[0]);let f=join(DIST,u==='/'?'index.html':u);try{if((await stat(f)).isDirectory())f=join(f,'index.html');}catch{f=join(DIST,'index.html');}rs.writeHead(200,{'Content-Type':MIME[extname(f)]??'application/octet-stream'});rs.end(await readFile(f));}catch{rs.writeHead(404).end('nf');}});
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


await b.close(); server.close();
console.log(`\n${res.filter(Boolean).length}/${res.length} extra checks passed`);
if(errs.length){console.log('errors:'); [...new Set(errs)].slice(0,6).forEach(e=>console.log('  - '+e));}
