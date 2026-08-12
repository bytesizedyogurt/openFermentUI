import { chromium } from 'playwright';
import { createServer } from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { join, extname } from 'node:path';
const DIST = join(process.cwd(), 'dist');
const OUT = '/tmp/claude-0/-home-user-openFermentUI/167fd0e3-b3d3-562c-b052-449a10776bea/scratchpad/shots';
const MIME = { '.html':'text/html','.js':'text/javascript','.css':'text/css','.woff2':'font/woff2' };
const server = createServer(async (req,res)=>{ try{
  const u=decodeURIComponent((req.url??'/').split('?')[0]);
  let f=join(DIST,u==='/'?'index.html':u);
  try{ if((await stat(f)).isDirectory()) f=join(f,'index.html'); }catch{ f=join(DIST,'index.html'); }
  res.writeHead(200,{'Content-Type':MIME[extname(f)]??'application/octet-stream'}); res.end(await readFile(f));
}catch{ res.writeHead(404).end('nf'); }});
await new Promise(r=>server.listen(4330,r));
const b = await chromium.launch({ executablePath:'/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });

const SHOTS = JSON.parse(process.argv[2]);
for (const { route, name, w, h, theme } of SHOTS) {
  const p = await b.newPage({ viewport:{ width:w, height:h }, colorScheme: theme==='dark'?'dark':'light' });
  await p.goto(`http://localhost:4330/#${route}`, { waitUntil:'networkidle' });
  await p.waitForTimeout(1100);
  await p.screenshot({ path:`${OUT}/${name}.png`, fullPage:false });
  await p.close();
  console.log('shot', name);
}
await b.close(); server.close();
