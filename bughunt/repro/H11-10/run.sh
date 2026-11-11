#!/usr/bin/env bash
# H11-10: scripts/host/lib.sh's backup_database writes the night's dump to <name>.part and removes the .part
# only when pg_dump returns a failure (lib.sh:188-191). A night stopped by SIGTERM (launchd stopping the job,
# or a restart, which signals the job's process group) ends bash before that `rm`, and the rotation's glob
# (lib.sh:197) counts only openferment-YYYY-MM-DD.dump, so the stopped night's .part stays in the folder for
# good: no later night removes it.
# usage, from the repository root: bash bughunt/repro/H11-10/run.sh
#
# What runs: backup_database itself, sourced from a detached worktree of 2047f5a, as nightly.sh's first step
# calls it (`source lib.sh; backup_database`), with the real pg_dump (PostgreSQL 16 here) on a fresh test
# database. The only stand-ins: `date +%F` (to set each night's date) and a pg_dump wrapper that execs the real
# /usr/bin/pg_dump with the database name `openferment` swapped for this run's test database and the role's
# password from the environment. HOME is a scratch folder, so ~/openferment-backups is scratch too.
# To stop the dump half way the way a real night is stopped, a second session holds an ACCESS EXCLUSIVE lock on
# one table, so the real pg_dump has opened its .part and waits; the night's process group is then sent SIGTERM.
# Keyless and offline: no key is read and no network is reached beyond the local PostgreSQL.
source /home/user/openFermentUI/bughunt/lib/env.sh
SHA=2047f5a
T=$BH_WORK/H11-10; WT=$T/wt; OUT=$T/out
DB=bh_r_h11_10_dump
LOCKAPP=bh_h11_10_lock; DUMPAPP=bh_h11_10_dump
BACKUPS=$OUT/home/openferment-backups

q() { psql "$BH_SERVER/$DB" -XtAqc "$1" 2>/dev/null; }
cleanup() {
  [ -n "${NIGHT_PID:-}" ] && kill -KILL -- "-$NIGHT_PID" 2>/dev/null
  [ -n "${LOCK_PID:-}" ] && kill -KILL -- "-$LOCK_PID" 2>/dev/null
  bh_db_drop "$DB" 2>/dev/null
  git -C "$BH_ROOT" worktree remove --force "$WT" >/dev/null 2>&1
  rm -rf "$T"
}
trap cleanup EXIT
NIGHT_PID=""; LOCK_PID=""
cleanup; mkdir -p "$OUT/bin" "$OUT/launchd" "$BACKUPS"

echo "EXPECTED: scripts/host/lib.sh:172-173 'The dump is written beside its name and moved into place once whole, so"
echo "EXPECTED: a failed night keeps the seven as they were', lib.sh:189 removes the .part on a failed night, and"
echo "EXPECTED: core/tests/test_host.py:344 holds a failed night to 'no half file'; the runbook"
echo "EXPECTED: (docs/runbooks/live-host-install.md:260) says 'the newest seven are kept'. So a night stopped half"
echo "EXPECTED: way leaves no .part behind, or the next nights clear it: after the stopped night and three ordinary"
echo "EXPECTED: nights the folder holds the newest seven openferment-<date>.dump files and nothing else."

bh_db_fresh "$DB" 2>/dev/null || { echo "OBSERVED: could not make the test database $DB"; echo "RESULT: NO-DEFECT"; exit 0; }
git -C "$BH_ROOT" worktree add --detach "$WT" "$SHA" >/dev/null 2>&1 ||
  { echo "OBSERVED: could not add the worktree"; echo "RESULT: NO-DEFECT"; exit 0; }
LIB=$WT/scripts/host/lib.sh
echo "setup: worktree $(git -C "$WT" rev-parse --short HEAD); test database $DB, $(q "select count(*) from pg_tables where schemaname in ('openferment','sci_rag')") tables"
echo "setup: lib.sh:188-189 reads: $(sed -n 188p "$LIB" | sed 's/^ *//') / $(sed -n 189p "$LIB" | sed 's/^ *//')"
echo "setup: lib.sh:197 reads: $(sed -n 197p "$LIB" | sed 's/^ *//')"

# Stand-ins: the night's date, and the real pg_dump on this run's test database.
cat > "$OUT/bin/date" <<EOF
#!/bin/bash
if [ "\$*" = "+%F" ]; then cat "$OUT/today"; else exec /usr/bin/date "\$@"; fi
EOF
cat > "$OUT/bin/pg_dump" <<EOF
#!/bin/bash
echo "pg_dump \$*" >> "$OUT/calls"
args=(); for a in "\$@"; do [ "\$a" = openferment ] && a="$DB"; args+=("\$a"); done
PGUSER=openferment PGPASSWORD=openferment PGPORT=5432 PGAPPNAME=$DUMPAPP exec /usr/bin/pg_dump "\${args[@]}"
EOF
chmod 755 "$OUT/bin/date" "$OUT/bin/pg_dump"

# Seven kept dumps from the week before, as the folder holds them on an ordinary morning.
for d in 03 04 05 06 07 08 09; do printf 'kept %s\n' "$d" > "$BACKUPS/openferment-2026-11-$d.dump"; done
chmod 700 "$BACKUPS"; chmod 600 "$BACKUPS"/*
folder() { (cd "$BACKUPS" && ls | tr '\n' ' '); }
echo "setup: folder before: $(folder)"

start_night() { # start_night DATE: backup_database in a process group of its own, as launchd starts the job
  printf '%s' "$1" > "$OUT/today"
  setsid env PATH="$OUT/bin:/usr/bin:/bin" HOME="$OUT/home" OPENFERMENT_LAUNCHD_DIR="$OUT/launchd" \
    /bin/bash -c 'set -uo pipefail; source "$1"; backup_database' _ "$LIB" >> "$OUT/night-$1.log" 2>&1 &
  NIGHT_PID=$!
}

# Night 2026-11-10, stopped half way. A second session takes an ACCESS EXCLUSIVE lock on one table and holds it.
table=$(q "select format('%I.%I', schemaname, tablename) from pg_tables where schemaname = 'openferment' order by tablename limit 1")
setsid env PGAPPNAME=$LOCKAPP psql "$BH_SERVER/$DB" -XqAtc \
  "BEGIN; LOCK TABLE $table IN ACCESS EXCLUSIVE MODE; SELECT pg_sleep(120); COMMIT" >/dev/null 2>&1 &
LOCK_PID=$!
for i in $(seq 1 100); do
  [ "$(q "select count(*) from pg_locks l join pg_stat_activity a using (pid) where a.application_name = '$LOCKAPP' and l.mode = 'AccessExclusiveLock' and l.granted")" -ge 1 ] 2>/dev/null && break
  sleep 0.1
done
start_night 2026-11-10
part="$BACKUPS/openferment-2026-11-10.dump.part"
waiting=0
for i in $(seq 1 200); do
  waiting=$(q "select count(*) from pg_stat_activity where application_name = '$DUMPAPP' and wait_event_type = 'Lock'")
  [ "${waiting:-0}" -ge 1 ] && [ -e "$part" ] && break
  sleep 0.1
done
echo "night 2026-11-10: the real pg_dump has opened $(basename "$part") ($( [ -e "$part" ] && stat -c %s "$part" || echo none) bytes) and waits on the lock on $table (sessions waiting: ${waiting:-0}); SIGTERM to the night's process group"
kill -TERM -- "-$NIGHT_PID"; wait "$NIGHT_PID"; stopped_exit=$?; NIGHT_PID=""
q "select pg_terminate_backend(pid) from pg_stat_activity where application_name = '$LOCKAPP'" >/dev/null
kill -KILL -- "-$LOCK_PID" 2>/dev/null; wait "$LOCK_PID" 2>/dev/null; LOCK_PID=""
after_stop=$(folder)
echo "night 2026-11-10: exit $stopped_exit; the night's log: $(tr '\n' ' ' < "$OUT/night-2026-11-10.log")"
echo "night 2026-11-10: folder: $after_stop"

# Three ordinary nights after it: each dumps, moves its file into place and rotates.
for day in 2026-11-11 2026-11-12 2026-11-13; do
  start_night "$day"; wait "$NIGHT_PID"; e=$?; NIGHT_PID=""
  echo "night $day: exit $e; $(grep -c . "$OUT/night-$day.log") log lines: $(tr '\n' ' ' < "$OUT/night-$day.log" | sed "s|$OUT/home|~|g")"
  echo "night $day: folder: $(folder)"
done
echo "pg_dump calls: $(wc -l < "$OUT/calls"), each: $(head -1 "$OUT/calls" | sed "s|$OUT/home|~|g; s|2026-11-10|<date>|")"

dumps=$(cd "$BACKUPS" && ls | grep -cE '^openferment-[0-9]{4}-[0-9]{2}-[0-9]{2}\.dump$')
parts=$(cd "$BACKUPS" && ls | grep -c '\.part$')
real=$(cd "$BACKUPS" && for f in openferment-2026-11-1[123].dump; do pg_restore --list "$f" >/dev/null 2>&1 && echo ok; done | grep -c ok)
partread=$(pg_restore --list "$part" >/dev/null 2>&1 && echo reads it || echo refuses it)
echo "OBSERVED: the stopped night exited $stopped_exit and left $(basename "$part") in the folder ($(echo "$after_stop" | grep -o '\.part' | wc -l) .part after it; $(stat -c %s "$part" 2>/dev/null || echo no) bytes now, and pg_restore --list $partread)."
echo "OBSERVED: after three ordinary nights (each a whole dump pg_restore reads: $real of 3) the folder holds $dumps dated dumps and $parts .part file(s): $(folder)"
if [ "$stopped_exit" -ge 128 ] && [ "$parts" -ge 1 ] && [ -e "$part" ] && [ "$real" = 3 ]; then
  echo "OBSERVED: no later night removed the stopped night's half file; the rotation's glob never names it."
  echo "RESULT: DEFECT"
else
  echo "OBSERVED: the folder holds only the dated dumps (or the stop did not land as a signal: exit $stopped_exit)."
  echo "RESULT: NO-DEFECT"
fi
exit 0
