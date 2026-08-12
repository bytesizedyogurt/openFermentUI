import { chromium } from 'playwright';
import http from 'http'; import fs from 'fs'; import path from 'path';
const PORT=4441, DIST='/home/user/openFermentUI/dist';
const MIME={'.html':'text/html','.js':'text/javascript','.css':'text/css','.svg':'image/svg+xml','.woff':'font/woff','.woff2':'font/woff2'};
const server=http.createServer((req,res)=>{let p=decodeURIComponent(req.url.split('?')[0]);let f=path.join(DIST,p);if(!fs.existsSync(f)||fs.statSync(f).isDirectory())f=path.join(DIST,'index.html');res.writeHead(200,{'Content-Type':MIME[path.extname(f)]||'application/octet-stream'});fs.createReadStream(f).pipe(res);});
await new Promise(r=>server.listen(PORT,r));
const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium-1194/chrome-linux/chrome'});
const page=await (await b.newContext({viewport:{width:420,height:900}})).newPage();
await page.goto(`http://localhost:${PORT}/#/ledger`,{waitUntil:'load'});
await page.waitForTimeout(600);
const out = await page.evaluate(()=>{
  function sel(el){let s=el.tagName.toLowerCase();if(el.id)s+='#'+el.id;const c=(el.getAttribute('class')||'').trim().split(/\s+/).filter(Boolean).join('.');if(c)s+='.'+c;return s;}
  function pth(el){const a=[];let n=el;while(n&&n!==document.documentElement&&a.length<6){a.unshift(sel(n));n=n.parentElement}return a.join('\n    > ')}
  const de=document.documentElement;
  const res={de:{sw:de.scrollWidth,cw:de.clientWidth}, body:{sw:document.body.scrollWidth,cw:document.body.clientWidth}, chain:[]};
  // walk down finding elements whose scrollWidth exceeds clientWidth with visible overflow
  function walk(el,depth){
    if(depth>25) return;
    const cs=getComputedStyle(el);
    const d=el.scrollWidth-el.clientWidth;
    if(d>1 && (cs.overflowX==='visible')) res.chain.push({sel:sel(el), d, sw:el.scrollWidth, cw:el.clientWidth});
    for(const c of el.children) walk(c,depth+1);
  }
  walk(document.body,0);
  // widest descendant rect
  let widest=null;
  for(const el of document.querySelectorAll('body *')){ const cs=getComputedStyle(el); if(cs.display==='none')continue; const r=el.getBoundingClientRect(); if(!widest||r.right>widest.right) widest={right:r.right, sel:pth(el), w:r.width, pos:cs.position}; }
  res.widest=widest;
  const main=document.getElementById('of-main');
  res.main={sw:main.scrollWidth,cw:main.clientWidth,ox:getComputedStyle(main).overflowX};
  return res;
});
console.log(JSON.stringify(out,null,1));
await b.close(); server.close();
