// The prototype's static server, as scripts/prototype-up.sh builds it (decodeURIComponent of the path,
// then serve-dist.mjs's serveStatic over dist/), on 127.0.0.1:PORT, for a traversal probe.
// Usage: node serve_dist_probe.mjs 8904
import { createServer } from 'node:http';
import { serveStatic } from '/home/user/openFermentUI/scripts/lib/serve-dist.mjs';
const port = Number(process.argv[2]);
createServer(async (req, res) => {
  let url;
  try { url = decodeURIComponent((req.url ?? '/').split('?')[0]); } catch { res.writeHead(400).end('bad request'); return; }
  await serveStatic('/home/user/openFermentUI/dist', url, res);
}).listen(port, '127.0.0.1');
