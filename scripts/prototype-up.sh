#!/bin/bash
# The running prototype, from a fresh clone, in one command (OF-BLD-014 §1.4).
#
#   bash scripts/prototype-up.sh        pnpm prototype:up
#
# Runs session-start.sh (dependencies, core/.env, pnpm ready), builds the app,
# starts openferment-core on 127.0.0.1:8000 over the real data directories,
# and serves the build on 127.0.0.1:4173 with /api passed through to the
# service. Then it prints the address. Ctrl-C stops both.
#
# This is the live app. The service keeps every record in the PostgreSQL
# database core/.env names (session-start.sh migrates it): what this machine
# collected, extracted and decided. With a key in core/.env, extraction and
# Postdoc spend money under the day's cap.
# Both servers listen on loopback alone.
set -uo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO" || exit 1
parent=$PPID
HOST=127.0.0.1
API_PORT=8000
PORT=4173

say() { printf '\n── %s\n' "$*"; }
die() { printf '\n✗ %s\n' "$*" >&2; exit 1; }
# Free when nothing accepts a connection on it.
port_free() { ! (exec 3<>"/dev/tcp/$HOST/$1") 2>/dev/null; }

bash scripts/session-start.sh || die "scripts/session-start.sh failed"

say "pnpm build"
pnpm build || die "pnpm build failed"

for port in "$API_PORT" "$PORT"; do
  port_free "$port" || die "port $port is in use. An earlier pnpm prototype:up may still run; stop it first"
done

svc="" web=""
stop() {
  [ -z "$web" ] || kill "$web" 2>/dev/null
  [ -z "$svc" ] || kill "$svc" 2>/dev/null
  wait 2>/dev/null
}
trap stop EXIT
trap 'exit 130' INT TERM

say "the service on $HOST:$API_PORT"
(cd core && exec uv run uvicorn openferment_core.api:app --host "$HOST" --port "$API_PORT" --log-level warning) &
svc=$!
health=""
for _ in $(seq 1 240); do
  health="$(curl -fsS "http://$HOST:$API_PORT/api/health" 2>/dev/null)" && break
  kill -0 "$svc" 2>/dev/null || die "the service exited before it answered /api/health"
  sleep 0.5
done
[ -n "$health" ] || die "the service did not answer /api/health within 120 s"

say "the app on $HOST:$PORT"
node --input-type=module - "$REPO" "$HOST" "$PORT" "$API_PORT" <<'EOF' &
import { createServer, request } from 'node:http';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';

const [root, host, port, apiPort] = process.argv.slice(2);
const { serveStatic } = await import(pathToFileURL(join(root, 'scripts', 'lib', 'serve-dist.mjs')).href);
const dist = join(root, 'dist');

const web = createServer(async (req, res) => {
  let url;
  try {
    url = decodeURIComponent((req.url ?? '/').split('?')[0]);
  } catch {
    res.writeHead(400).end('bad request');
    return;
  }
  if (url.startsWith('/api/')) {
    // The browser's own headers go through, Host and Origin included, so the
    // service's guard sees the address the page is on.
    const upstream = request(
      { host: '127.0.0.1', port: Number(apiPort), path: req.url, method: req.method, headers: req.headers },
      (up) => {
        res.writeHead(up.statusCode ?? 502, up.headers);
        up.pipe(res);
      },
    );
    const fail = (detail) => {
      if (!res.headersSent) res.writeHead(502, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ detail }));
    };
    // A real extraction or a Postdoc answer can take minutes; this is idle time.
    upstream.setTimeout(600_000, () => {
      upstream.destroy();
      fail('the service went quiet for 10 minutes');
    });
    upstream.on('error', () => fail('the service is not answering'));
    req.pipe(upstream);
    return;
  }
  await serveStatic(dist, url, res);
});
web.on('error', (e) => {
  console.error(`✗ the web server could not listen on ${host}:${port}: ${e.code ?? e.message}`);
  process.exit(1);
});
web.listen(Number(port), host);
EOF
web=$!
for _ in $(seq 1 20); do
  curl -fsS "http://$HOST:$PORT/" >/dev/null 2>&1 && break
  kill -0 "$web" 2>/dev/null || die "the web server did not start"
  sleep 0.25
done

node -e '
  const h = JSON.parse(process.argv[1]);
  console.log("\nopenFerment — the prototype");
  console.log("───────────────────────────");
  console.log(`  service   http://${process.argv[2]}:${process.argv[3]}  core/data/, ${h.records} records, key: ${h.hasKey ? "present" : "none (Extract and Live mode wait for core/.env)"}`);
  console.log(`  open      http://${process.argv[2]}:${process.argv[4]}/`);
  console.log("\n  Ctrl-C stops the service and the server.\n");
' "$health" "$HOST" "$API_PORT" "$PORT"

# bash 3.2 has no `wait -n`: watch both, and stop the pair when either ends,
# or when whatever started this script is gone (pnpm's shell, a terminal).
while kill -0 "$svc" 2>/dev/null && kill -0 "$web" 2>/dev/null; do
  kill -0 "$parent" 2>/dev/null || die "the command that started the prototype is gone; stopping both servers"
  sleep 1
done
die "the service or the web server stopped; the prototype is down"
