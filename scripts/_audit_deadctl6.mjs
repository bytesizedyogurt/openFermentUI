import { chromium } from 'playwright';
import http from 'node:http'; import fs from 'node:fs'; import path from 'node:path';
const ROOT='/tmp/claude-0/-home-user-openFermentUI/167fd0e3-b3d3-562c-b052-449a10776bea/scratchpad/dist-dc';const PORT=4487;
const MIME={'.html':'text/html','.js':'text/javascript','.css':'text/css','.woff2':'font/woff2','.woff':'font/woff','.svg':'image/svg+xml'};
const server=http.createServer((q,r)=>{const u=decodeURIComponent(q.url.split('?')[0]);let f=path.join(ROOT,u);if(!fs.existsSync(f)||fs.statSync(f).isDirectory())f=path.join(ROOT,'index.html');r.writeHead(200,{'Content-Type':MIME[path.extname(f)]??'application/octet-stream'});fs.createReadStream(f).pipe(r);});
await new Promise(r=>server.listen(PORT,r));
const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium-1194/chrome-linux/chrome'});
const page=await b.newPage({viewport:{width:1500,height:1000}});
const go=async h=>{await page.goto(`http://localhost:${PORT}/#${h}`,{waitUntil:'domcontentloaded'});await page.evaluate(x=>location.hash=x,h);await page.waitForTimeout(1200);};
for (const t of ['[H4]','[I1]','[C2]','[K1]','[F1]','[J10]']) {
  await go('/assay');
  const loc = page.locator('#of-main button').filter({hasText: new RegExp('^' + t.replace(/[[]]/g, (m) => '\' + m) + '$')}).first();
  const cnt = await loc.count();
  if (!cnt) { console.log(t, 'not found'); continue; }
  await loc.scrollIntoViewIfNeeded().catch(()=>{});
  await loc.click({force:true}).catch(e=>console.log(t,'clickerr',String(e).slice(0,50)));
  await page.waitForTimeout(700);
  const d = await page.locator('[role=dialog]').count();
  console.log(t, 'dialogs:', d, '| aria-expanded:', await loc.getAttribute('aria-expanded'));
}
await b.close(); server.close();
