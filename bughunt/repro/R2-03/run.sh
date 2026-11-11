#!/usr/bin/env bash
# R2-03: no test holds the MCP --service relay's "no proxy" rule. Flip the relay's httpx.Client to
# trust_env=True (mutation M16) and core/tests/test_mcp_service.py stays green where the suite runs (this
# container, NO_PROXY covering loopback; CI, no proxy at all), while the same mutant, run where HTTP_PROXY names
# a proxy and NO_PROXY is unset, sends every relayed call, its project and the client's name through that proxy.
# Run from the repository root: bash bughunt/repro/R2-03/run.sh
#
# Keyless (bh_env), no model call, nothing under core/ written: the main checkout's Python runs the tests of a
# scratch worktree of 2047f5a ($BH_WORK/R2-03/wt-*), PYTHONPATH naming the worktree's core so its
# openferment_core is the one imported (checked), PYTHONDONTWRITEBYTECODE and -p no:cacheprovider set. In the
# worktree alone: the served test's _free_port returns 10920 (the ports this repro may bind are 10920 to 10929),
# and the mutations M16 (trust_env=False to True) and M17 (follow_redirects=False to True, the control) are
# applied one at a time and restored. The suite's own fixture makes a fresh migrated database each pytest session
# on OPENFERMENT_TEST_DATABASE_URL=.../bh_r_r2_03_t (named bh_r_r2_03_t_<pid>_<hex>) and drops it; every
# bh_r_r2_03_* database left is dropped at the start and at the end. A stand-in proxy (a recorder that answers
# 502) listens on 127.0.0.1:10921. Steps:
#   0. the contract's words (commit 6f85338's message, mcp_server.py's Service docstring and its client line);
#   1. why the relay tests cannot see trust_env: they hand the client a stand-in transport (test line 63), and
#      httpx reads environment proxies only for a client given no transport (httpx/_client.py:685);
#   2. M16: the whole of tests/test_mcp_service.py in this container's environment, then the served test in a
#      CI-like environment (no proxy variable at all);
#   3. the control M17: the redirect test fails, so the suite does hold the rule written beside "no proxy";
#   4. what M16 changes: the served test (the real server over stdio, through a served app, its relay built
#      with no transport) with HTTP_PROXY and HTTPS_PROXY naming the recorder and NO_PROXY unset, the original
#      code and then M16, reading what the recorder received.
# Exits 0 either way.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
TAG="$(date +%s)-$$"
BASE="$BH_WORK/R2-03"
OUT="$BASE/out-$TAG"
WT="$BASE/wt-$TAG"
SVC_PORT=10920
PROXY_PORT=10921
REC_PID=""
SERVED=test_the_server_started_with_service_writes_through_it_and_the_audit_names_the_client
F=core/openferment_core/mcp_server.py
T=core/tests/test_mcp_service.py
ORIG='httpx.Client(base_url=origin, trust_env=False, follow_redirects=False,'
M16='httpx.Client(base_url=origin, trust_env=True, follow_redirects=False,'
M17='httpx.Client(base_url=origin, trust_env=False, follow_redirects=True,'

drop_ours() {
  local n
  for n in $(psql "$BH_SERVER/postgres" -AtqXc "SELECT datname FROM pg_database WHERE datname LIKE 'bh\_r\_r2\_03\_%'"); do
    bh_db_drop "$n"
  done
}
stop_recorder() { [ -n "$REC_PID" ] && kill "$REC_PID" 2>/dev/null; wait "$REC_PID" 2>/dev/null; REC_PID=""; }
cleanup() {
  stop_recorder
  [ -d "$WT" ] && git -C "$BH_ROOT" worktree remove --force "$WT" >/dev/null 2>&1
  git -C "$BH_ROOT" worktree prune >/dev/null 2>&1
  drop_ours; rm -rf "$OUT"
}
trap cleanup EXIT
mkdir -p "$OUT"
verdict() { echo "EXPECTED: $1"; echo "OBSERVED: $2"; echo "RESULT: $3"; exit 0; }

# pt [ENV...] -- PYTEST-ARGS: the worktree's tests, keyless, with extra environment settings before --.
pt() {
  local extra=()
  while [ "$#" -gt 0 ] && [ "$1" != "--" ]; do extra+=("$1"); shift; done
  shift
  (cd "$WT/core" && bh_env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$WT/core" OPENFERMENT_DATABASE_URL= \
     OPENFERMENT_TEST_DATABASE_URL="$BH_SERVER/bh_r_r2_03_t" BH_R2_03_PORT="$SVC_PORT" env "${extra[@]}" \
     timeout 900 "$BH_ROOT/core/.venv/bin/python" -m pytest "$@" -q -p no:randomly -p no:cacheprovider \
     -m "not live and not sim and not slow and not lit" < /dev/null)
}
# apply OLD NEW: replace the one occurrence of OLD in the worktree's mcp_server.py.
apply() {
  "$BH_ROOT/core/.venv/bin/python" -I - "$WT/$F" "$1" "$2" <<'PY'
import sys
path, old, new = sys.argv[1:4]
text = open(path, encoding="utf-8").read()
assert text.count(old) == 1, f"the text occurs {text.count(old)} times"
open(path, "w", encoding="utf-8").write(text.replace(old, new))
PY
}
restore() { git -C "$WT" checkout -q -- "$F"; }
summary() { grep -E '^[0-9]+ (passed|failed)|^(FAILED|ERROR) | passed| failed' "$1" | tail -3 | cut -c1-240; }

echo "== 0. the contract"
git -C "$BH_ROOT" show -s --format=%B 6f85338 | grep -n -F -- '`--service <origin>` (a loopback address alone, no proxy, no redirect)' | cut -c1-140
grep -n -F 'one project (--service). Through no proxy: the call is a loopback one,' "$BH_ROOT/$F"
grep -n -F "and a cloud container's HTTPS_PROXY names a proxy elsewhere. A redirect" "$BH_ROOT/$F"
grep -n -F "$ORIG" "$BH_ROOT/$F"

echo "== 1. what the relay tests hand the client, and what httpx reads then"
grep -n -F 'mcp_server.build(project, origin, transport=httpx.MockTransport(handle))' "$BH_ROOT/$T"
HX="$BH_ROOT/core/.venv/lib/python3.13/site-packages/httpx/_client.py"
grep -n -F 'allow_env_proxies = trust_env and transport is None' "$HX" | head -1 | sed "s#^#httpx/_client.py:#"
named=$(grep -c -i -E 'proxy' "$BH_ROOT/$T")
echo "lines of $T naming a proxy: $named"
[ "$named" = 0 ] || echo "(a test names a proxy: read it)"

echo "== the worktree"
git -C "$BH_ROOT" worktree add -q --detach "$WT" 2047f5a >/dev/null 2>&1 || verdict "a worktree of 2047f5a" "git worktree add failed" NO-DEFECT
git -C "$WT" log --oneline -1
"$BH_ROOT/core/.venv/bin/python" -I - "$WT/$T" <<'PY' || verdict "the served test's port moved into 10920-10929" "the port line was not found" NO-DEFECT
import sys
path = sys.argv[1]
text = open(path, encoding="utf-8").read()
old = '        s.bind(("127.0.0.1", 0))\n        return s.getsockname()[1]'
new = ('        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)\n'
       '        s.bind(("127.0.0.1", int(os.environ["BH_R2_03_PORT"])))\n        return s.getsockname()[1]')
assert text.count(old) == 1
open(path, "w", encoding="utf-8").write(text.replace(old, new))
PY
echo "the worktree's served test binds 127.0.0.1:$SVC_PORT (its _free_port alone changed)"
whose=$(cd "$WT/core" && PYTHONPATH="$WT/core" PYTHONDONTWRITEBYTECODE=1 "$BH_ROOT/core/.venv/bin/python" -c 'import openferment_core.mcp_server as m; print(m.__file__)')
echo "openferment_core imported from: $whose"
case "$whose" in "$WT"/*) ;; *) verdict "the worktree's openferment_core imported" "$whose imported" NO-DEFECT;; esac
drop_ours

echo "== 2a. M16 applied; the whole of tests/test_mcp_service.py in this container's environment"
env | grep -E '^(HTTP|HTTPS|ALL|NO)_PROXY=|^(http|https|all|no)_proxy=' | sed -E 's/=(.{40}).*/=\1.../' | sort
apply "$ORIG" "$M16" || verdict "M16 applied" "the relay's client line was not found" NO-DEFECT
grep -n -F "$M16" "$WT/$F" | cut -c1-120
pt -- tests/test_mcp_service.py > "$OUT/a.log" 2>&1; xa=$?
summary "$OUT/a.log"; echo "exit $xa"
served_a=0; grep -q -E 'passed' "$OUT/a.log" && ! grep -q -E "deselected|skipped" "$OUT/a.log" && served_a=1
echo "== 2b. M16; the served test in a CI-like environment (no proxy variable)"
pt -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u NO_PROXY -u http_proxy -u https_proxy -u all_proxy -u no_proxy \
   -- "tests/test_mcp_service.py::$SERVED" > "$OUT/b.log" 2>&1; xb=$?
summary "$OUT/b.log"; echo "exit $xb"
restore

echo "== 3. the control: M17 (follow_redirects=True); the redirect test"
apply "$ORIG" "$M17" || verdict "M17 applied" "the relay's client line was not found" NO-DEFECT
pt -- "tests/test_mcp_service.py::test_a_redirect_the_service_answers_is_followed_nowhere" > "$OUT/c.log" 2>&1; xc=$?
summary "$OUT/c.log"; echo "exit $xc"
restore

echo "== 4. what M16 changes: HTTP_PROXY and HTTPS_PROXY name a recorder on 127.0.0.1:$PROXY_PORT, NO_PROXY unset"
cat > "$OUT/recorder.py" <<'PY'
"""A proxy stand-in: it writes each request it receives (its line, two headers, the body's start) and answers 502."""
import http.server, json, socketserver, sys
port, log = int(sys.argv[1]), open(sys.argv[2], "a", encoding="utf-8")
class H(http.server.BaseHTTPRequestHandler):
    def _any(self):
        n = int(self.headers.get("content-length") or 0)
        body = self.rfile.read(n) if n else b""
        log.write(json.dumps({"line": self.requestline,
                              "project": self.headers.get("x-openferment-project"),
                              "assistant": self.headers.get("x-openferment-assistant"),
                              "body": body.decode("utf-8", "replace")[:160]}) + "\n"); log.flush()
        said = b"a proxy stand-in"
        self.send_response(502); self.send_header("content-length", str(len(said)))
        self.send_header("connection", "close"); self.end_headers(); self.wfile.write(said)
    do_GET = do_POST = do_PUT = do_DELETE = do_CONNECT = _any
    def log_message(self, *args): pass
class S(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True
with S(("127.0.0.1", port), H) as s:
    s.serve_forever()
PY
: > "$OUT/proxy-orig.jsonl"; : > "$OUT/proxy-m16.jsonl"
PROXIED=(-u NO_PROXY -u no_proxy -u ALL_PROXY -u all_proxy HTTP_PROXY="http://127.0.0.1:$PROXY_PORT"
         HTTPS_PROXY="http://127.0.0.1:$PROXY_PORT" http_proxy="http://127.0.0.1:$PROXY_PORT"
         https_proxy="http://127.0.0.1:$PROXY_PORT")
start_recorder() {
  /usr/bin/python3 -I "$OUT/recorder.py" "$PROXY_PORT" "$1" > "$OUT/recorder.err" 2>&1 &
  REC_PID=$!
  local i; for i in $(seq 1 40); do
    (exec 3<>"/dev/tcp/127.0.0.1/$PROXY_PORT") 2>/dev/null && return 0; sleep 0.25; done
  return 1
}
echo "-- 4a. the code as it stands (trust_env=False)"
start_recorder "$OUT/proxy-orig.jsonl" || verdict "the recorder listening on $PROXY_PORT" "it did not start" NO-DEFECT
: > "$OUT/proxy-orig.jsonl"   # the readiness probe is no request
pt "${PROXIED[@]}" -- "tests/test_mcp_service.py::$SERVED" > "$OUT/d.log" 2>&1; xd=$?
stop_recorder
summary "$OUT/d.log"; echo "exit $xd; requests the recorder received: $(wc -l < "$OUT/proxy-orig.jsonl")"
echo "-- 4b. M16 (trust_env=True)"
apply "$ORIG" "$M16"
start_recorder "$OUT/proxy-m16.jsonl" || verdict "the recorder listening on $PROXY_PORT" "it did not start" NO-DEFECT
: > "$OUT/proxy-m16.jsonl"
pt "${PROXIED[@]}" -- "tests/test_mcp_service.py::$SERVED" > "$OUT/e.log" 2>&1; xe=$?
stop_recorder
restore
summary "$OUT/e.log"; echo "exit $xe; requests the recorder received: $(wc -l < "$OUT/proxy-m16.jsonl")"
cut -c1-300 "$OUT/proxy-m16.jsonl"
grep -o -E "AssertionError: .{0,200}" "$OUT/e.log" | head -1
drop_ours

# ── the verdict ──
a_pass=0; [ "$xa" = 0 ] && a_pass=1
b_pass=0; [ "$xb" = 0 ] && grep -q '1 passed' "$OUT/b.log" && b_pass=1
c_caught=0; [ "$xc" != 0 ] && grep -q -E '1 failed' "$OUT/c.log" && c_caught=1
d_pass=0; [ "$xd" = 0 ] && grep -q '1 passed' "$OUT/d.log" && [ "$(wc -l < "$OUT/proxy-orig.jsonl")" = 0 ] && d_pass=1
e_leak=0; [ "$xe" != 0 ] && grep -q '"line": "POST http://127.0.0.1:'"$SVC_PORT"'/api/tools/catalogue_write' "$OUT/proxy-m16.jsonl" \
  && grep -q '"project": "test-project", "assistant": "example-test/0.1"' "$OUT/proxy-m16.jsonl" && e_leak=1
echo "== the reading"
echo "M16, whole file in this container: green=$a_pass (served test run: $served_a); M16, served test with no proxy" \
     "variable: green=$b_pass; control M17 caught by the redirect test: $c_caught; under HTTP_PROXY with NO_PROXY unset," \
     "the code as it stands passes with nothing sent to the proxy: $d_pass; M16 sends the relayed call, its project and" \
     "the client's name to the proxy and the served test fails: $e_leak"
EXP="a test of tests/test_mcp_service.py fails when the --service relay reads the environment's proxy settings (commit 6f85338: 'a loopback address alone, no proxy, no redirect'; mcp_server.py:232 'Through no proxy: the call is a loopback one'), as the redirect test fails for follow_redirects=True"
OBS="M16 (trust_env=True at mcp_server.py:239): test_mcp_service.py $(summary "$OUT/a.log" | tail -1) in this container, the served test $(summary "$OUT/b.log" | tail -1) with no proxy set; M17: $(summary "$OUT/c.log" | tail -1); under HTTP_PROXY=127.0.0.1:$PROXY_PORT with NO_PROXY unset the mutant sent $(wc -l < "$OUT/proxy-m16.jsonl") relayed requests (project test-project, assistant example-test/0.1) to the proxy, where the code as it stands sent $(wc -l < "$OUT/proxy-orig.jsonl")"
if [ "$a_pass$b_pass$e_leak" = 111 ]; then
  verdict "$EXP" "$OBS: the suite stays green for a relay that goes through the environment's proxy" DEFECT
fi
verdict "$EXP" "$OBS: flags whole=$a_pass ci=$b_pass control=$c_caught original=$d_pass leak=$e_leak" NO-DEFECT
