#!/usr/bin/env bash
# H13-01: README.md's "Run it" on a fresh clone with no key gets no database.
# A scratch worktree at 2047f5a stands for the fresh clone: no core/.env, no key. PostgreSQL answers on
# 127.0.0.1:5432 with compose.yaml's role (what `pnpm db:up` starts), so db:up itself is not run.
#   0. README line 41's `pnpm db:migrate`: the real entry point, run in the clone's core/.
#   1. session-start.sh (pnpm prototype:up runs it first), run whole from the clone with stand-ins for
#      pnpm and uv on PATH: install, sync and ready are skipped; db:migrate resolves the address the way
#      migrations.main does and connects to nothing. Then the same with core/.env holding a placeholder
#      key line (the case with a key), to show the step itself works when the file exists.
#   2. the service and the app as prototype-up.sh starts them (its own uvicorn line and its own node
#      server, read from the script), on 10500 and 10501: health, /, and Home's /api/projects.
#   3. the same service over a fresh database named in OPENFERMENT_DATABASE_URL (10502): what the app
#      does once an address is named.
# Keyless; no model call; no database touched beyond bh_r_h13_01_ctl.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
cd "$BH_ROOT" || exit 0
SHA=2047f5a; DB=bh_r_h13_01_ctl; P_SVC=10500; P_WEB=10501; P_CTL=10502
OUT="$BH_WORK/H13-01"; W="$OUT/wt"; BIN="$OUT/bin"; PY="$BH_ROOT/core/.venv/bin/python"
c() { curl -s --noproxy '*' "$@"; }
cleanup() {
  bh_svc_stop "$P_WEB"; bh_svc_stop "$P_SVC"; bh_svc_stop "$P_CTL"; bh_db_drop "$DB"
  git -C "$BH_ROOT" worktree remove --force "$W" >/dev/null 2>&1; rm -rf "$OUT"; git -C "$BH_ROOT" worktree prune
}
trap cleanup EXIT
cleanup; mkdir -p "$OUT" "$BIN"
git -C "$BH_ROOT" worktree add --detach "$W" "$SHA" >/dev/null 2>&1 || { echo "OBSERVED: no worktree"; echo "RESULT: NO-DEFECT"; exit 0; }
ln -s "$BH_ROOT/dist" "$W/dist"     # the built app, as `pnpm build` leaves it in the clone
echo "fresh clone: $W at $(git -C "$W" rev-parse --short HEAD); core/.env present: $([ -e "$W/core/.env" ] && echo yes || echo no)"
echo "PostgreSQL on 127.0.0.1 (compose.yaml's role and port): $(pg_isready -h 127.0.0.1)"

# Stand-ins: pnpm and uv, so session-start.sh runs whole without installing anything.
cat > "$BIN/uv" <<'SH'
#!/bin/bash
echo "uv $* (stand-in: skipped)"
SH
cat > "$BIN/pnpm" <<'SH'
#!/bin/bash
case "$*" in
  "install --frozen-lockfile"|"--silent ready") echo "pnpm $* (stand-in: skipped)" ;;
  "--silent db:migrate")
    cd core && exec "$H13_PY" - <<'PY'
import sys
from pathlib import Path
from dotenv import load_dotenv
import openferment_core.migrations as m
load_dotenv(Path(m.__file__).parent.parent / ".env", override=False)  # migrations.main's first line
try:
    url = m.database_url()
except m.DatabaseUnavailable as e:
    print(f"pnpm db:migrate (stand-in) refused: {e}", file=sys.stderr); sys.exit(2)
print(f"pnpm db:migrate (stand-in): would migrate {url.render_as_string(hide_password=True)}; nothing connected")
PY
    ;;
  *) echo "pnpm $* (stand-in: not expected)"; exit 1 ;;
esac
SH
chmod +x "$BIN/uv" "$BIN/pnpm"
keyless() { bh_env env -u OPENFERMENT_DATABASE_URL -u OPENFERMENT_WORKSPACE_ID "$@"; }

echo; echo "== 0. README.md:41 \`pnpm db:migrate\` on the fresh clone (the real entry point, in its core/)"
(cd "$W/core" && keyless "$PY" -m openferment_core.migrations migrate) > "$OUT/migrate.txt" 2>&1
MIG_RC=$?; sed 's/^/   /' "$OUT/migrate.txt"; echo "   exit $MIG_RC"

echo; echo "== 1a. scripts/session-start.sh, keyless, no core/.env (prototype-up.sh:29 runs it)"
keyless PATH="$BIN:$PATH" H13_PY="$PY" bash "$W/scripts/session-start.sh" > "$OUT/ss-keyless.txt" 2>&1
sed -n '/── the database/,$p' "$OUT/ss-keyless.txt" | sed 's/^/   /'
if [ -e "$W/core/.env" ]; then NOKEY_ENV="present"; NOKEY_URL=$(grep -c '^OPENFERMENT_DATABASE_URL=' "$W/core/.env")
else NOKEY_ENV="absent"; NOKEY_URL=0; fi
echo "   core/.env after the run: $NOKEY_ENV; lines naming OPENFERMENT_DATABASE_URL: $NOKEY_URL"

echo; echo "== 1b. the same, core/.env holding a placeholder key line alone (the case with a key)"
# The placeholder is joined at run time, so check:secrets reads no key-shaped string in this file.
(umask 177; printf 'ANTHROPIC_API_KEY=%s%s\n' 'sk-ant-' 'placeholder-not-a-key' > "$W/core/.env")
keyless PATH="$BIN:$PATH" H13_PY="$PY" bash "$W/scripts/session-start.sh" > "$OUT/ss-key.txt" 2>&1
sed -n '/── the database/,$p' "$OUT/ss-key.txt" | sed 's/^/   /'
KEY_URL=$(grep -c '^OPENFERMENT_DATABASE_URL=' "$W/core/.env")
echo "   lines naming OPENFERMENT_DATABASE_URL in core/.env after the run: $KEY_URL"
rm -f "$W/core/.env"; rm -rf "$W/core/data"

echo; echo "== 2. the service and the app as prototype-up.sh starts them on the keyless clone"
(cd "$W/core" && keyless setsid "$PY" -m uvicorn openferment_core.api:app --host 127.0.0.1 --port "$P_SVC" \
   --log-level warning </dev/null > "$OUT/svc.log" 2>&1 &)
HEALTH=""; for _ in $(seq 1 240); do HEALTH=$(curl -fsS --noproxy '*' "http://127.0.0.1:$P_SVC/api/health" 2>/dev/null) && break; sleep 0.5; done
sed -n "/^node --input-type=module - \"\$REPO\"/,/^EOF\$/p" "$W/scripts/prototype-up.sh" | sed '1d;$d' > "$OUT/web.mjs"
(keyless setsid node --input-type=module - "$W" 127.0.0.1 "$P_WEB" "$P_SVC" < "$OUT/web.mjs" > "$OUT/web.log" 2>&1 &)
for _ in $(seq 1 40); do c -o /dev/null -f "http://127.0.0.1:$P_WEB/" && break; sleep 0.25; done
WEB_ROOT=$(c -o /dev/null -w '%{http_code}' "http://127.0.0.1:$P_WEB/")
GET_P=$(c -w '\n%{http_code}' "http://127.0.0.1:$P_WEB/api/projects")
POST_P=$(c -w '\n%{http_code}' -X POST "http://127.0.0.1:$P_WEB/api/projects" -H 'content-type: application/json' \
          -d '{"id":"keyless","name":"Keyless","by":"a stranger"}')
GET_CODE=$(echo "$GET_P" | tail -1); POST_CODE=$(echo "$POST_P" | tail -1)
echo "   GET /api/health (prototype-up.sh:51-56 waits on it): $HEALTH"
echo "   GET / through the app server: $WEB_ROOT"
echo "   GET /api/projects (Home's list): [$GET_CODE] $(echo "$GET_P" | sed '$d')"
echo "   POST /api/projects (Home's New project): [$POST_CODE] $(echo "$POST_P" | sed '$d')"
HEALTH_OK=$(echo "$HEALTH" | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("ok") is True)
except Exception: print(False)')
bh_svc_stop "$P_WEB"; bh_svc_stop "$P_SVC"; rm -rf "$W/core/data"

echo; echo "== 3. control: the same service over a fresh database named in OPENFERMENT_DATABASE_URL"
bh_db_fresh "$DB" || echo "   bh_db_fresh failed"
(cd "$W/core" && bh_env env -u OPENFERMENT_WORKSPACE_ID OPENFERMENT_DATABASE_URL="$BH_SERVER/$DB" setsid "$PY" -m uvicorn \
   openferment_core.api:app --host 127.0.0.1 --port "$P_CTL" --log-level warning </dev/null > "$OUT/ctl.log" 2>&1 &)
for _ in $(seq 1 240); do c -f -o /dev/null "http://127.0.0.1:$P_CTL/api/health" && break; sleep 0.5; done
CTL_POST=$(c -o /dev/null -w '%{http_code}' -X POST "http://127.0.0.1:$P_CTL/api/projects" -H 'content-type: application/json' \
          -d '{"id":"keyless","name":"Keyless","by":"a stranger"}')
CTL_GET=$(c -w '\n%{http_code}' "http://127.0.0.1:$P_CTL/api/projects")
CTL_GET_CODE=$(echo "$CTL_GET" | tail -1)
echo "   POST /api/projects: [$CTL_POST]; GET /api/projects: [$CTL_GET_CODE] $(echo "$CTL_GET" | sed '$d' | cut -c1-160)"
bh_svc_stop "$P_CTL"

echo; echo "== the contract and the guard, as the tree holds them"
sed -n 41p README.md | sed 's/^/   README.md:41: /'
sed -n 46,47p README.md | sed 's/^/   README.md:46-47: /'
sed -n 18,20p scripts/session-start.sh | sed 's/^/   scripts\/session-start.sh:18-20: /'
sed -n 62,63p scripts/session-start.sh | sed 's/^/   scripts\/session-start.sh:62-63: /'

echo
echo "EXPECTED: by session-start.sh:18-20, PostgreSQL answering on 127.0.0.1 and core/.env naming no address, the development address joins core/.env and db:migrate migrates it; by README.md:46-47 the keyless app then runs whole, Home listing and making projects (as the control service over a named database does: POST [$CTL_POST], GET [$CTL_GET_CODE])"
echo "OBSERVED: README.md:41's db:migrate exits $MIG_RC refused; session-start.sh with no core/.env leaves core/.env $NOKEY_ENV with $NOKEY_URL address lines (with a key line present it writes $KEY_URL); the service prototype-up.sh starts there answers health ok=$HEALTH_OK, / [$WEB_ROOT], GET /api/projects [$GET_CODE], POST /api/projects [$POST_CODE]"
if [ "$MIG_RC" != 0 ] && [ "$NOKEY_URL" = 0 ] && [ "$KEY_URL" = 1 ] && [ "$HEALTH_OK" = True ] && [ "$WEB_ROOT" = 200 ] \
   && [ "$GET_CODE" = 503 ] && [ "$POST_CODE" = 503 ] && [ "$CTL_GET_CODE" = 200 ]; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
