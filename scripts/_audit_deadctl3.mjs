import { chromium } from 'playwright';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
const ROOT = '/tmp/claude-0/-home-user-openFermentUI/167fd0e3-b3d3-562c-b052-449a10776bea/scratchpad/dist-dc';
const PORT = 4487;
const MIME = { '.html':'text/html','.js':'text/javascript','.css':'text/css','.woff2':'font/woff2','.woff':'font/woff','.svg':'image/svg+xml' };
const server = http.createServer((req,res)=>{const u=decodeURIComponent(req.url.split('?')[0]);let f=path.join(ROOT,u);if(!fs.existsSync(f)||fs.statSync(f).isDirectory())f=path.join(ROOT,'index.html');res.writeHead(200,{'Content-Type':MIME[path.extname(f)]??'application/octet-stream'});fs.createReadStream(f).pipe(res);});
await new Promise(r=>server.listen(PORT,r));
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
const ROUTES = process.argv.slice(2);
for (const route of ROUTES) {
  const page = await browser.newPage({ viewport:{width:1500,height:1000} });
  const errs=[]; page.on('pageerror',e=>errs.push(String(e)));
  const go = async () => { await page.goto(`http://localhost:${PORT}/#${route}`,{waitUntil:'domcontentloaded'}); await page.evaluate(x=>location.hash=x,route); await page.waitForTimeout(700); };
  await go();
  // enumerate buttons in main content only (skip shell chrome)
  const list = await page.evaluate(() => {
    const main = document.getElementById('of-main'); if (!main) return [];
    const out = [];
    main.querySelectorAll('button').forEach((el, i) => {
      const r = el.getBoundingClientRect();
      if (r.width===0 && r.height===0) return;
      if (el.matches(':disabled')) return;
      out.push({ i, label: (el.getAttribute('aria-label')||el.textContent||'').trim().replace(/\s+/g,' ').slice(0,60) });
    });
    return out;
  });
  console.log(`\n===== ${route}  (${list.length} enabled buttons in main)`);
  const seen = new Set();
  for (const item of list) {
    if (seen.has(item.label)) continue; seen.add(item.label);
    await go();
    const before = await page.evaluate(() => ({ h: location.hash, t: document.body.innerText.replace(/\s+/g,' '), o: document.querySelectorAll('[role=dialog],[data-popover],[role=tooltip]').length }));
    const clicked = await page.evaluate((idx) => {
      const main = document.getElementById('of-main');
      const els = [...main.querySelectorAll('button')].filter(el=>{const r=el.getBoundingClientRect();return (r.width||r.height) && !el.matches(':disabled');});
      const el = els[idx]; if (!el) return false; el.scrollIntoView({block:'center'}); el.click(); return true;
    }, list.indexOf(item));
    if (!clicked) continue;
    await page.waitForTimeout(650);
    const after = await page.evaluate(() => ({ h: location.hash, t: document.body.innerText.replace(/\s+/g,' '), o: document.querySelectorAll('[role=dialog],[data-popover],[role=tooltip]').length }));
    const changed = before.h!==after.h || before.t!==after.t || before.o!==after.o;
    if (!changed) console.log('  NO-VISIBLE-CHANGE:', JSON.stringify(item.label));
  }
  if (errs.length) console.log('  ERRORS:', [...new Set(errs)].slice(0,4).join(' | '));
  await page.close();
}
await browser.close(); server.close();
