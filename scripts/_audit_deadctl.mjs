import { chromium } from 'playwright';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';

const ROOT = '/tmp/claude-0/-home-user-openFermentUI/167fd0e3-b3d3-562c-b052-449a10776bea/scratchpad/dist-dc';
const PORT = 4487;
const MIME = { '.html':'text/html', '.js':'text/javascript', '.css':'text/css', '.woff2':'font/woff2', '.woff':'font/woff', '.svg':'image/svg+xml', '.json':'application/json' };

const server = http.createServer((req, res) => {
  const u = decodeURIComponent(req.url.split('?')[0]);
  let f = path.join(ROOT, u);
  if (!fs.existsSync(f) || fs.statSync(f).isDirectory()) f = path.join(ROOT, 'index.html');
  const ext = path.extname(f);
  res.writeHead(200, { 'Content-Type': MIME[ext] ?? 'application/octet-stream' });
  fs.createReadStream(f).pipe(res);
});
await new Promise(r => server.listen(PORT, r));

const ROUTES = process.argv[2] ? process.argv[2].split(',') : [
  '/', '/trawl', '/trawl/sources/H4', '/trawl/review', '/trawl/ingest',
  '/ledger', '/ledger/p/titer_secreted', '/ledger/p/kinase_identity', '/ledger/records',
  '/ledger/contradictions', '/assay', '/geneos', '/geneos/cw15', '/fermos', '/fermos/s/sc-s1',
  '/fermos/d', '/fermos/d/sc-s1-d01', '/fermos/compare', '/parchment', '/postdoc', '/runbook',
  '/runbook/PR-PHOS-01', '/openlab', '/notary', '/learn', '/settings/appearance',
];

const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
const page = await browser.newPage({ viewport: { width: 1440, height: 950 } });
const errors = [];
page.on('pageerror', e => errors.push(String(e)));
page.on('console', m => { if (m.type() === 'error') errors.push('console: ' + m.text()); });

const SCAN = () => {
  const reactProps = (el) => {
    for (const k of Object.keys(el)) {
      if (k.startsWith('__reactProps$')) return el[k];
    }
    return null;
  };
  const vis = (el) => {
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) return false;
    const cs = getComputedStyle(el);
    return cs.visibility !== 'hidden' && cs.display !== 'none' && cs.opacity !== '0';
  };
  const label = (el) => (el.getAttribute('aria-label') || el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 70);
  const out = { buttons: [], links: [], pointerNoHandler: [], inputs: [] };

  for (const el of document.querySelectorAll('button, [role="button"]')) {
    if (!vis(el)) continue;
    const p = reactProps(el) || {};
    const handlers = Object.keys(p).filter(k => /^on[A-Z]/.test(k) && typeof p[k] === 'function');
    out.buttons.push({
      label: label(el),
      disabled: el.disabled === true || el.getAttribute('aria-disabled') === 'true',
      type: el.getAttribute('type'),
      handlers,
      cls: el.className && typeof el.className === 'string' ? el.className.slice(0,120) : '',
      inForm: !!el.closest('form'),
    });
  }
  for (const el of document.querySelectorAll('a')) {
    if (!vis(el)) continue;
    out.links.push({ label: label(el), href: el.getAttribute('href') });
  }
  for (const el of document.querySelectorAll('*')) {
    if (!vis(el)) continue;
    const cn = typeof el.className === 'string' ? el.className : '';
    if (!/cursor-pointer/.test(cn)) continue;
    if (el.tagName === 'BUTTON' || el.tagName === 'A' || el.closest('a') || el.closest('button')) continue;
    const p = reactProps(el) || {};
    const handlers = Object.keys(p).filter(k => /^on[A-Z]/.test(k) && typeof p[k] === 'function');
    // walk up for a handler on parent
    let anc = el.parentElement, ancH = [];
    while (anc && ancH.length === 0 && anc !== document.body) {
      const pp = reactProps(anc) || {};
      ancH = Object.keys(pp).filter(k => /^onClick$/.test(k) && typeof pp[k] === 'function');
      anc = anc.parentElement;
    }
    out.pointerNoHandler.push({ tag: el.tagName, label: label(el), handlers, ancestorHandler: ancH.length > 0, cls: cn.slice(0,120) });
  }
  for (const el of document.querySelectorAll('input, select, textarea')) {
    if (!vis(el)) continue;
    const p = reactProps(el) || {};
    const handlers = Object.keys(p).filter(k => /^on[A-Z]/.test(k) && typeof p[k] === 'function');
    out.inputs.push({ tag: el.tagName, type: el.getAttribute('type'), label: (el.getAttribute('aria-label')||el.getAttribute('placeholder')||el.name||'').slice(0,60), handlers, disabled: el.disabled === true });
  }
  return out;
};

const results = {};
for (const r of ROUTES) {
  await page.goto(`http://localhost:${PORT}/#${r}`, { waitUntil: 'domcontentloaded' });
  await page.evaluate((h) => { window.location.hash = h; }, r);
  await page.waitForTimeout(500);
  const notFound = await page.locator('text=Route not found').count();
  const data = await page.evaluate(SCAN);
  results[r] = { notFound, ...data, hash: await page.evaluate(() => location.hash) };
}
fs.writeFileSync('/tmp/claude-0/-home-user-openFermentUI/167fd0e3-b3d3-562c-b052-449a10776bea/scratchpad/scan.json', JSON.stringify(results, null, 1));

// Summary of suspicious items
for (const [r, d] of Object.entries(results)) {
  const dead = d.buttons.filter(b => !b.disabled && b.handlers.length === 0 && b.type !== 'submit' && !b.inForm);
  const ptr = d.pointerNoHandler.filter(p => p.handlers.length === 0 && !p.ancestorHandler);
  if (d.notFound || dead.length || ptr.length) {
    console.log('=== ' + r + (d.notFound ? '  [ROUTE NOT FOUND]' : ''));
    dead.forEach(b => console.log('   DEADBTN:', JSON.stringify(b.label), '|', b.cls));
    ptr.forEach(p => console.log('   PTR-NOHANDLER:', p.tag, JSON.stringify(p.label), '|', p.cls));
  }
}
console.log('\n--- page errors ---');
console.log([...new Set(errors)].slice(0,20).join('\n'));

// Verify every anchor href resolves
const allHrefs = new Set();
for (const [r, d] of Object.entries(results)) for (const l of d.links) if (l.href) allHrefs.add(l.href + ' <<< ' + r + ' :: ' + l.label);
fs.writeFileSync('/tmp/claude-0/-home-user-openFermentUI/167fd0e3-b3d3-562c-b052-449a10776bea/scratchpad/hrefs.txt', [...allHrefs].sort().join('\n'));
console.log('\nhrefs collected:', allHrefs.size);

await browser.close();
server.close();
