#!/usr/bin/env bash
# H11-11: scripts/host/lib.sh's backup_database keeps the seven dump names that sort last. When the Mac's
# clock reads a date earlier than the kept files' (a clock set back), tonight's dump sorts first, and the
# rotation removes it a line after "openferment dumped into ...", and the night still returns 0.
# usage, from the repository root: bash bughunt/repro/H11-11/run.sh
#
# backup_database is run from a detached worktree of 2047f5a under $BH_WORK/H11-11/wt, in a scratch HOME,
# with two stand-ins on PATH ahead of /usr/bin:/bin: `date +%F` answers the night's date from a file (every
# other `date` call goes to /usr/bin/date), and `pg_dump` runs the real /usr/bin/pg_dump with lib.sh's
# arguments, the database `openferment` replaced by a fresh migrated test database, bh_r_h11_11_dump, so
# every dump is a real custom-format dump and the live database is never named. There is no brew here, so
# lib.sh takes pg_dump from the path. Keyless and offline: no key is read and no service is started.
source /home/user/openFermentUI/bughunt/lib/env.sh
SHA=2047f5a
T=$BH_WORK/H11-11; WT=$T/wt; OUT=$T/out
DB=bh_r_h11_11_dump
B="$OUT/home/openferment-backups"

cleanup() {
  git -C "$BH_ROOT" worktree remove --force "$WT" >/dev/null 2>&1
  bh_db_drop "$DB" 2>/dev/null
  rm -rf "$T"
}
trap cleanup EXIT
cleanup; mkdir -p "$OUT/bin" "$OUT/home"

echo "EXPECTED: scripts/host/lib.sh:168-170 'one file a day named by its date, the newest seven kept': the dump a"
echo "EXPECTED: night makes is the newest, so after a night that prints 'openferment dumped into <file>' and returns 0,"
echo "EXPECTED: <file> is in ~/openferment-backups; a night that cannot keep it says so in words and returns non-zero."

bh_db_fresh "$DB" 2>/dev/null || { echo "OBSERVED: could not make $DB"; echo "RESULT: NO-DEFECT"; exit 0; }
git -C "$BH_ROOT" worktree add --detach "$WT" "$SHA" >/dev/null 2>&1 ||
  { echo "OBSERVED: could not add the worktree"; echo "RESULT: NO-DEFECT"; exit 0; }
LIB="$WT/scripts/host/lib.sh"
echo "setup: worktree $(git -C "$WT" rev-parse --short HEAD); database $DB migrated; lib.sh:197-198 reads:"
sed -n '197,198p' "$LIB" | sed 's/^/setup:   /'

cat > "$OUT/bin/date" <<EOF
#!/bin/bash
if [ "\$*" = "+%F" ]; then cat "$OUT/today"; else exec /usr/bin/date "\$@"; fi
EOF
cat > "$OUT/bin/pg_dump" <<EOF
#!/bin/bash
args=(); for a in "\$@"; do [ "\$a" = openferment ] && a="$BH_SERVER/$DB"; args+=("\$a"); done
exec /usr/bin/pg_dump "\${args[@]}"
EOF
chmod 755 "$OUT/bin/date" "$OUT/bin/pg_dump"

night() { # night DATE: one run of backup_database as nightly.sh runs it; its output into $OUT/night-DATE.log
  printf '%s' "$1" > "$OUT/today"
  env PATH="$OUT/bin:/usr/bin:/bin" HOME="$OUT/home" /bin/bash -c \
    'set -uo pipefail; source "$1"; backup_database' _ "$LIB" > "$OUT/night-$1.log" 2>&1
  echo $?
}
kept() { (cd "$B" 2>/dev/null && ls -1 | LC_ALL=C sort | sed 's/^openferment-//; s/\.dump$//' | tr '\n' ' '); }

# Seven nights with the clock right, 6 to 12 January 2027.
for d in 2027-01-0{6..9} 2027-01-1{0..2}; do night "$d" >/dev/null; done
echo "setup: seven nights, 2027-01-06 to 2027-01-12; the folder holds: $(kept)"

# A control night with the clock right: the eighth file pushes the oldest out and tonight's stays.
s=$(night 2027-01-13)
ctl_ok=0; [ "$s" = 0 ] && [ -s "$B/openferment-2027-01-13.dump" ] && [ ! -e "$B/openferment-2027-01-06.dump" ] && ctl_ok=1
echo "control: night 2027-01-13 (clock right): status $s; log: $(tr '\n' '|' < "$OUT/night-2027-01-13.log" | sed "s|$OUT/home|~|g")"
echo "control: the folder holds: $(kept)"

# The clock set back a year: the Mac reads 2026-01-14 on the night after 2027-01-13.
s=$(night 2026-01-14)
tonight="$B/openferment-2026-01-14.dump"
echo "OBSERVED: night 2026-01-14 (the clock a year back): status $s; its log, line by line:"
sed "s|$OUT/home|~|g; s/^/OBSERVED:   /" "$OUT/night-2026-01-14.log"
echo "OBSERVED: the folder after it holds: $(kept)"
if [ -e "$tonight" ]; then echo "OBSERVED: tonight's dump openferment-2026-01-14.dump is in the folder"
else echo "OBSERVED: tonight's dump openferment-2026-01-14.dump is gone, though the night said it dumped into it"; fi

# The next night, the clock still a year back: the same again, so no night's dump survives until the date
# passes the oldest kept name.
s2=$(night 2026-01-15)
echo "OBSERVED: night 2026-01-15 (still a year back): status $s2; $(tr '\n' '|' < "$OUT/night-2026-01-15.log" | sed "s|$OUT/home|~|g")"
echo "OBSERVED: the folder after it holds: $(kept)"

said_dumped=0; grep -q "openferment dumped into .*openferment-2026-01-14.dump" "$OUT/night-2026-01-14.log" && said_dumped=1
said_removed=0; grep -q "openferment-2026-01-14.dump removed: the newest 7 are kept" "$OUT/night-2026-01-14.log" && said_removed=1
if [ "$ctl_ok" = 1 ] && [ "$s" = 0 ] && [ "$said_dumped" = 1 ] && [ "$said_removed" = 1 ] && [ ! -e "$tonight" ]; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
