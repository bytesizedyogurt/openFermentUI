/**
 * One static handler for every script that serves dist/ (OF-BLD-012.1 §6.9).
 *
 * Seven scripts — the smoke, the five browser checks and the offline demo —
 * each carried their own copy of the same eight lines, and every copy had
 * the same hole: `join(DIST, url)` collapses `..`, so `/../core/.env` read
 * the key off the disk of whoever was running `pnpm demo:offline`, and the
 * demo listened on every interface while it did. The path is resolved and
 * CONFINED to dist/ here, once; a request that leaves it is a 404 like any
 * other miss, and the servers bind to loopback unless told otherwise.
 */
import { readFile, stat } from 'node:fs/promises';
import { extname, resolve, sep } from 'node:path';

export const MIME = {
  '.html': 'text/html',
  '.js': 'text/javascript',
  '.css': 'text/css',
  '.svg': 'image/svg+xml',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.json': 'application/json',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
};

/** Where every script's server listens unless the operator says otherwise. */
export const LOOPBACK = '127.0.0.1';

/**
 * The file under `dist` that a request path names, or null when the path
 * points outside it. A path that names no file falls back to index.html —
 * the hash router owns the path from there — but only INSIDE dist.
 */
export async function resolveStatic(dist, url) {
  const root = resolve(dist);
  let file = resolve(root, '.' + (url === '/' ? '/index.html' : url));
  if (file !== root && !file.startsWith(root + sep)) return null;
  try {
    if ((await stat(file)).isDirectory()) file = resolve(file, 'index.html');
  } catch {
    file = resolve(root, 'index.html');
  }
  return file;
}

/** Answer one request for a static file. Returns after the response is sent. */
export async function serveStatic(dist, url, res) {
  const file = await resolveStatic(dist, url);
  if (!file) {
    res.writeHead(404).end('not found');
    return;
  }
  try {
    const body = await readFile(file);
    res.writeHead(200, { 'Content-Type': MIME[extname(file)] ?? 'application/octet-stream' });
    res.end(body);
  } catch {
    res.writeHead(404).end('not found');
  }
}
