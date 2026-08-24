/**
 * Deposition flow (OF-BLD-006 §4).
 *
 * Driven at 810px tablet portrait, because that is the documented target for
 * RunMode and the constraints are the point: this test fails if any
 * interactive target in the extended screen drops below 44px, or if the page
 * starts scrolling sideways. RunMode was extended rather than rewritten, and
 * the accessibility guarantees it was built to are not allowed to erode
 * quietly underneath the new capture surface.
 *
 * It also pins the two asymmetries §4.3 and §4.4 rest on: a number matching
 * the schema demands a read-back, and narrative does not.
 *
 *   pnpm build && node scripts/check-deposition.mjs
 */
import { chromium } from 'playwright';
import { createServer } from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { join, extname } from 'node:path';
const DIST = join(process.cwd(),'dist'); const PORT = 4380;
const MIME = {'.html':'text/html','.js':'text/javascript','.css':'text/css','.woff2':'font/woff2','.woff':'font/woff'};
const server = createServer(async (req,res)=>{ try{const u=decodeURIComponent((req.url??'/').split('?')[0]);
  let f=join(DIST,u==='/'?'index.html':u);
  try{ if((await stat(f)).isDirectory()) f=join(f,'index.html'); }catch{ f=join(DIST,'index.html'); }
  const b=await readFile(f); res.writeHead(200,{'Content-Type':MIME[extname(f)]??'application/octet-stream'}); res.end(b);
}catch{res.writeHead(404).end('nf');}});
await new Promise(r=>server.listen(PORT,r));
const exe='/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const browser=await chromium.launch(existsSync(exe)?{executablePath:exe}:{});
let fails=0; const errs=[];
// 810px tablet portrait — the documented target for this screen.
const ctx=await browser.newContext({viewport:{width:810,height:1080}});
const page=await ctx.newPage();
page.on('console',m=>{if(m.type()==='error'&&!/DevTools|favicon/i.test(m.text()))errs.push(m.text());});
page.on('pageerror',e=>errs.push('UNCAUGHT: '+e.message));
const check=(l,ok,x='')=>{console.log((ok?'✓':'✗')+' '+l+(x?'  '+x:''));if(!ok)fails++;};
const body=async()=>(await page.locator('body').innerText()).replace(/\s+/g,' ');
const go=async r=>{await page.goto(`http://localhost:${PORT}/#${r}`,{waitUntil:'networkidle'});await page.waitForTimeout(1200);};

// Locked runbook offers the launch; unlocked one refuses.
await go('/runbooks/rb-lyo-ambient');
check('unlocked runbook blocks the bench', (await body()).includes('Lock the predictions first'));
await go('/runbooks/rb-taq-kigali');
check('locked runbook offers a deposition', (await body()).includes('Take this to a bench'));
await page.getByRole('button', { name: /Start a deposition/ }).click();
await page.waitForTimeout(600);
await page.locator('div[role="dialog"] button', { hasText: 'TAP medium' }).first().click().catch(async () => {
  await page.locator('div[role="dialog"] button').nth(1).click();
});
await page.waitForTimeout(1400);

// §4.5 staged
let t = await body();
check('lands on staged', t.includes('Deposition · staged') || t.includes('DEPOSITION · STAGED'));
check('schema visible before starting', t.includes('What will be recorded') || t.includes('WHAT WILL BE RECORDED'));
check('says it is the last moment to change it', t.toLowerCase().includes('last moment this list can change'));
check('quantities scaled', t.toLowerCase().includes('quantities at this scale'));
await page.getByRole('button', { name: /Begin recording/ }).click();
await page.waitForTimeout(1200);

// §4.3 capture
const box = page.locator('textarea[aria-label="Describe what you observed"]');
check('capture box present', await box.count() === 1);
await box.fill('titre came in at 7.4 g/L');
await page.waitForTimeout(500);
check('preview shows where it will file', (await body()).includes('files as'));
await page.getByRole('button', { name: /^Record$/ }).click();
await page.waitForTimeout(700);

// §4.4 read-back
t = await body();
check('number demands a read-back', t.toLowerCase().includes('read this back') || t.toLowerCase().includes('read these back'));
check('shows what was said', t.includes('you said'));
await page.getByRole('button', { name: /That is right/ }).click();
await page.waitForTimeout(600);
check('confirmation clears the prompt', !(await body()).toLowerCase().includes('read this back'));

// narrative flows without interruption
await box.fill('foam was worse than usual on the second impeller');
await page.waitForTimeout(400);
check('narrative previews as an observation', (await body()).includes('kept as an observation'));
await page.getByRole('button', { name: /^Record$/ }).click();
await page.waitForTimeout(700);
check('narrative did NOT demand a read-back', !(await body()).toLowerCase().includes('read this back'));

// accessibility constraints of the host screen must survive
const small = await page.evaluate(() => {
  const bad = [];
  for (const el of document.querySelectorAll('main button, main input, main textarea, footer button, header button')) {
    const r = el.getBoundingClientRect();
    if (r.width > 0 && r.height > 0 && r.height < 44) bad.push((el.textContent||el.tagName).trim().slice(0,28) + ` h=${Math.round(r.height)}`);
  }
  return bad;
});
check('every interactive target >= 44px', small.length === 0, small.slice(0,3).join(' | '));
check('no horizontal scroll at 810px', await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1));

console.log('\nconsole errors:', errs.length);
if (errs.length) console.log(errs.slice(0,4).join('\n'));
console.log(fails===0&&errs.length===0?'\nDEPOSITION FLOW PASSES':`\n${fails} failures`);
await browser.close(); server.close();
process.exit(fails===0&&errs.length===0?0:1);
