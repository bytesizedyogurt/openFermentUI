import { chromium } from 'playwright';
import http from 'http'; import fs from 'fs'; import path from 'path';
const PORT=4444, DIST='/home/user/openFermentUI/dist';
const MIME={'.html':'text/html','.js':'text/javascript','.css':'text/css','.svg':'image/svg+xml','.woff':'font/woff','.woff2':'font/woff2'};
const server=http.createServer((req,res)=>{let p=decodeURIComponent(req.url.split('?')[0]);let f=path.join(DIST,p);if(!fs.existsSync(f)||fs.statSync(f).isDirectory())f=path.join(DIST,'index.html');res.writeHead(200,{'Content-Type':MIME[path.extname(f)]||'application/octet-stream'});fs.createReadStream(f).pipe(res);});
await new Promise(r=>server.listen(PORT,r));
const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium-1194/chrome-linux/chrome'});
const page=await (await b.newContext({viewport:{width:420,height:900}})).newPage();
const OUT='/tmp/claude-0/-home-user-openFermentUI/167fd0e3-b3d3-562c-b052-449a10776bea/scratchpad';
await page.goto(`http://localhost:${PORT}/#/ledger`,{waitUntil:'load'});
await page.waitForTimeout(700);
await page.screenshot({path:OUT+'/ledger420.png', fullPage:true});
await page.evaluate(()=>window.scrollTo(112,0));
await page.waitForTimeout(200);
await page.screenshot({path:OUT+'/ledger420-scrolled.png'});
// which element's box actually lives beyond x=420?
const r=await page.evaluate(()=>{
  function sel(el){let s=el.tagName.toLowerCase();if(el.id)s+='#'+el.id;const c=(el.getAttribute('class')||'').trim().split(/\s+/).filter(Boolean).join('.');if(c)s+='.'+c;return s;}
  const hits=[];
  for(let x=425;x<532;x+=20){ for(let y=40;y<880;y+=40){ const e=document.elementFromPoint(x-window.scrollX,y); if(e&&!hits.some(h=>h.el===e)) hits.push({el:e,x,y}); } }
  return hits.map(h=>({sel:sel(h.el), x:h.x, y:h.y, parent: h.el.parentElement?sel(h.el.parentElement):null}));
});
console.log(JSON.stringify(r,null,1));
await b.close(); server.close();
