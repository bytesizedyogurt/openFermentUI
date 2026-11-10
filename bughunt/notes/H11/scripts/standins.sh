#!/bin/bash
# standins.sh DIR CHECKOUT: stand-ins for macOS and Homebrew, written into DIR, for running
# scripts/host/install.sh, deploy.sh and nightly.sh on Linux against a worktree CHECKOUT.
# Every stand-in appends one line to DIR/calls ("name args"), so a run's actions can be compared.
# Nothing here reaches PostgreSQL, launchd, the network or the repository's own checkout:
# psql, createdb, pg_isready and pg_dump are stand-ins; python under CHECKOUT/core/.venv runs
# scripts/host/launchd.py with the real interpreter and answers every -m openferment_core.* call.
# Usage: source the printed exports (eval "$(bash standins.sh DIR CHECKOUT)").
set -euo pipefail
D="$1"; CO="$2"
REAL_PY="${REAL_PY:-/home/user/openFermentUI/core/.venv/bin/python}"
mkdir -p "$D/bin" "$D/keg/bin" "$D/brewprefix/bin" "$D/state" "$D/daemons"
calls="$D/calls"
: > "$calls"

mk() { # mk PATH BODY
  printf '#!/bin/bash\nprintf "%%s\\n" "%s $*" >> "%s"\n%s\n' "$(basename "$1")" "$calls" "$2" > "$1"
  chmod 755 "$1"
}

mk "$D/bin/uname" 'if [ "${1:-}" = -s ]; then echo Darwin; else exec /usr/bin/uname "$@"; fi'
mk "$D/bin/id" 'case "${1:-}" in -u) echo 501 ;; -un) echo sean ;; *) exec /usr/bin/id "$@" ;; esac'
mk "$D/bin/brew" "case \"\$*\" in
  '--prefix --installed postgresql@17') echo \"$D/keg\" ;;
  '--prefix') echo \"$D/brewprefix\" ;;
  *) exit 0 ;;
esac"
# sudo: runs what it is given, as this user; install(1) without -o/-g (no root:wheel here).
mk "$D/bin/sudo" 'if [ "$1" = install ]; then shift; a=(); while [ $# -gt 0 ]; do case "$1" in -o|-g) shift 2 ;; *) a+=("$1"); shift ;; esac; done; exec install "${a[@]}"; fi
exec "$@"'
# launchctl: bootout fails for a job that is not loaded (as launchd answers 3), bootstrap loads it.
mk "$D/bin/launchctl" "st=\"$D/state\"
case \"\$1\" in
  bootout) l=\"\${2#system/}\"; [ -e \"\$st/\$l\" ] || exit 3; rm -f \"\$st/\$l\" ;;
  bootstrap) l=\"\$(basename \"\$3\" .plist)\"; [ -e \"\$st/\$l\" ] && exit 37; cp \"\$3\" \"\$st/\$l\" ;;
  kickstart) exit 0 ;;
esac"
mk "$D/bin/pmset" 'exit 0'
mk "$D/bin/fdesetup" 'exit 1'
mk "$D/bin/plutil" "[ \"\$1\" = -lint ] || exit 2; shift; for f in \"\$@\"; do \"$REAL_PY\" -I -c 'import plistlib,sys; plistlib.loads(open(sys.argv[1],\"rb\").read())' \"\$f\" && echo \"\$f: OK\" || exit 1; done"
mk "$D/bin/tailscale" 'case "$1" in status) exit 1 ;; serve) exit 0 ;; esac'
mk "$D/bin/pgrep" 'exit 1'
mk "$D/bin/curl" 'case "$*" in *"/api/health"*) echo "{\"ok\":true}" ;; *) exit 7 ;; esac'
mk "$D/bin/pnpm" 'exit 0'
mk "$D/bin/node" 'echo v22.0.0'
mk "$D/bin/uv" 'if [ "$1" = export ]; then echo "placeholder-pin==1.0"; fi; exit 0'
mk "$D/brewprefix/bin/brew" 'exit 0'
# The keg: PostgreSQL answering, pgvector there, no database named openferment until createdb.
mk "$D/keg/bin/pg_isready" 'exit 0'
mk "$D/keg/bin/psql" "case \"\$*\" in
  *pg_available_extensions*) echo 1 ;;
  *pg_database*) [ -e \"$D/state/db-openferment\" ] && echo 1 ;;
esac; exit 0"
mk "$D/keg/bin/createdb" "touch \"$D/state/db-openferment\""
mk "$D/keg/bin/pg_dump" 'for a in "$@"; do case "$a" in --file=*) out="${a#--file=}" ;; esac; done; printf "dump\n" > "$out"'
# The checkout's interpreter: launchd.py on the real Python; every module call answered.
mkdir -p "$CO/core/.venv/bin"
mk "$CO/core/.venv/bin/python" "case \"\$1\" in
  *launchd.py) exec \"$REAL_PY\" -I \"\$@\" ;;
  -m) exit 0 ;;
  *) exit 0 ;;
esac"
echo "export PATH=\"$D/bin:/usr/bin:/bin\" OPENFERMENT_LAUNCHD_DIR=\"$D/daemons\""
