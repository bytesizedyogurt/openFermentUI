#!/bin/bash
# backup-rotation.sh LIB OUT: lib.sh's backup_database, run night after night against stand-ins
# for brew, date and pg_dump, in a scratch HOME whose path holds a space. Checks, after every
# night, that the folder keeps exactly the newest seven dumps by date (the rule the comment and
# the runbook state), across a month boundary and a year boundary, and what a failed dump, a
# dump onto a full disk and a clock set back leave behind. LIB is scripts/host/lib.sh.
# BASHBIN names the bash to run (default /bin/bash); BASH_COMPAT may be set by the caller.
set -uo pipefail
LIB="$1"; OUT="$2"; BASHBIN="${BASHBIN:-/bin/bash}"
rm -rf "$OUT"; mkdir -p "$OUT/bin" "$OUT/keg/bin" "$OUT/home dir"
export HOME="$OUT/home dir"
B="$HOME/openferment-backups"
cat > "$OUT/bin/brew" <<EOF
#!/bin/bash
[ "\$*" = "--prefix --installed postgresql@17" ] && echo "$OUT/keg" && exit 0
exit 1
EOF
# date +%F answers the night in $OUT/today; every other call goes to the real date.
cat > "$OUT/bin/date" <<EOF
#!/bin/bash
if [ "\$*" = "+%F" ]; then cat "$OUT/today"; else exec /usr/bin/date "\$@"; fi
EOF
# pg_dump: MODE in $OUT/mode: ok (writes the night's name), half (writes half, fails), full (the
# file is /dev/full: ENOSPC on the first write, as pg_dump meets a full disk).
cat > "$OUT/keg/bin/pg_dump" <<EOF
#!/bin/bash
for a in "\$@"; do case "\$a" in --file=*) out="\${a#--file=}" ;; esac; done
case "\$(cat "$OUT/mode")" in
  ok) printf 'dump of %s\n' "\$(cat "$OUT/today")" > "\$out" ;;
  half) printf half > "\$out"; exit 1 ;;
  full) ln -sf /dev/full "\$out"; printf 'dump\n' > "\$out" || { echo "pg_dump: error: could not write to output file: No space left on device" >&2; exit 1; } ;;
esac
EOF
chmod 755 "$OUT/bin/brew" "$OUT/bin/date" "$OUT/keg/bin/pg_dump"
PATH="$OUT/bin:/usr/bin:/bin"

night() { # night DATE MODE: one run of backup_database; prints its status
  printf '%s' "$1" > "$OUT/today"; printf '%s' "$2" > "$OUT/mode"
  PATH="$PATH" HOME="$HOME" "$BASHBIN" -c 'set -uo pipefail; source "$1"; backup_database' _ "$LIB" \
    >> "$OUT/log" 2>&1
  echo $?
}
kept() { (cd "$B" 2>/dev/null && ls -1 | LC_ALL=C sort | tr '\n' ' '); }
expect_newest7() { # expect_newest7 DATES...: the folder holds exactly the newest seven of DATES
  local want; want="$(printf 'openferment-%s.dump\n' "$@" | LC_ALL=C sort | tail -7 | tr '\n' ' ')"
  [ "$(kept)" = "$want" ] && echo ok || echo "WRONG kept=[$(kept)] want=[$want]"
}

pass=0 fail=0
check() { if [ "$2" = ok ]; then pass=$((pass+1)); else fail=$((fail+1)); fi; printf '%-58s %s\n' "$1" "$2"; }

# 1. Seven nights, then the eighth: the first one goes.
days=(); for d in 2026-10-0{1..8}; do days+=("$d"); s=$(night "$d" ok); done
check "eight nights: newest seven kept (status $s)" "$(expect_newest7 "${days[@]}")"
# 2. Across a month boundary, night by night.
r=ok; for d in 2026-10-{25..31} 2026-11-0{1..9}; do days+=("$d"); night "$d" ok >/dev/null
  [ "$(expect_newest7 "${days[@]}")" = ok ] || r="WRONG on $d: $(kept)"; done
check "nights across 31 Oct into November" "$r"
# 3. Across a year boundary, night by night.
r=ok; for d in 2026-12-{20..31} 2027-01-0{1..9}; do days+=("$d"); night "$d" ok >/dev/null
  [ "$(expect_newest7 "${days[@]}")" = ok ] || r="WRONG on $d: $(kept)"; done
check "nights across 31 Dec into 2027" "$r"
# 4. The same night run twice: one file a day.
before="$(kept)"; night 2027-01-09 ok >/dev/null
[ "$(kept)" = "$before" ] && r=ok || r="WRONG: $(kept)"
check "the same night again keeps one file for the day" "$r"
# 5. A dump that fails half way: status 1, nothing removed, no .part left.
before="$(kept)"; s=$(night 2027-01-10 half)
[ "$s" = 1 ] && [ "$(kept)" = "$before" ] && r=ok || r="WRONG status=$s kept=[$(kept)]"
check "a dump failing half way keeps the seven, no .part" "$r"
# 6. A full disk: status 1, nothing removed, no .part left.
before="$(kept)"; s=$(night 2027-01-11 full)
[ "$s" = 1 ] && [ "$(kept)" = "$before" ] && r=ok || r="WRONG status=$s kept=[$(kept)]"
check "a full disk keeps the seven, no .part" "$r"
# 7. A file of the owner's own and a dump named otherwise stay.
printf mine > "$B/notes.txt"; printf x > "$B/openferment-before-upgrade.dump"
night 2027-01-12 ok >/dev/null
case "$(kept)" in *notes.txt*openferment-before-upgrade.dump*|*openferment-before-upgrade.dump*notes.txt*) r=ok ;; *) r="WRONG: $(kept)" ;; esac
check "other files in the folder are left alone" "$r"
rm -f "$B/notes.txt" "$B/openferment-before-upgrade.dump"
# 8. Modes: the folder 700, every dump 600.
m="$(stat -c %a "$B") $(cd "$B" && stat -c %a ./* | sort -u | tr '\n' ' ')"
[ "$m" = "700 600 " ] && r=ok || r="WRONG modes: $m"
check "folder 700, dumps 600" "$r"
# 9. A clock set back a year: tonight's dump sorts oldest and is the one removed.
s=$(night 2026-01-13 ok)
[ -e "$B/openferment-2026-01-13.dump" ] && r=ok || r="WRONG: tonight's dump (2026-01-13) was removed at once; status $s; kept=[$(kept)]"
check "a clock set back keeps tonight's dump" "$r"
echo "passed $pass, failed $fail"; echo "--- the log's last lines:"; tail -4 "$OUT/log"
