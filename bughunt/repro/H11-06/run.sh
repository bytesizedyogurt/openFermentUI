#!/usr/bin/env bash
# H11-06: scripts/session-start.sh looks for core/.env's database with `grep -q '^OPENFERMENT_DATABASE_URL='`,
# so a core/.env naming its database as `export OPENFERMENT_DATABASE_URL=...` or `OPENFERMENT_DATABASE_URL = ...`
# (forms python-dotenv reads, and scripts/host/lib.sh's env_setting reads) gains the development address on a
# later line, and the service's own reading of core/.env then names openferment_dev.
#
# A scratch worktree at 2047f5a runs its own scripts/session-start.sh, with the real pg_isready (PostgreSQL
# answers on 127.0.0.1) and stand-ins for pnpm and uv that record their arguments and do nothing, so no
# install, sync or migration runs and nothing reaches openferment_dev. Each case writes the worktree's core/.env
# naming a fresh test database, reads it as the service does (load_dotenv(core/.env, override=False), then
# db.engine.database_url(), the worktree's own code), connects to it, runs session-start, and reads it again.
#   case 0 (control): OPENFERMENT_DATABASE_URL=<url>
#   case A:           export OPENFERMENT_DATABASE_URL=<url>
#   case B:           OPENFERMENT_DATABASE_URL = <url>
# The database is made fresh here and dropped after; the worktree is removed after.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
cd "$BH_ROOT" || exit 0
SHA=2047f5a; DB=bh_r_h11_06_named; URL="$BH_SERVER/$DB"
OUT="$BH_WORK/H11-06"; W="$OUT/wt"; PY="$BH_ROOT/core/.venv/bin/python"
cleanup() {
  bh_db_drop "$DB" 2>/dev/null
  git -C "$BH_ROOT" worktree remove --force "$W" >/dev/null 2>&1; git -C "$BH_ROOT" worktree prune
  rm -rf "$OUT"
}
trap cleanup EXIT
cleanup; mkdir -p "$OUT/bin" "$OUT/home"
git -C "$BH_ROOT" worktree add --detach "$W" "$SHA" >/dev/null 2>&1 ||
  { echo "OBSERVED: no worktree"; echo "RESULT: NO-DEFECT"; exit 0; }
echo "worktree: $W at $(git -C "$W" rev-parse --short HEAD)"

echo; echo "== 1. the contract and the code, as $SHA holds them"
show() { sed -n "$2p" "$W/$1" | sed "s|^|   $1:$2: |"; }
for n in 18 19 20; do show scripts/session-start.sh $n; done
show scripts/session-start.sh 62; show scripts/session-start.sh 63
for n in 97 98 99 100; do show scripts/host/lib.sh $n; done
show scripts/host/lib.sh 110
show core/tests/test_host.py 195; show core/tests/test_host.py 196
show core/openferment_core/api.py 178

echo; echo "== 2. a fresh test database for core/.env to name"
bh_db_fresh "$DB" 2>/dev/null || { echo "OBSERVED: no test database"; echo "RESULT: NO-DEFECT"; exit 0; }
echo "   $DB made and migrated; pg_isready -h 127.0.0.1: $(pg_isready -h 127.0.0.1)"

# Stand-ins: pnpm and uv record their arguments and succeed; everything else is the machine's own.
for t in pnpm uv; do
  printf '#!/bin/bash\nprintf "%%s\\n" "%s $*" >> "%s/calls"\nexit 0\n' "$t" "$OUT" > "$OUT/bin/$t"; chmod 755 "$OUT/bin/$t"
done

# The service's reading of the worktree's core/.env: api.py:178 and migrations.py:113 load it with
# load_dotenv(override=False), then db.engine.database_url() reads OPENFERMENT_DATABASE_URL.
service_db() {
  env -u OPENFERMENT_DATABASE_URL "$PY" -I -c '
import sys; sys.path.insert(0, sys.argv[1] + "/core")
from pathlib import Path
from dotenv import load_dotenv
import importlib; e = importlib.import_module("openferment_core.db.engine")
assert e.__file__.startswith(sys.argv[1]), e.__file__
load_dotenv(Path(e.__file__).parents[2] / ".env", override=False)
print(e.database_url().database)' "$W" 2>&1 | tail -1
}
lib_db() {
  env -u OPENFERMENT_DATABASE_URL HOME="$OUT/home" bash -c 'source "$1/scripts/host/lib.sh"; env_setting OPENFERMENT_DATABASE_URL' _ "$W"
}
connects_to() { case "$1" in bh_r_h11_06_*) psql "$BH_SERVER/$1" -XtAc 'select current_database()' 2>&1 ;; *) echo "(not connected: $1 is outside the test databases)" ;; esac; }

declare -A AFTER ADDED BEFORE
run_case() { # run_case TAG LINE
  local tag="$1" line="$2"
  printf '# the database this checkout serves\n%s\n' "$line" > "$W/core/.env"; chmod 600 "$W/core/.env"
  : > "$OUT/calls"
  echo; echo "== case $tag: core/.env's database line: $line"
  BEFORE[$tag]="$(service_db)"
  echo "   before: the service's reading names ${BEFORE[$tag]}; it connects to $(connects_to "${BEFORE[$tag]}")"
  echo "   before: lib.sh env_setting reads $(lib_db)"
  (cd "$W" && env -u OPENFERMENT_API_KEY -u OPENFERMENT_WORKSPACE_ID -u OPENFERMENT_DATABASE_URL \
     HOME="$OUT/home" PATH="$OUT/bin:/usr/bin:/bin" bash scripts/session-start.sh) > "$OUT/out-$tag" 2>&1
  local st=$?
  ADDED[$tag]="$(grep -c 'OPENFERMENT_DATABASE_URL added to core/.env' "$OUT/out-$tag")"
  echo "   session-start exit $st; its database lines: $(grep 'OPENFERMENT_DATABASE_URL' "$OUT/out-$tag" || echo '(none)')"
  echo "   stand-in calls: $(paste -sd ';' "$OUT/calls")"
  echo "   core/.env after:"; sed 's|^|      |' "$W/core/.env"
  AFTER[$tag]="$(service_db)"
  echo "   after: the service's reading names ${AFTER[$tag]}; it connects to $(connects_to "${AFTER[$tag]}")"
  echo "   after: lib.sh env_setting reads $(lib_db)"
}
run_case 0 "OPENFERMENT_DATABASE_URL=$URL"
run_case A "export OPENFERMENT_DATABASE_URL=$URL"
run_case B "OPENFERMENT_DATABASE_URL = $URL"
rm -f "$W/core/.env"

echo
echo "EXPECTED: a core/.env that names $DB in a form python-dotenv reads (export NAME=..., NAME = ...) is left as it is by session-start (session-start.sh:18-20: the development address joins core/.env only when core/.env names none), so the service reads $DB after the session start as before it."
echo "OBSERVED: control (NAME=url): before ${BEFORE[0]}, added ${ADDED[0]} line(s), after ${AFTER[0]}. export form: before ${BEFORE[A]}, added ${ADDED[A]} line(s), after ${AFTER[A]}. spaced form: before ${BEFORE[B]}, added ${ADDED[B]} line(s), after ${AFTER[B]}."
bad=0
for t in A B; do
  [ "${BEFORE[$t]}" = "$DB" ] && [ "${ADDED[$t]}" = 1 ] && [ "${AFTER[$t]}" = openferment_dev ] && bad=$((bad + 1))
done
if [ "$bad" = 2 ] && [ "${AFTER[0]}" = "$DB" ]; then echo "RESULT: DEFECT"; else echo "RESULT: NO-DEFECT"; fi
exit 0
