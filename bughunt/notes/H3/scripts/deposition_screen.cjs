// H3: what DepositionDetail draws for released measured evidence nobody read back, beside what the module
// read answers for the same row. Run after bench_doors.py, against ORIGIN (project p1):
//   node bughunt/notes/H3/scripts/deposition_screen.cjs http://127.0.0.1:8830 <shots dir>
const { chromium } = require('/home/user/openFermentUI/node_modules/playwright');
const origin = process.argv[2] || 'http://127.0.0.1:8830';
const shots = process.argv[3] || '.';
const H = { 'content-type': 'application/json', 'X-OpenFerment-Project': 'p1' };
(async () => {
  const rb = { id: 'rb1', kind: 'research', title: 'Bench check', status: 'draft',
    measurementSchema: [{ id: 'm1', label: 'Ethanol titre', unit: 'g/L', timepoint: 'harvest' }] };
  let r = await fetch(`${origin}/api/state/runbooks/rb1`, { method: 'PUT', headers: H, body: JSON.stringify({ by: 'Ada Lovelace', value: rb }) });
  console.log('runbook', r.status);
  const me = { id: 'me5', depositionId: 'dep1', runbookId: 'rb1', productId: null, predictionId: 'p1', label: 'Unread titre',
    value: 55.0, unit: 'g/L', provenance: 'measured', conditions: { protocolId: null, scale: 1, strainId: null },
    deviations: [], confirmed: false, at: '2026-11-09T10:00:00Z' };
  r = await fetch(`${origin}/api/state/measuredEvidence/me5`, { method: 'PUT', headers: H, body: JSON.stringify({ by: 'Ada Lovelace', value: me }) });
  console.log('measured evidence me5 (confirmed false)', r.status);
  r = await fetch(`${origin}/api/tools/runbooks_read?by=Ada%20Lovelace`, { method: 'POST', headers: H,
    body: JSON.stringify({ ids: ['runbooks/measured-evidence/me5'], words: '', kind: '', state: '', limit: 5 }) });
  const read = await r.json();
  console.log('module read of me5:', (read.rows || []).map((x) => `${x.ref} ${x.provenance}`));
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', proxy: undefined });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1800 } });
  await page.goto(`${origin}/#/p/p1/runbooks/depositions/dep1`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1500);
  const band = page.locator('section[aria-labelledby="band-evidence"]');
  const text = (await band.innerText().catch(() => '(no evidence band)')).replace(/\s+/g, ' ');
  console.log('evidence band text:', text.slice(0, 600));
  const ticks = await band.locator('[class*="tick-measured"]').count().catch(() => -1);
  console.log('measured ticks in the band:', ticks);
  await page.screenshot({ path: `${shots}/deposition-dep1.png`, fullPage: true });
  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
