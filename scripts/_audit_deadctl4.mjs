import { chromium } from 'playwright';
import http from 'node:http'; import fs from 'node:fs'; import path from 'node:path';
const ROOT='/tmp/claude-0/-home-user-openFermentUI/167fd0e3-b3d3-562c-b052-449a10776bea/scratchpad/dist-dc';const PORT=4487;
const MIME={'.html':'text/html','.js':'text/javascript','.css':'text/css','.woff2':'font/woff2','.woff':'font/woff','.svg':'image/svg+xml'};
const server=http.createServer((q,r)=>{const u=decodeURIComponent(q.url.split('?')[0]);let f=path.join(ROOT,u);if(!fs.existsSync(f)||fs.statSync(f).isDirectory())f=path.join(ROOT,'index.html');r.writeHead(200,{'Content-Type':MIME[path.extname(f)]??'application/octet-stream'});fs.createReadStream(f).pipe(r);});
await new Promise(r=>server.listen(PORT,r));
const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium-1194/chrome-linux/chrome'});
const page=await b.newPage({viewport:{width:1500,height:1000}});
page.on('pageerror',e=>console.log('PAGEERROR',String(e)));
const go=async h=>{await page.goto(`http://localhost:${PORT}/#${h}`,{waitUntil:'domcontentloaded'});await page.evaluate(x=>location.hash=x,h);await page.waitForTimeout(900);};

console.log('## strip-plot mark on /geneos/cw15');
await go('/geneos/cw15');
const mark = page.locator('button[aria-label*="Opens the quoted span"]').first();
console.log('marks:', await page.locator('button[aria-label*="Opens the quoted span"]').count());
const box = await mark.boundingBox();
console.log('bounding box:', JSON.stringify(box));
await mark.click({force:true});
await page.waitForTimeout(900);
console.log('hash after real click:', await page.evaluate(()=>location.hash));

console.log('\n## citation chip popover on /geneos/cw15');
await go('/geneos/cw15');
const chip = page.locator('button', { hasText: /^\[[A-Za-z0-9\-]+\]$/ }).first();
console.log('chips:', await page.locator('button').filter({hasText:/^\[[A-Za-z0-9\-]+\]$/}).count());
await chip.click();
await page.waitForTimeout(500);
console.log('dialog open:', await page.locator('[role=dialog]').count());
const dlg = await page.locator('[role=dialog]').first().innerText().catch(()=> 'none');
console.log('dialog text:', dlg.replace(/\s+/g,' ').slice(0,200));

console.log('\n## Runbook run mode full-screen');
await go('/runbook/PR-PHOS-01');
const startBtns = await page.locator('button').filter({hasText:/Start|Run/}).allTextContents();
console.log('buttons:', JSON.stringify(startBtns.slice(0,12)));
const start = page.locator('button').filter({hasText:/Start (a )?run|Start run/}).first();
if (await start.count()) {
  await start.click(); await page.waitForTimeout(1200);
  console.log('hash:', await page.evaluate(()=>location.hash));
  console.log('rail visible (should be hidden in run mode):', await page.locator('nav[aria-label="Primary"]').isVisible().catch(()=>false));
  console.log('top bar visible:', await page.locator('header').first().isVisible().catch(()=>false));
}
await b.close(); server.close();
