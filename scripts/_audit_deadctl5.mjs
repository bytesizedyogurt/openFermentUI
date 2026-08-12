import { chromium } from 'playwright';
import http from 'node:http'; import fs from 'node:fs'; import path from 'node:path';
const ROOT='/tmp/claude-0/-home-user-openFermentUI/167fd0e3-b3d3-562c-b052-449a10776bea/scratchpad/dist-dc';const PORT=4487;
const MIME={'.html':'text/html','.js':'text/javascript','.css':'text/css','.woff2':'font/woff2','.woff':'font/woff','.svg':'image/svg+xml'};
const server=http.createServer((q,r)=>{const u=decodeURIComponent(q.url.split('?')[0]);let f=path.join(ROOT,u);if(!fs.existsSync(f)||fs.statSync(f).isDirectory())f=path.join(ROOT,'index.html');r.writeHead(200,{'Content-Type':MIME[path.extname(f)]??'application/octet-stream'});fs.createReadStream(f).pipe(r);});
await new Promise(r=>server.listen(PORT,r));
const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium-1194/chrome-linux/chrome'});
const TAG = () => document.getElementById('of-main')?.querySelectorAll('button').forEach((el,i)=>el.setAttribute('data-aud', String(i)));
for (const route of process.argv.slice(2)) {
  const page=await b.newPage({viewport:{width:1500,height:1000}});
  const errs=[]; page.on('pageerror',e=>errs.push(String(e)));
  const go=async()=>{await page.goto(`http://localhost:${PORT}/#${route}`,{waitUntil:'domcontentloaded'});await page.evaluate(x=>location.hash=x,route);await page.waitForTimeout(1400);await page.evaluate(TAG);};
  await go();
  const list = await page.evaluate(()=>{const out=[];document.getElementById('of-main').querySelectorAll('button[data-aud]').forEach(el=>{const r=el.getBoundingClientRect();if(!r.width&&!r.height)return;if(el.matches(':disabled'))return;out.push({k:el.getAttribute('data-aud'),label:(el.getAttribute('aria-label')||el.textContent||'').trim().replace(/\s+/g,' ').slice(0,70),pressed:el.getAttribute('aria-pressed'),cls:(typeof el.className==='string'?el.className:'').slice(0,90)});});return out;});
  console.log(`\n===== ${route}  (${list.length} enabled)`);
  const seenLabel=new Set();
  for (const it of list) {
    if (seenLabel.has(it.label+it.pressed)) continue; seenLabel.add(it.label+it.pressed);
    if (it.pressed === 'true') continue; // already-active toggle: no-op is correct
    await go();
    const before = await page.evaluate(()=>({h:location.hash,t:document.body.innerText.replace(/\s+/g,' ')}));
    const loc = page.locator(`#of-main button[data-aud="${it.k}"]`);
    if (!(await loc.count())) { console.log('  MISSING after reload:', it.label); continue; }
    try { await loc.scrollIntoViewIfNeeded({timeout:2000}); } catch {}
    await page.waitForTimeout(320);
    try { await loc.click({timeout:3000, force:true}); } catch(e) { console.log('  CLICK-FAIL:', it.label, String(e).slice(0,60)); continue; }
    await page.waitForTimeout(800);
    const after = await page.evaluate(()=>({h:location.hash,t:document.body.innerText.replace(/\s+/g,' ')}));
    if (before.h===after.h && before.t===after.t) console.log('  NO-VISIBLE-CHANGE:', JSON.stringify(it.label), '|', it.cls);
  }
  if (errs.length) console.log('  ERRORS:', [...new Set(errs)].slice(0,3).join(' | '));
  await page.close();
}
await b.close(); server.close();
