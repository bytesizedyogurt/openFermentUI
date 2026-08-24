/**
 * Reconciliation (OF-BLD-006 §5, §6).
 *
 * Drives a full loop: start a deposition against a locked runbook, report a
 * titre well below the prediction, close, and record the verdict.
 *
 * The last two assertions are the ones that matter most. §5 says the delta
 * "enters BioRepo as evidence, never as a parameter override" -- so after a
 * REFUTED reconciliation this checks that the runbook still predicts 8 g/L and
 * is still locked. One result under one set of conditions must not silently
 * shift a global value, and the only way to know it does not is to look.
 *
 *   pnpm build && node scripts/check-reconcile.mjs
 */
import { chromium } from 'playwright';
import { createServer } from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { join, extname } from 'node:path';
const DIST=join(process.cwd(),'dist'); const PORT=4390;
const MIME={'.html':'text/html','.js':'text/javascript','.css':'text/css','.woff2':'font/woff2','.woff':'font/woff'};
const server=createServer(async(req,res)=>{try{const u=decodeURIComponent((req.url??'/').split('?')[0]);
 let f=join(DIST,u==='/'?'index.html':u); try{if((await stat(f)).isDirectory())f=join(f,'index.html');}catch{f=join(DIST,'index.html');}
 const b=await readFile(f);res.writeHead(200,{'Content-Type':MIME[extname(f)]??'application/octet-stream'});res.end(b);}catch{res.writeHead(404).end('nf');}});
await new Promise(r=>server.listen(PORT,r));
const exe='/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const browser=await chromium.launch(existsSync(exe)?{executablePath:exe}:{});
let fails=0; const errs=[];
const ctx=await browser.newContext({viewport:{width:810,height:1200}});
const page=await ctx.newPage();
page.on('console',m=>{if(m.type()==='error'&&!/DevTools|favicon/i.test(m.text()))errs.push(m.text());});
page.on('pageerror',e=>errs.push('UNCAUGHT: '+e.message));
const check=(l,ok,x='')=>{console.log((ok?'✓':'✗')+' '+l+(x?'  '+x:''));if(!ok)fails++;};
const body=async()=>(await page.locator('body').innerText()).replace(/\s+/g,' ');
const go=async r=>{await page.goto(`http://localhost:${PORT}/#${r}`,{waitUntil:'networkidle'});await page.waitForTimeout(1200);};

await go('/runbooks/rb-taq-kigali');
await page.getByRole('button',{name:/Start a deposition/}).click(); await page.waitForTimeout(600);
await page.locator('div[role="dialog"] button').nth(1).click(); await page.waitForTimeout(1400);
await page.getByRole('button',{name:/Begin recording/}).click(); await page.waitForTimeout(1100);
const box=page.locator('textarea[aria-label="Describe what you observed"]');

// Predicted titre is 8 g/L. Report 5.1 → a clear miss.
await box.fill('titre came in at 5.1 g/L');
await page.getByRole('button',{name:/^Record$/}).click(); await page.waitForTimeout(600);
await page.getByRole('button',{name:/That is right/}).click(); await page.waitForTimeout(600);
await box.fill('the impeller seal was weeping from about hour six');
await page.getByRole('button',{name:/^Record$/}).click(); await page.waitForTimeout(600);

// Walk the run to its summary. The complete control is a raw button in the
// footer, labelled "Mark step complete" until the final step.
const completeBtn = page.locator('footer button', { hasText: /step complete|final step/ });
for (let i=0;i<60;i++){
  if (await page.getByRole('button',{name:/Close the deposition/}).count() > 0) break;
  if (await completeBtn.count() === 0) break;
  await completeBtn.first().click();
  await page.waitForTimeout(140);
}
await page.getByRole('button',{name:/Close the deposition/}).click();
await page.waitForTimeout(1600);
check('lands on the deposition record', page.url().includes('/depositions/'), page.url().split('#')[1]);

let t = await body();
check('reconciliation offered on close', t.includes('Predicted vs observed') || t.includes('PREDICTED VS OBSERVED'));
check('delta shown', t.includes('8') && t.includes('5.1') && /-3[0-9]%/.test(t), t.match(/-\d+%/)?.[0] ?? '');
check('suggests refuted', t.toLowerCase().includes('suggested: refuted'));
check('unmeasured predictions listed, not scored', t.toLowerCase().includes('predicted, not measured'));
check('observation kept verbatim', t.includes('impeller seal was weeping'));

await page.getByRole('button',{name:/Record as refuted/}).click();
await page.waitForTimeout(1200);
t = await body();
check('recorded as refuted', t.toLowerCase().includes('recorded as refuted'));
check('evidence released to BioRepo', t.includes('Released to BioRepo') || t.includes('RELEASED TO BIOREPO'));
check('carries measured provenance', t.includes('Measured · first-party'));
check('conditions attached', t.toLowerCase().includes('scale') && t.toLowerCase().includes('deviation') === false || t.toLowerCase().includes('under pr-'));
check('states it is evidence not an override', t.toLowerCase().includes('evidence, not an override'));

// The critical negative: the runbook's prediction must be untouched.
await go('/runbooks/rb-taq-kigali');
t = await body();
check('runbook prediction UNCHANGED at 8 g/L', t.includes('8 g/L'), 'no silent parameter override');
check('runbook still locked', t.includes('Frozen'));

console.log('\nconsole errors:', errs.length);
if (errs.length) console.log(errs.slice(0,4).join('\n'));
console.log(fails===0&&errs.length===0?'\nRECONCILIATION PASSES':`\n${fails} failures`);
await browser.close(); server.close();
process.exit(fails===0&&errs.length===0?0:1);
