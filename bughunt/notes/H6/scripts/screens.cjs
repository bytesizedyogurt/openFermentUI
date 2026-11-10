// H6: open every screen of the head's app over a database alpha 2.1 filled and the head migrated, and say
// for each what it drew, its console errors, uncaught exceptions and failed requests.
//   node bughunt/notes/H6/scripts/screens.cjs ORIGIN PROJECT SHOTS_DIR > screens.log
// The list: every rail entry (src/data/nav.ts), the screens beyond the rail the smoke opens, and a detail page
// for each row the project holds (runs, artifacts, flowsheets, scenarios, comparisons, runbooks, depositions,
// conversations, catalogue entries, Guild's people, skills and checks, trains, lessons), each id read from the
// head's own routes. Chromium launches with no proxy; every request stays on the loopback origin.
const { chromium } = require('/home/user/openFermentUI/node_modules/playwright');
const fs = require('fs');
const origin = process.argv[2];
const project = process.argv[3];
const shots = process.argv[4];
const H = { 'X-OpenFerment-Project': project };
const IGNORE = [/Download the React DevTools/i, /favicon/i];

async function json(path) {
  const r = await fetch(`${origin}${path}`, { headers: H });
  return r.ok ? r.json() : null;
}

(async () => {
  const nav = fs.readFileSync('/home/user/openFermentUI/src/data/nav.ts', 'utf8');
  const rail = [...nav.matchAll(/label: '([^']+)',\s*\n\s*to: '([^']+)'/g)].map((m) => [m[1], m[2]]);
  const also = [['Studies', '/proforma/studies'], ['Settings', '/settings'], ['Products', '/catalogues/products'],
    ['Skills', '/catalogues/skills'], ['Lessons', '/catalogues/lessons'], ['Flowsheets', '/flowsheets'],
    ['Protocols', '/runbooks/protocols'], ['Depositions', '/runbooks/depositions'], ['Witness', '/biorepo/witness'],
    ['Ledger', '/runbooks/ledger'], ['Artifacts', '/biorepo/artifacts'], ['Guild people', '/guild/people'],
    ['Guild skills', '/guild/skills'], ['Guild checks', '/guild/checks'], ['Guild matrix', '/guild/matrix'],
    ['Primer path', '/primer/path'], ['Intake ingest', '/intake/ingest'], ['Builder', '/pureos/build']];
  const pages = [...rail, ...also];
  const runs = (await json('/api/runs')) || [];
  for (const r of runs) pages.push([`run ${r.id} (${r.engine} ${r.plant})`, `/proforma/runs/${r.id}`]);
  const arts = (await json('/api/biorepo/artifacts')) || [];
  for (const a of (Array.isArray(arts) ? arts : arts.artifacts || [])) pages.push([`artifact ${a.id} (${a.tool})`, `/biorepo/artifacts/${a.id}`]);
  for (const f of (await json('/api/flowsheets')) || []) pages.push([`flowsheet ${f.id}`, `/flowsheets/${f.id}`]);
  for (const c of (await json('/api/studies/comparisons')) || []) pages.push([`comparison ${c.id}`, `/proforma/comparisons/${c.id}`]);
  const st = (await json('/api/state')) || {};
  for (const s of st.scenarios || []) pages.push([`proforma scenario ${s.id}`, `/proforma/scenario/${s.id}`]);
  for (const s of (await json('/api/studies/scenarios')) || []) pages.push([`study scenario ${s.id}`, `/proforma/scenario/${s.id}`]);
  for (const b of (await json('/api/studies/runbooks')) || []) pages.push([`runbook ${b.id}`, `/runbooks/${b.id}`]);
  for (const b of st.runbooks || []) pages.push([`page runbook ${b.id}`, `/runbooks/${b.id}`]);
  for (const r of st.refused || []) if (r.kind === 'runbooks') pages.push([`refused runbook ${r.id}`, `/runbooks/${r.id}`]);
  for (const d of st.depositions || []) pages.push([`deposition ${d.id}`, `/runbooks/depositions/${d.id}`]);
  for (const c of (await json('/api/conversations')) || []) pages.push([`conversation ${c.id}`, `/postdoc/${c.id}`]);
  for (const t of Object.keys(st.trains || {})) pages.push([`train ${t}`, `/pureos/build/${t}`]);
  for (const s of st.scenarios || []) pages.push([`pureOS train of ${s.id}`, `/pureos/train/${s.id}`]);
  for (const e of (await json('/api/catalogues/strain')) || []) pages.push([`strain ${e.id}`, `/geneos/hosts/${e.id}`]);
  for (const e of (await json('/api/catalogues/lesson')) || []) pages.push([`lesson ${e.id}`, `/primer/${e.id}`]);
  const guild = (await json('/api/guild')) || {};
  for (const p of guild.people || []) pages.push([`person ${p.id}`, `/guild/people/${p.id}`]);
  for (const e of (await json('/api/catalogues/skill')) || []) pages.push([`skill ${e.id}`, `/guild/skills/${e.id}`]);
  for (const c of ((await json('/api/guild/checks')) || {}).checks || []) pages.push([`check ${c.id}`, `/guild/checks/${c.id}`]);
  const docs = (await json('/api/literature/documents')) || [];
  for (const d of docs.slice(0, 3)) pages.push([`paper ${d.documentId}`, `/biorepo/paper/${d.documentId}`]);
  for (const id of ['corn_drygrind', 'cornstover_benchmark', 'cornstover']) pages.push([`reference ${id}`, `/proforma/reference/${id}`]);
  for (const id of ['ethanol', 'xylitol', 'cellulase']) pages.push([`product link ${id}`, `/catalogues/products?entry=${id}`]);

  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
  const out = [];
  let n = 0;
  for (const [label, to] of pages) {
    n += 1;
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 1100 } });
    const page = await ctx.newPage();
    const errors = [];
    const failed = [];
    page.on('console', (m) => { if (m.type() === 'error' && !IGNORE.some((re) => re.test(m.text()))) errors.push(m.text().slice(0, 300)); });
    page.on('pageerror', (e) => errors.push(`uncaught: ${String(e).slice(0, 300)}`));
    page.on('response', (r) => { if (r.status() >= 400 && r.url().startsWith(origin)) failed.push(`${r.status()} ${r.request().method()} ${r.url().replace(origin, '')}`); });
    page.on('requestfailed', (r) => failed.push(`failed ${r.method()} ${r.url().replace(origin, '')} ${r.failure()?.errorText}`));
    const url = `${origin}/#/p/${encodeURIComponent(project)}${to === '/' ? '' : to}`;
    let text = '';
    try {
      await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
      await page.waitForTimeout(1200);
      text = (await page.locator('#of-main').innerText({ timeout: 5000 }).catch(() => page.locator('body').innerText())).replace(/\s+/g, ' ');
    } catch (e) {
      errors.push(`navigation: ${String(e).split('\n')[0]}`);
    }
    const bad = /Route not found|Something went wrong|doesn.t match a screen|could not be read|not found/i.exec(text);
    const row = { label, to, chars: text.length, errors, failed, flagged: bad ? bad[0] : null, head: text.slice(0, 260) };
    out.push(row);
    console.log(`${errors.length || failed.length || bad ? '✗' : '✓'} ${label} #${to} (${text.length} chars)`
      + (errors.length ? `\n    console: ${errors.join(' | ')}` : '') + (failed.length ? `\n    requests: ${failed.join(' | ')}` : '')
      + (bad ? `\n    says: ${text.slice(Math.max(0, bad.index - 120), bad.index + 160)}` : ''));
    await page.screenshot({ path: `${shots}/${String(n).padStart(3, '0')}.png`, fullPage: false }).catch(() => {});
    await ctx.close();
  }
  fs.writeFileSync(`${shots}/screens.json`, JSON.stringify(out, null, 1));
  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
