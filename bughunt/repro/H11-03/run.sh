#!/usr/bin/env bash
# H11-03: install.sh run from a shell that exports OPENFERMENT_DATABASE_URL, over the core/.env of the live-host
# runbook's step 1 (core/.env.example with its database line taken out), writes no database line into core/.env;
# the server's LaunchDaemon starts the service with PATH, HOME and PYTHONUNBUFFERED alone, so the installed service
# reaches no database, while install.sh's own health wait and pnpm ready's data and service rows all pass.
# usage, from the repository root: bash bughunt/repro/H11-03/run.sh
#
# install.sh runs unchanged in a detached worktree of 2047f5a under $BH_WORK/H11-03/wt, on Linux, over stand-ins for
# macOS and Homebrew (uname, id, brew, sudo, pmset, fdesetup, plutil, tailscale, pgrep, launchctl, the keg's psql,
# pg_isready and createdb, node, pnpm, uv) written into $BH_WORK/H11-03/out/standins. The stand-in launchctl does
# what launchd does with the server job: it reads the plist install.sh installed and starts ProgramArguments in
# WorkingDirectory with EnvironmentVariables as the whole environment (plus ANTHROPIC_BASE_URL on a closed loopback
# port, a keyless guard). The worktree's core/.venv/bin/python is a stand-in that runs launchd.py and `-m uvicorn`
# on the repository's interpreter (the worktree's code first on sys.path, so the service reads the worktree's
# core/.env) and answers deploy.sh's other module calls. The repository's own core/ is never read for .env and
# never written. Port 9370 (service), 9379 (closed). Database bh_r_h11_03_live, made fresh, is the address the
# shell exports.
source /home/user/openFermentUI/bughunt/lib/env.sh
DB=bh_r_h11_03_live
PORT=9370
T=$BH_WORK/H11-03; WT=$T/wt; OUT=$T/out; SI=$OUT/standins
PY=$BH_ROOT/core/.venv/bin/python
# The address the shell exports, shaped as the live one (a role, no password, the database): this test server asks
# the role openferment for a password, given by PGPASSWORD, as a Mac's PostgreSQL lets its owner in by trust.
URL="postgresql://openferment@127.0.0.1:5432/$DB"

cleanup() {
  if [ -f "$SI/state/server.pgid" ]; then kill -TERM -- "-$(cat "$SI/state/server.pgid")" 2>/dev/null; sleep 1
    kill -KILL -- "-$(cat "$SI/state/server.pgid")" 2>/dev/null; fi
  bh_svc_stop "$PORT"
  bh_db_drop "$DB" 2>/dev/null
  rm -rf "$OUT"
  git -C "$BH_ROOT" worktree remove --force "$WT" >/dev/null 2>&1
  rmdir "$T" 2>/dev/null
}
trap cleanup EXIT
cleanup; mkdir -p "$OUT/home" "$SI/bin" "$SI/keg/bin" "$SI/brewprefix/bin" "$SI/state" "$SI/daemons"

echo "EXPECTED: with no database line in core/.env, install.sh names a database there (the live address, or the value the"
echo "EXPECTED:   shell exports), as ensure_database's comment says (scripts/host/lib.sh:122-124 'its address in core/.env."
echo "EXPECTED:   Makes what is missing') and the runbook says (live-host-install.md:137-139 'when no database is named in"
echo "EXPECTED:   core/.env, ... makes the database openferment and names it there'), so the service the LaunchDaemon"
echo "EXPECTED:   starts reads its database from core/.env and GET /api/projects answers 200."

git -C "$BH_ROOT" worktree add --detach "$WT" 2047f5a >/dev/null 2>&1 || { echo "OBSERVED: could not add the worktree"; echo "RESULT: NO-DEFECT"; exit 0; }
bh_db_fresh "$DB" 2>/dev/null || { echo "OBSERVED: could not make $DB"; echo "RESULT: NO-DEFECT"; exit 0; }

# ── stand-ins for macOS and Homebrew ─────────────────────────────────────────────────────────────────────────────
mk() { printf '#!/bin/bash\nprintf "%%s\\n" "%s $*" >> "%s"\n%s\n' "$(basename "$1")" "$SI/calls" "$2" > "$1"; chmod 755 "$1"; }
mk "$SI/bin/uname" 'if [ "${1:-}" = -s ]; then echo Darwin; else exec /usr/bin/uname "$@"; fi'
mk "$SI/bin/id" 'case "${1:-}" in -u) echo 501 ;; -un) echo owner ;; *) exec /usr/bin/id "$@" ;; esac'
mk "$SI/bin/brew" "case \"\$*\" in '--prefix --installed postgresql@17') echo \"$SI/keg\" ;; '--prefix') echo \"$SI/brewprefix\" ;; *) exit 0 ;; esac"
mk "$SI/bin/sudo" 'if [ "$1" = install ]; then shift; a=(); while [ $# -gt 0 ]; do case "$1" in -o|-g) shift 2 ;; *) a+=("$1"); shift ;; esac; done; exec install "${a[@]}"; fi
exec "$@"'
mk "$SI/bin/pmset" 'exit 0'
mk "$SI/bin/fdesetup" 'exit 1'
mk "$SI/bin/plutil" "[ \"\$1\" = -lint ] || exit 2; shift; for f in \"\$@\"; do \"$PY\" -I -c 'import plistlib,sys; plistlib.loads(open(sys.argv[1],\"rb\").read())' \"\$f\" && echo \"\$f: OK\" || exit 1; done"
mk "$SI/bin/tailscale" 'case "$1" in status) exit 1 ;; *) exit 0 ;; esac'
mk "$SI/bin/pgrep" 'exit 1'
mk "$SI/bin/curl" "exec /usr/bin/curl --noproxy '*' \"\$@\""
mk "$SI/bin/pnpm" 'exit 0'
mk "$SI/bin/node" 'echo v22.0.0'
mk "$SI/bin/uv" 'if [ "$1" = export ]; then echo "placeholder-pin==1.0"; fi; exit 0'
mk "$SI/brewprefix/bin/brew" 'exit 0'
mk "$SI/keg/bin/pg_isready" 'exit 0'
mk "$SI/keg/bin/psql" "case \"\$*\" in *pg_available_extensions*) echo 1 ;; *pg_database*) [ -e \"$SI/state/db-openferment\" ] && echo 1 ;; esac; exit 0"
mk "$SI/keg/bin/createdb" "touch \"$SI/state/db-openferment\""
# launchctl: bootstrap starts the server job as launchd would (the plist's environment alone, its working directory,
# its log), bootout stops it; the nightly job is only recorded.
cat > "$SI/launch.py" <<'PYEOF'
import os, plistlib, subprocess, sys
p = plistlib.loads(open(sys.argv[1], "rb").read())
env = dict(p["EnvironmentVariables"]); env["ANTHROPIC_BASE_URL"] = "http://127.0.0.1:9379"  # keyless guard
os.makedirs(os.path.dirname(p["StandardOutPath"]), exist_ok=True)
log = open(p["StandardOutPath"], "ab")
proc = subprocess.Popen(p["ProgramArguments"], cwd=p["WorkingDirectory"], env=env, stdin=subprocess.DEVNULL,
                        stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
print(proc.pid)
PYEOF
mk "$SI/bin/launchctl" "st=\"$SI/state\"
case \"\$1\" in
  bootout) l=\"\${2#system/}\"; [ -e \"\$st/\$l\" ] || exit 3; rm -f \"\$st/\$l\"
    if [ -f \"\$st/server.pgid\" ] && [ \"\$l\" = com.umutuzo.openferment ]; then kill -TERM -- \"-\$(cat \"\$st/server.pgid\")\" 2>/dev/null; rm -f \"\$st/server.pgid\"; fi ;;
  bootstrap) l=\"\$(basename \"\$3\" .plist)\"; [ -e \"\$st/\$l\" ] && exit 37; cp \"\$3\" \"\$st/\$l\"
    if [ \"\$l\" = com.umutuzo.openferment ]; then \"$PY\" -I \"$SI/launch.py\" \"\$3\" > \"\$st/server.pgid\"; fi ;;
  kickstart) exit 0 ;;
esac"
# The worktree's interpreter: launchd.py and the service on the repository's Python; deploy.sh's other module calls
# (geneos fetch, migrations, ready) answered with 0.
mkdir -p "$WT/core/.venv/bin"
mk "$WT/core/.venv/bin/python" "case \"\$1 \${2:-}\" in
  *launchd.py*) exec \"$PY\" -I \"\$@\" ;;
  '-m uvicorn') exec \"$PY\" \"\$@\" ;;
  *) exit 0 ;;
esac"
where=$(cd "$WT/core" && env -i PATH=/usr/bin:/bin "$PY" -c 'import importlib.util as u; print(u.find_spec("openferment_core").origin)')
case "$where" in "$WT"/*) echo "setup: the service's code is the worktree's: $where" ;;
  *) echo "OBSERVED: the service would import $where, outside the worktree; stopping"; echo "RESULT: NO-DEFECT"; exit 0 ;; esac

step1() { rm -f "$WT/core/.env"; (cd "$WT/core" && umask 077 && sed '/^OPENFERMENT_DATABASE_URL=/d' .env.example > .env); }
dotenv_db() { "$PY" -I -c 'import sys; from dotenv import dotenv_values; print(dotenv_values(sys.argv[1]).get("OPENFERMENT_DATABASE_URL"))' "$WT/core/.env"; }
# The install shell: stand-ins first on the path, the test launchd folder, the stand-in home, port 9370, no proxy.
shell_env() {
  bh_env env -u OPENFERMENT_HOST -u OPENFERMENT_DATABASE_URL -u https_proxy -u http_proxy -u HTTPS_PROXY -u HTTP_PROXY \
    PATH="$SI/bin:/usr/bin:/bin" HOME="$OUT/home" PGPASSWORD=openferment \
    OPENFERMENT_LAUNCHD_DIR="$SI/daemons" OPENFERMENT_PORT="$PORT" "$@"
}

# ── control: the same file, the shell exporting nothing ──────────────────────────────────────────────────────────
step1
ctl=$(cd "$WT" && shell_env bash -c 'set -euo pipefail; source scripts/host/lib.sh; ensure_database' 2>&1 | tail -1)
echo "OBSERVED: [control: shell exports no database] ensure_database said: $ctl"
echo "OBSERVED: [control] core/.env's database afterwards, as python-dotenv reads it: $(dotenv_db)"

# ── the case: install.sh from a shell exporting the live database's address ──────────────────────────────────────
step1; rm -f "$SI/state/db-openferment"
echo "setup: step 1's core/.env holds a database line: $(grep -c '^OPENFERMENT_DATABASE_URL' "$WT/core/.env")"
(cd "$WT" && shell_env OPENFERMENT_DATABASE_URL="$URL" /bin/bash scripts/host/install.sh) > "$OUT/install.out" 2>&1
st=$?
said=$(grep -m1 'OPENFERMENT_DATABASE_URL\|Database openferment' "$OUT/install.out")
health_said=$(grep -m1 '"ok"' "$OUT/install.out" | cut -c1-90)
envfile=$(dotenv_db)
jobenv=$("$PY" -I -c 'import plistlib,sys; print(",".join(sorted(plistlib.loads(open(sys.argv[1],"rb").read())["EnvironmentVariables"])))' "$SI/daemons/com.umutuzo.openferment.plist" 2>/dev/null)
echo "OBSERVED: the shell exports OPENFERMENT_DATABASE_URL=$URL; install.sh exit $st"
echo "OBSERVED: install.sh said about the database: $said"
echo "OBSERVED: install.sh's wait_for_health printed: $health_said"
echo "OBSERVED: core/.env's database after install.sh, as python-dotenv reads it (the service's load_dotenv): $envfile"
echo "OBSERVED: the installed server job's EnvironmentVariables: $jobenv"

# pnpm ready's two rows that bear on this, from the install shell as run_ready runs it (lib.sh:77-80).
rows=$(cd "$WT/core" && shell_env OPENFERMENT_DATABASE_URL="$URL" OPENFERMENT_POLL_HOST=127.0.0.1 "$PY" -c '
from dotenv import load_dotenv
from openferment_core import ready
load_dotenv(ready.CORE / ".env", override=False)
for c in (ready.check_data(), ready.check_service(9370, False, "127.0.0.1")):
    print(f"{c.mark} {c.name}: {c.detail}")' 2>&1 | tr '\n' ';')
echo "OBSERVED: pnpm ready's rows from the install shell: $rows"

# The service the job started, asked as a person's browser asks it.
h=$(curl -s --noproxy '*' -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/api/health")
p=$(curl -s --noproxy '*' -o "$OUT/projects.json" -w '%{http_code}' "http://127.0.0.1:$PORT/api/projects")
echo "OBSERVED: the job's service: GET /api/health -> $h; GET /api/projects -> $p $(cut -c1-230 "$OUT/projects.json")"

# ── also: the example's development address exported, the same file ─────────────────────────────────────────────
step1
dev=$(cd "$WT" && shell_env OPENFERMENT_DATABASE_URL=postgresql://openferment:openferment@127.0.0.1:5432/openferment_dev \
  bash -c 'set -euo pipefail; source scripts/host/lib.sh; ensure_database' 2>&1 | grep -o 'Delete that line from core/.env[^:]*')
echo "OBSERVED: [also: the example's address exported] ensure_database's refusal says '$dev'; core/.env's database lines: $(grep -c '^OPENFERMENT_DATABASE_URL' "$WT/core/.env")"

if [ "$st" = 0 ] && [ "$envfile" = None ] && [ "$p" = 503 ] && grep -q 'not set' "$OUT/projects.json" &&
   ! grep -q OPENFERMENT_DATABASE_URL <<<"$jobenv" && grep -q '^ok data' <<<"${rows//;/$'\n'}"; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
