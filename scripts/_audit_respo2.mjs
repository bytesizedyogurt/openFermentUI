import { chromium } from 'playwright';
import http from 'http'; import fs from 'fs'; import path from 'path';
const PORT=4438, DIST='/home/user/openFermentUI/dist';
const MIME={'.html':'text/html','.js':'text/javascript','.css':'text/css','.svg':'image/svg+xml','.woff':'font/woff','.woff2':'font/woff2'};
const server=http.createServer((req,res)=>{let p=decodeURIComponent(req.url.split('?')[0]);let f=path.join(DIST,p);if(!fs.existsSync(f)||fs.statSync(f).isDirectory())f=path.join(DIST,'index.html');res.writeHead(200,{'Content-Type':MIME[path.extname(f)]||'application/octet-stream'});fs.createReadStream(f).pipe(res);});
await new Promise(r=>server.listen(PORT,r));
const ROUTES=['/','/trawl','/trawl/sources/H4','/trawl/review','/trawl/ingest','/ledger','/ledger/p/titer_secreted','/ledger/p/kinase_identity','/ledger/records','/ledger/contradictions','/assay','/geneos','/geneos/cw15','/fermos','/fermos/s/sc-s1','/fermos/d','/fermos/d/sc-s1-d01','/fermos/compare','/parchment','/postdoc','/runbook','/runbook/PR-PHOS-01','/openlab','/notary','/learn','/settings/appearance'];
const WIDTHS=[1440,1100,900,760,420];
const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium-1194/chrome-linux/chrome'});
const ctx=await b.newContext({viewport:{width:1440,height:900}});
const page=await ctx.newPage();
const P=()=>{
 function sel(el){let s=el.tagName.toLowerCase();if(el.id)s+='#'+el.id;const c=(el.getAttribute('class')||'').trim().split(/\s+/).filter(Boolean).slice(0,10).join('.');if(c)s+='.'+c;return s;}
 function pth(el){const a=[];let n=el;while(n&&n!==document.documentElement&&a.length<5){a.unshift(sel(n));n=n.parentElement}return a.join(' > ')}
 const out={docOver:document.documentElement.scrollWidth-document.documentElement.clientWidth, global:[], clip:[], fixedW:[]};
 const lim=document.documentElement.clientWidth;
 // ANY element in the whole doc extending past viewport right edge, no containment check
 for(const el of document.querySelectorAll('body *')){
   const cs=getComputedStyle(el); if(cs.display==='none'||cs.visibility==='hidden')continue;
   const r=el.getBoundingClientRect(); if(!r.width&&!r.height)continue;
   if(cs.position==='fixed'||cs.position==='absolute'){ if(r.right-lim>1) out.global.push({sel:pth(el),over:Math.round(r.right-lim),pos:cs.position,w:Math.round(r.width)}); continue; }
   if(r.right-lim>1) out.global.push({sel:pth(el),over:Math.round(r.right-lim),pos:cs.position,w:Math.round(r.width),minW:cs.minWidth,cssW:cs.width});
 }
 out.global.sort((a,b)=>b.over-a.over); out.global=out.global.slice(0,20);
 // real clipping: overflow hidden ancestor cutting a NON-truncating child
 for(const el of document.querySelectorAll('#of-main *')){
   const cs=getComputedStyle(el);
   if((cs.overflowX==='hidden'||cs.overflowX==='clip')&&el.scrollWidth-el.clientWidth>2&&el.clientWidth>60){
     if(cs.textOverflow==='ellipsis')continue;
     // check children: if the overflowing child truncates, skip
     let real=false;
     for(const ch of el.children){const ccs=getComputedStyle(ch);const cr=ch.getBoundingClientRect();const er=el.getBoundingClientRect();if(cr.right-(er.left+el.clientWidth)>2&&ccs.textOverflow!=='ellipsis')real=true;}
     if(!real&&el.children.length)continue;
     out.clip.push({sel:pth(el),delta:el.scrollWidth-el.clientWidth,clientW:el.clientWidth});
   }
 }
 // fixed/min-width offenders inside main that exceed available width
 const main=document.getElementById('of-main');
 if(main){ const avail=main.clientWidth;
  for(const el of main.querySelectorAll('*')){ const cs=getComputedStyle(el);
   const mw=parseFloat(cs.minWidth); const wd=cs.width;
   if(!isNaN(mw)&&mw>avail-40) out.fixedW.push({sel:pth(el),minW:cs.minWidth,avail});
  }}
 return out;
};
const res=[];
for(const route of ROUTES){ for(const w of WIDTHS){
  await page.setViewportSize({width:w,height:900});
  await page.goto(`http://localhost:${PORT}/#${route}`,{waitUntil:'load'});
  await page.waitForTimeout(400);
  res.push({route,w,...await page.evaluate(P)});
}}
for(const r of res){
  if(r.docOver>1||r.global.length||r.clip.length||r.fixedW.length){
    console.log(`\n### ${r.route} @${r.w}  docOver=${r.docOver}`);
    for(const g of r.global.slice(0,6)) console.log(`  OVER +${g.over} pos=${g.pos} w=${g.w} minW=${g.minW} :: ${g.sel}`);
    for(const c of r.clip.slice(0,6)) console.log(`  CLIP ${c.delta}px clientW=${c.clientW} :: ${c.sel}`);
    const uniq=[...new Map(r.fixedW.map(f=>[f.sel,f])).values()];
    for(const f of uniq.slice(0,6)) console.log(`  MINW ${f.minW} avail=${f.avail} :: ${f.sel}`);
  }
}
await b.close(); server.close();
