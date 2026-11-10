#!/usr/bin/env bash
# H11-02: install.sh takes OPENFERMENT_HOST from the installing shell and writes it into the server's LaunchDaemon,
# so OPENFERMENT_HOST=0.0.0.0 installs a server on every interface, and guard.py admits a write whose Host names a
# LAN address. The candidate reads this as a break of CLAUDE.md:52 and the stop condition at CLAUDE.md:137.
# usage, from the repository root: bash bughunt/repro/H11-02/run.sh
#
# install.sh runs unchanged in a detached worktree of 2047f5a under $BH_WORK/H11-02/wt, on Linux, over stand-ins for
# macOS and Homebrew written into $BH_WORK/H11-02/out/standins (uname, id, brew, sudo, launchctl, pmset, fdesetup,
# plutil, tailscale, pgrep, curl, node, pnpm, uv, the keg's pg_isready, psql and createdb). The worktree's
# core/.venv/bin/python is a stand-in that runs scripts/host/launchd.py on the repository's interpreter and answers
# every `-m openferment_core.*` call with exit 0, so deploy.sh and pnpm ready do nothing real. Three installs:
#   A. a first install with OPENFERMENT_HOST unset (the runbook's path);
#   then install.sh --uninstall, so the next install finds no server job, as a first install does;
#   B. an install with OPENFERMENT_HOST=0.0.0.0 (the candidate's case);
#   C. a reinstall after B with OPENFERMENT_HOST unset (does a wide address linger?).
# Then the guard, end to end: the service on 127.0.0.1:9070 over a fresh test database bh_r_h11_02_svc takes a POST
# whose Host names a LAN address (no Origin, as curl or a script sends), and one whose Host names a public domain.
# Last, the tree's own record of the knob (lib.sh, test_host.py, PROGRESS.md, the alpha 1.0 guidance).
# Keyless: no key anywhere, no request leaves the machine (curl --noproxy '*', loopback alone).
source /home/user/openFermentUI/bughunt/lib/env.sh
DB=bh_r_h11_02_svc
PORT=9070
T=$BH_WORK/H11-02; WT=$T/wt; OUT=$T/out; SI=$OUT/standins
PY=$BH_ROOT/core/.venv/bin/python
PLIST=$SI/daemons/com.umutuzo.openferment.plist

cleanup() {
  bh_svc_stop "$PORT"
  bh_db_drop "$DB" 2>/dev/null
  rm -rf "$OUT" "$BH_WORK/data-$DB"
  git -C "$BH_ROOT" worktree remove --force "$WT" >/dev/null 2>&1
  git -C "$BH_ROOT" worktree prune >/dev/null 2>&1
  rmdir "$T" 2>/dev/null
}
trap cleanup EXIT
cleanup; mkdir -p "$OUT/home" "$SI/bin" "$SI/keg/bin" "$SI/brewprefix/bin" "$SI/state" "$SI/daemons"

echo "EXPECTED: the candidate's expectation: the installed server job listens on 127.0.0.1, or install.sh stops and asks"
echo "EXPECTED:   before it writes a wider address (CLAUDE.md:52 'The service binds 127.0.0.1'; CLAUDE.md:137, a stop"
echo "EXPECTED:   condition, 'the service keeps its loopback bind'; live-host-install.md:146 'binds 127.0.0.1 and nothing else')."
echo "EXPECTED: the tree's own rule for the knob: an install with OPENFERMENT_HOST unset writes --host 127.0.0.1, a reinstall"
echo "EXPECTED:   without it returns to loopback, and a wider address comes only from the person installing setting"
echo "EXPECTED:   OPENFERMENT_HOST that time (lib.sh:37-39; test_host.py:160-170; PROGRESS.md:3432-3435)."
echo "EXPECTED: the verdict is DEFECT when a wider address reaches the job with OPENFERMENT_HOST unset (A or C), or when the"
echo "EXPECTED:   knob is nowhere recorded as the install's explicit choice."

git -C "$BH_ROOT" worktree add --detach "$WT" 2047f5a >/dev/null 2>&1 || { echo "OBSERVED: could not add the worktree"; echo "RESULT: NO-DEFECT"; exit 0; }
bh_db_fresh "$DB" 2>/dev/null || { echo "OBSERVED: could not make $DB"; echo "RESULT: NO-DEFECT"; exit 0; }

# ── stand-ins for macOS and Homebrew ─────────────────────────────────────────────────────────────────────────────
mk() { printf '#!/bin/bash\nprintf "%%s\\n" "%s $*" >> "%s"\n%s\n' "$(basename "$1")" "$SI/calls" "$2" > "$1"; chmod 755 "$1"; }
mk "$SI/bin/uname" 'if [ "${1:-}" = -s ]; then echo Darwin; else exec /usr/bin/uname "$@"; fi'
mk "$SI/bin/id" 'case "${1:-}" in -u) echo 501 ;; -un) echo owner ;; *) exec /usr/bin/id "$@" ;; esac'
mk "$SI/bin/brew" "case \"\$*\" in '--prefix --installed postgresql@17') echo \"$SI/keg\" ;; '--prefix') echo \"$SI/brewprefix\" ;; *) exit 0 ;; esac"
mk "$SI/bin/sudo" 'if [ "$1" = install ]; then shift; a=(); while [ $# -gt 0 ]; do case "$1" in -o|-g) shift 2 ;; *) a+=("$1"); shift ;; esac; done; exec install "${a[@]}"; fi
exec "$@"'
mk "$SI/bin/launchctl" "st=\"$SI/state\"
case \"\$1\" in
  bootout) l=\"\${2#system/}\"; [ -e \"\$st/\$l\" ] || exit 3; rm -f \"\$st/\$l\" ;;
  bootstrap) l=\"\$(basename \"\$3\" .plist)\"; [ -e \"\$st/\$l\" ] && exit 37; cp \"\$3\" \"\$st/\$l\" ;;
  kickstart) exit 0 ;;
esac"
mk "$SI/bin/pmset" 'exit 0'
mk "$SI/bin/fdesetup" 'exit 1'
mk "$SI/bin/plutil" "[ \"\$1\" = -lint ] || exit 2; shift; for f in \"\$@\"; do \"$PY\" -I -c 'import plistlib,sys; plistlib.loads(open(sys.argv[1],\"rb\").read())' \"\$f\" && echo \"\$f: OK\" || exit 1; done"
mk "$SI/bin/tailscale" 'case "$1" in status) exit 1 ;; *) exit 0 ;; esac'
mk "$SI/bin/pgrep" 'exit 1'
mk "$SI/bin/curl" 'case "$*" in *"/api/health"*) echo "{\"ok\":true}" ;; *) exit 7 ;; esac'
mk "$SI/bin/pnpm" 'exit 0'
mk "$SI/bin/node" 'echo v22.0.0'
mk "$SI/bin/uv" 'if [ "$1" = export ]; then echo "placeholder-pin==1.0"; fi; exit 0'
mk "$SI/brewprefix/bin/brew" 'exit 0'
mk "$SI/keg/bin/pg_isready" 'exit 0'
mk "$SI/keg/bin/psql" "case \"\$*\" in
  *pg_available_extensions*) echo 1 ;;
  *pg_database*) [ -e \"$SI/state/db-openferment\" ] && echo 1 ;;
esac; exit 0"
mk "$SI/keg/bin/createdb" "touch \"$SI/state/db-openferment\""
mkdir -p "$WT/core/.venv/bin"
mk "$WT/core/.venv/bin/python" "case \"\$1\" in
  *launchd.py) exec \"$PY\" -I \"\$@\" ;;
  *) exit 0 ;;
esac"

# Runbook step 1's core/.env in the worktree (the example with its database line taken out); ensure_database names one.
(cd "$WT/core" && umask 077 && sed '/^OPENFERMENT_DATABASE_URL=/d' .env.example > .env)

# install CASE [HOST]: install.sh from the worktree, OPENFERMENT_HOST set only when HOST is given. Sets $exit and
# $bound (the host and port the installed server job's ProgramArguments hold).
install() {
  local label="$1" host="${2:-}" e=()
  [ -n "$host" ] && e=(OPENFERMENT_HOST="$host")
  (cd "$WT" && env -i HOME="$OUT/home" PATH="$SI/bin:/usr/bin:/bin" OPENFERMENT_LAUNCHD_DIR="$SI/daemons" "${e[@]}" \
     /bin/bash scripts/host/install.sh) > "$OUT/install-$label.out" 2>&1
  exit=$?
  bound=$("$PY" -I -c 'import plistlib,sys; a=plistlib.loads(open(sys.argv[1],"rb").read())["ProgramArguments"]; print(a[a.index("--host")+1], a[a.index("--port")+1])' "$PLIST" 2>/dev/null)
  echo "OBSERVED: [$label] OPENFERMENT_HOST=${host:-<unset>}; install.sh exit $exit; the server job's --host --port: ${bound:-<no plist>}"
  local said; said=$(grep -i 'listen\|0\.0\.0\.0\|loopback\|On this Mac' "$OUT/install-$label.out" | sed 's/^/  /' | paste -sd'|' -)
  echo "OBSERVED: [$label] what install.sh said about the address: ${said:-<nothing>}"
}

install "A first install"
A="$bound"
(cd "$WT" && env -i HOME="$OUT/home" PATH="$SI/bin:/usr/bin:/bin" OPENFERMENT_LAUNCHD_DIR="$SI/daemons" \
   /bin/bash scripts/host/install.sh --uninstall) > "$OUT/uninstall.out" 2>&1
echo "OBSERVED: install.sh --uninstall exit $?; server jobs left in the daemons folder: $(ls "$SI/daemons" | paste -sd' ' - | grep . || echo "<none>")"
install "B install, OPENFERMENT_HOST set" 0.0.0.0
B="$bound"
install "C reinstall after B" ""
C="$bound"

# ── the guard, end to end, on the real service over a fresh test database ──────────────────────────────────────
origin=$(bh_svc_start "$DB" "$PORT") || origin=""
post() { # post HOSTHEADER ID: POST /api/projects naming HOSTHEADER in Host, no Origin; prints status and body.
  curl -s --noproxy '*' -o "$OUT/post.json" -w '%{http_code}' -X POST "http://127.0.0.1:$PORT/api/projects" \
       -H "Host: $1" -H 'content-type: application/json' -d "{\"id\":\"$2\",\"name\":\"$2\",\"by\":\"bughunt\"}"
  printf ' %s' "$(head -c 160 "$OUT/post.json")"
}
if [ -n "$origin" ]; then
  lan=$(post 192.168.1.20:8000 bh-lan-write)
  bonjour=$(post mini.local:8000 bh-bonjour-write)
  public=$(post attacker.example.com:8000 bh-public-write)
else
  lan="no service"; bonjour="no service"; public="no service"
fi
echo "OBSERVED: guard on the service: POST /api/projects with Host 192.168.1.20:8000, no Origin -> $lan"
echo "OBSERVED: guard on the service: POST /api/projects with Host mini.local:8000, no Origin -> $bonjour"
echo "OBSERVED: guard on the service: POST /api/projects with Host attacker.example.com:8000, no Origin -> $public"
bh_svc_stop "$PORT"
echo "OBSERVED: guard.py's own rule for the hosts it answers to (guard.py:22-26): $(sed -n 22,26p "$WT/core/openferment_core/guard.py" | paste -sd' ' -)"

# ── the tree's own record of the knob ──────────────────────────────────────────────────────────────────────────
rec_lib=$(sed -n 37,39p "$WT/scripts/host/lib.sh" | paste -sd' ' -)
rec_test=$(grep -c 'parametrize(("asked", "expected"), \[(None, "127.0.0.1"), ("0.0.0.0", "0.0.0.0")\])' "$WT/core/tests/test_host.py")
rec_prog=$(sed -n 3432,3435p "$WT/docs/PROGRESS.md" | paste -sd' ' -)
rec_hist=$(sed -n 261,264p "$WT/docs/history/CLAUDE-2026-10-21.md" | paste -sd' ' -)
rec_runbook=$(grep -c 'OPENFERMENT_HOST' "$WT/docs/runbooks/live-host-install.md")
echo "OBSERVED: lib.sh:37-39: $rec_lib"
echo "OBSERVED: test_host.py:160 holds (None -> 127.0.0.1) and (0.0.0.0 -> 0.0.0.0): $rec_test match"
echo "OBSERVED: PROGRESS.md:3432-3435: $rec_prog"
echo "OBSERVED: docs/history/CLAUDE-2026-10-21.md:261-264 (alpha 1.0, no authority): $rec_hist"
echo "OBSERVED: lines of the live-host runbook naming OPENFERMENT_HOST: $rec_runbook"

recorded=0
grep -q "Left for the owner" <<<"$rec_prog" && grep -q "OPENFERMENT_HOST\` stays" <<<"$rec_prog" \
  && grep -q "choice made each time" <<<"$rec_lib" && [ "$rec_test" = 1 ] && recorded=1
echo "OBSERVED: summary: A=${A:-none} B=${B:-none} C=${C:-none}; knob recorded as the install's explicit choice: $recorded"

if [ "${A%% *}" != 127.0.0.1 ] || [ "${C%% *}" != 127.0.0.1 ] || [ "$recorded" != 1 ]; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
