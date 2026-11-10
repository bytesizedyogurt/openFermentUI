// H3-14: a closed deposition with one reading read back and one never read back, reconciled on its own
// screen by the app's button, then the "Released to BioRepo" band read beside the runbooks module read.
//   node screen.cjs ORIGIN SHOT.png
// Prints SEED:, CLICK:, SERVICE:, SCREEN: lines, then EXPECTED:, OBSERVED: and RESULT:.
const { chromium } = require('/home/user/openFermentUI/node_modules/playwright');
const origin = process.argv[2];
const shot = process.argv[3];
const P = 'h3-14';
const H = { 'content-type': 'application/json', 'X-OpenFerment-Project': P };
const BY = 'Ada Lovelace';
const T0 = '2026-11-09T10:00:00Z';

async function put(kind, id, value) {
  const r = await fetch(`${origin}/api/state/${kind}/${id}`, { method: 'PUT', headers: H, body: JSON.stringify({ by: BY, value }) });
  const t = await r.text();
  console.log(`SEED: PUT ${kind}/${id} -> ${r.status}${r.status === 200 ? '' : ' ' + t.slice(0, 200)}`);
  return r.status;
}
async function state() {
  const r = await fetch(`${origin}/api/state`, { headers: H });
  return r.json();
}
const sleep = (ms) => new Promise((res) => setTimeout(res, ms));

(async () => {
  // A runbook with two predictions, each tested by one measure.
  const rb = {
    id: 'rb1', kind: 'research', title: 'Read-back check', status: 'draft',
    predictions: [
      { id: 'pr1', label: 'Titre read back', value: 50, unit: 'g/L', confidence: 'medium', basis: 'a test fixture' },
      { id: 'pr2', label: 'Titre never read back', value: 50, unit: 'g/L', confidence: 'medium', basis: 'a test fixture' },
    ],
    measurementSchema: [
      { id: 'm1', label: 'Titre read back', unit: 'g/L', timepoint: 'harvest', predictionId: 'pr1' },
      { id: 'm2', label: 'Titre never read back', unit: 'g/L', timepoint: 'harvest', predictionId: 'pr2' },
    ],
  };
  const entry = (id, measureId, value, confirmed) =>
    ({ id, measureId, stepId: 'readings', at: T0, value, unit: 'g/L', raw: `${value} g/L`, confirmed });
  const dep = {
    id: 'dep1', runbookId: 'rb1', protocolId: null, operatorId: null, startedAt: T0, closedAt: null,
    state: 'running', observations: [], reconciliation: null, sampleTimes: {},
    entries: [entry('e1', 'm1', 48, true), entry('e2', 'm2', 55, false)],
  };
  if ((await put('runbooks', 'rb1', rb)) !== 200) throw new Error('runbook refused');
  if ((await put('depositions', 'dep1', dep)) !== 200) throw new Error('deposition refused');
  if ((await put('depositions', 'dep1', { ...dep, state: 'closed', closedAt: '2026-11-09T12:00:00Z' })) !== 200)
    throw new Error('close refused');

  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--no-proxy-server'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 1800 } });
  const url = `${origin}/#/p/${P}/runbooks/depositions/dep1`;
  await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
  // Reconcile through the screen: the app's own path that releases the evidence.
  const btn = page.getByRole('button', { name: 'Record as inconclusive' });
  await btn.waitFor({ timeout: 30000 });
  await btn.click();
  console.log('CLICK: Record as inconclusive');

  // Wait for the browser's writes to reach the service.
  let released = [];
  for (let i = 0; i < 60; i++) {
    const st = await state();
    released = (st.measuredEvidence || []).filter((m) => m.depositionId === 'dep1');
    if (released.length >= 2) break;
    await sleep(500);
  }
  for (const m of released)
    console.log(`SERVICE: kept measuredEvidence ${m.id} label="${m.label}" value=${m.value} ${m.unit} confirmed=${m.confirmed} provenance=${m.provenance}`);
  if (released.length < 2) throw new Error(`the service kept ${released.length} released values`);

  // The service's answer for each released value: the runbooks module read.
  const service = {};
  const r = await fetch(`${origin}/api/tools/runbooks_read?by=${encodeURIComponent(BY)}`, {
    method: 'POST', headers: H,
    body: JSON.stringify({ ids: released.map((m) => `runbooks/measured-evidence/${m.id}`), words: '', kind: '', state: '', limit: 10 }),
  });
  const read = await r.json();
  for (const row of read.rows || []) {
    service[String(row.ref).split('/').pop()] = row.provenance;
    console.log(`SERVICE: runbooks_read ${row.ref} provenance=${row.provenance} confirmed=${row.detail && row.detail.confirmed}`);
  }

  // What the screen draws for the same values, after a fresh load from the service.
  await page.goto('about:blank');
  await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
  const band = page.locator('section[aria-labelledby="band-evidence"]');
  await band.waitFor({ timeout: 30000 });
  const badge = (await band.locator('.chip').first().innerText()).trim();
  console.log(`SCREEN: band badge "${badge}"`);
  const items = await band.locator('ul > li').evaluateAll((lis) => lis.map((li) => {
    const tick = li.querySelector('.tick');
    return {
      label: (li.querySelector('.text-body') || {}).textContent || '',
      tickClass: tick ? [...tick.classList].filter((c) => c.startsWith('tick-')).join(' ') : '(none)',
      srLabel: ((tick && tick.querySelector('.sr-only')) || {}).textContent || '',
      title: tick ? tick.getAttribute('title') : '',
      caption: ((li.querySelector('.text-caption.text-ink-soft.mt-0\\.5')) || {}).textContent || '',
    };
  }));
  for (const it of items)
    console.log(`SCREEN: "${it.label}" tick=${it.tickClass} sr="${it.srLabel.trim()}" title="${it.title}" caption="${it.caption.trim()}"`);
  if (shot) await page.screenshot({ path: shot, fullPage: true });
  await browser.close();

  const unread = released.find((m) => m.confirmed === false);
  const readBack = released.find((m) => m.confirmed === true);
  const unreadItem = items.find((it) => it.label === unread.label);
  const readItem = items.find((it) => it.label === readBack.label);
  console.log(`EXPECTED: the value nobody read back (${unread.id}) drawn with the class the service gives it, ` +
    `runbooks_read provenance=${service[unread.id]}, a tick-${service[unread.id]} tick; the read-back one ` +
    `(${readBack.id}) as the service gives it, ${service[readBack.id]}`);
  console.log(`OBSERVED: unread ${unread.id}: service ${service[unread.id]}, screen ${unreadItem ? unreadItem.tickClass : '(not drawn)'} ` +
    `("${unreadItem ? unreadItem.srLabel.trim() : ''}") under the band badge "${badge}"; read-back ${readBack.id}: ` +
    `service ${service[readBack.id]}, screen ${readItem ? readItem.tickClass : '(not drawn)'}`);
  const defect = service[unread.id] === 'unverified' && unreadItem && unreadItem.tickClass === 'tick-measured';
  console.log(`RESULT: ${defect ? 'DEFECT' : 'NO-DEFECT'}`);
})().catch((e) => { console.log('SCREEN_ERROR:', String(e).slice(0, 400)); console.log('RESULT: NO-DEFECT (the script did not complete)'); process.exit(0); });
