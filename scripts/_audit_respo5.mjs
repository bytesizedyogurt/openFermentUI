import { chromium } from 'playwright';
import http from 'http'; import fs from 'fs'; import path from 'path';
const PORT=4443, DIST='/home/user/openFermentUI/dist';
const MIME={'.html':'text/html','.js':'text/javascript','.css':'text/css','.svg':'image/svg+xml','.woff':'font/woff','.woff2':'font/woff2'};
const server=http.createServer((req,res)=>{let p=decodeURIComponent(req.url.split('?')[0]);let f=path.join(DIST,p);if(!fs.existsSync(f)||fs.statSync(f).isDirectory())f=path.join(DIST,'index.html');res.writeHead(200,{'Content-Type':MIME[path.extname(f)]||'application/octet-stream'});fs.createReadStream(f).pipe(res);});
await new Promise(r=>server.listen(PORT,r));
const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium-1194/chrome-linux/chrome'});
const page=await (await b.newContext({viewport:{width:420,height:900}})).newPage();
const target = process.argv[2] || '/ledger';
await page.goto(`http://localhost:${PORT}/#${target}`,{waitUntil:'load'});
await page.waitForTimeout(700);
const R = await page.evaluate(()=>{
  function sel(el){let s=el.tagName.toLowerCase();if(el.id)s+='#'+el.id;const c=(el.getAttribute('class')||'').trim().split(/\s+/).filter(Boolean).join('.');if(c)s+='.'+c;return s;}
  const base=document.documentElement.scrollWidth;
  const log=[];
  let node=document.body, guard=0;
  while(guard++<40){
    let culprit=null;
    for(const ch of Array.from(node.children)){
      const prev=ch.style.display; ch.style.display='none';
      const sw=document.documentElement.scrollWidth;
      ch.style.display=prev;
      if(sw<base-1){ culprit=ch; break; }
    }
    if(!culprit) break;
    log.push(sel(culprit));
    node=culprit;
  }
  const rows=[];
  for(const q of ['#of-main','#of-main > div','div.overflow-x-auto','div.overflow-x-auto > table','header','div.h-full.flex.flex-col','#root','body']){
    const el=document.querySelector(q); if(!el) {rows.push({q,missing:true}); continue;}
    const cs=getComputedStyle(el); const r=el.getBoundingClientRect();
    rows.push({q, rectL:Math.round(r.left), rectW:Math.round(r.width), clientW:el.clientWidth, scrollW:el.scrollWidth, ox:cs.overflowX, oy:cs.overflowY, disp:cs.display, pos:cs.position});
  }
  return {base, clientW:document.documentElement.clientWidth, chain:log, rows};
});
console.log(process.argv[2]||'/ledger', JSON.stringify(R,null,1));
await b.close(); server.close();
