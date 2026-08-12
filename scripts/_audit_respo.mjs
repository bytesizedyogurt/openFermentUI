import { chromium } from 'playwright';
import http from 'http';
import fs from 'fs';
import path from 'path';

const PORT = 4437;
const DIST = '/home/user/openFermentUI/dist';
const MIME = { '.html':'text/html', '.js':'text/javascript', '.css':'text/css', '.json':'application/json', '.svg':'image/svg+xml', '.woff':'font/woff', '.woff2':'font/woff2', '.png':'image/png' };

const server = http.createServer((req,res)=>{
  let p = decodeURIComponent(req.url.split('?')[0]);
  let f = path.join(DIST, p);
  if (!fs.existsSync(f) || fs.statSync(f).isDirectory()) f = path.join(DIST,'index.html');
  res.writeHead(200, {'Content-Type': MIME[path.extname(f)] || 'application/octet-stream'});
  fs.createReadStream(f).pipe(res);
});
await new Promise(r=>server.listen(PORT,r));

const ROUTES = ['/', '/trawl', '/trawl/sources/H4', '/trawl/review', '/trawl/ingest',
 '/ledger', '/ledger/p/titer_secreted', '/ledger/p/kinase_identity', '/ledger/records',
 '/ledger/contradictions', '/assay', '/geneos', '/geneos/cw15', '/fermos', '/fermos/s/sc-s1',
 '/fermos/d', '/fermos/d/sc-s1-d01', '/fermos/compare', '/parchment', '/postdoc', '/runbook',
 '/runbook/PR-PHOS-01', '/openlab', '/notary', '/learn', '/settings/appearance'];
const WIDTHS = [1440, 1100, 900, 760, 420];

const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
const page = await ctx.newPage();
const errs = [];
page.on('pageerror', e => errs.push(String(e)));

const results = [];

const PROBE = () => {
  function sel(el){
    if(!el) return null;
    if(el===document.body) return 'body';
    let s = el.tagName.toLowerCase();
    if(el.id) s += '#'+el.id;
    const cls = (el.getAttribute('class')||'').trim().split(/\s+/).filter(Boolean).slice(0,8).join('.');
    if(cls) s += '.'+cls;
    return s;
  }
  function pathOf(el){
    const parts=[]; let n=el;
    while(n && n!==document.documentElement && parts.length<6){ parts.unshift(sel(n)); n=n.parentElement; }
    return parts.join(' > ');
  }
  const out = { doc:{}, main:{}, offenders:[], containers:[] };
  const de = document.documentElement, body=document.body;
  out.doc = { deScrollW: de.scrollWidth, deClientW: de.clientWidth, bodyScrollW: body.scrollWidth, bodyClientW: body.clientWidth, innerW: window.innerWidth };
  const main = document.getElementById('of-main');
  if(main){
    const cs = getComputedStyle(main);
    out.main = { scrollW: main.scrollWidth, clientW: main.clientWidth, overflowX: cs.overflowX, overflowY: cs.overflowY };
  }
  // find all elements whose right edge exceeds the main's client right edge
  const ref = main || body;
  const refRect = ref.getBoundingClientRect();
  const limit = refRect.left + ref.clientWidth;
  const all = document.querySelectorAll('#of-main *');
  const seen = new Set();
  for(const el of all){
    const cs = getComputedStyle(el);
    if(cs.display==='none'||cs.visibility==='hidden') continue;
    const r = el.getBoundingClientRect();
    if(r.width===0&&r.height===0) continue;
    const over = r.right - limit;
    if(over > 1){
      // is any ancestor between el and ref a horizontal scroll container? then it's contained
      let contained=false, a=el.parentElement;
      while(a && a!==ref){ const acs=getComputedStyle(a); if(acs.overflowX==='auto'||acs.overflowX==='scroll'||acs.overflowX==='hidden'){contained=true;break;} a=a.parentElement; }
      if(contained) continue;
      out.offenders.push({ sel: pathOf(el), over: Math.round(over*10)/10, w: Math.round(r.width), minW: cs.minWidth, width: cs.width, tag: el.tagName, text: (el.textContent||'').trim().slice(0,60) });
    }
  }
  // dedupe: keep only deepest-ish; sort by over desc
  out.offenders.sort((a,b)=>b.over-a.over);
  out.offenders = out.offenders.slice(0,14);

  // horizontal scroll containers inside main and whether they actually scroll
  for(const el of document.querySelectorAll('#of-main *')){
    const cs=getComputedStyle(el);
    if(cs.overflowX==='auto'||cs.overflowX==='scroll'){
      if(el.scrollWidth-el.clientWidth>1) out.containers.push({sel:pathOf(el), scrollW:el.scrollWidth, clientW:el.clientWidth, delta:el.scrollWidth-el.clientWidth});
    }
    if(cs.overflowX==='hidden' && el.scrollWidth-el.clientWidth>1){
      out.containers.push({sel:pathOf(el), scrollW:el.scrollWidth, clientW:el.clientWidth, delta:el.scrollWidth-el.clientWidth, clipped:true});
    }
  }
  // tables not in a scroll container
  out.tables = [];
  for(const t of document.querySelectorAll('#of-main table')){
    let a=t.parentElement, scroller=null;
    while(a && a.id!=='of-main'){ const acs=getComputedStyle(a); if(acs.overflowX==='auto'||acs.overflowX==='scroll'){scroller=a;break;} a=a.parentElement; }
    const tr=t.getBoundingClientRect();
    out.tables.push({ sel: pathOf(t), w: Math.round(tr.width), hasScroller: !!scroller, scrollerOverflowing: scroller? scroller.scrollWidth-scroller.clientWidth>1 : false, over: Math.round((tr.right-limit)*10)/10, minW: getComputedStyle(t).minWidth });
  }
  // rail
  const rail = document.querySelector('nav[aria-label="Primary"]');
  out.rail = rail ? { w: rail.getBoundingClientRect().width, display: getComputedStyle(rail).display } : null;
  return out;
};

for (const route of ROUTES) {
  for (const w of WIDTHS) {
    await page.setViewportSize({ width: w, height: 900 });
    await page.goto(`http://localhost:${PORT}/#${route}`, { waitUntil: 'load' });
    await page.evaluate((r)=>{ window.location.hash = r; }, route);
    await page.waitForTimeout(450);
    const r = await page.evaluate(PROBE);
    results.push({ route, w, ...r });
  }
}

fs.writeFileSync('/tmp/claude-0/-home-user-openFermentUI/167fd0e3-b3d3-562c-b052-449a10776bea/scratchpad/resp.json', JSON.stringify(results,null,1));

// terse report
for(const r of results){
  const docOver = r.doc.deScrollW - r.doc.deClientW;
  const mainOver = (r.main.scrollW||0) - (r.main.clientW||0);
  const flags=[];
  if(docOver>1) flags.push(`DOC+${docOver}`);
  if(mainOver>1) flags.push(`MAIN+${mainOver}`);
  if(flags.length || r.offenders.length){
    console.log(`\n=== ${r.route} @ ${r.w} ${flags.join(' ')} rail=${r.rail? r.rail.display+'/'+Math.round(r.rail.w):'none'}`);
    for(const o of r.offenders.slice(0,6)) console.log(`   +${o.over}px w=${o.w} minW=${o.minW} :: ${o.sel} :: ${JSON.stringify(o.text)}`);
  }
}
console.log('\nERRORS', errs.slice(0,5));
await browser.close(); server.close();
