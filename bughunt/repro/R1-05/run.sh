#!/usr/bin/env bash
# R1-05 (and R2-04, the same line): the handoff report counts the docs/TOOLS.md the agent builder read at
# CORE=6f85338 as 838 lines; that file holds 837 lines, its last byte a newline.
# Run from the repository root: bash bughunt/repro/R1-05/run.sh
#
# A static defect: every read is a git object (git show), so no database, service, worktree or model call is
# needed, and nothing in the checkout is written. Keyless (env.sh sourced; bh_py runs the repository's Python).
# Steps:
#   1. the report's words at 2047f5a (line 82, the count; line 11, CORE; line 127, the size), and the commit that
#      wrote line 82 (git log -L);
#   2. docs/TOOLS.md at CORE=6f85338 and at the commit that wrote the line: wc -l, awk NR, Python splitlines()
#      (the counting test_guidance.py uses for CLAUDE.md), bytes, and the last byte;
#   3. where 838 comes from: Python split('\n') pieces at CORE, and the first commit whose TOOLS.md held 838 lines.
# Exits 0 either way.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
G() { git -C "$BH_ROOT" "$@"; }
HEAD_C=2047f5a
CORE=6f85338
REPORT=docs/reports/handoff-2026-11.md
TOOLS=docs/TOOLS.md
verdict() { echo "EXPECTED: $1"; echo "OBSERVED: $2"; echo "RESULT: $3"; exit 0; }

echo "== 1. the report at $HEAD_C"
G show "$HEAD_C:$REPORT" > /dev/null 2>&1 || verdict "the report at $HEAD_C" "git show failed" NO-DEFECT
G show "$HEAD_C:$REPORT" | grep -n -F 'CORE=6f85338' | head -1
line82=$(G show "$HEAD_C:$REPORT" | sed -n 82p)
echo "82:$line82"
G show "$HEAD_C:$REPORT" | grep -n -F '84 KB `docs/TOOLS.md`'
claimed=$(printf '%s\n' "$line82" | sed -n -E 's/.*`docs\/TOOLS\.md` whole \(([0-9]+) lines\).*/\1/p')
echo "the report's count: ${claimed:-none}"
[ -n "$claimed" ] || verdict "the report's line 82 names a line count for docs/TOOLS.md" "no count found on line 82" NO-DEFECT
wrote=$(G log -L82,82:"$REPORT" --format='COMMIT %h %s' "$HEAD_C" | grep '^COMMIT' | tail -1 | cut -c8-)
echo "the commit that wrote line 82: $wrote"
WROTE=${wrote%% *}

echo "== 2. docs/TOOLS.md at CORE=$CORE and at $WROTE"
count() {  # count COMMIT: wc -l, awk NR, splitlines, split('\n'), bytes, the last byte
  local c=$1 wl aw b last py
  wl=$(G show "$c:$TOOLS" | wc -l | tr -d ' ')
  aw=$(G show "$c:$TOOLS" | awk 'END{print NR}')
  b=$(G show "$c:$TOOLS" | wc -c | tr -d ' ')
  last=$(G show "$c:$TOOLS" | tail -c 1 | od -An -c | tr -d ' ')
  py=$(G show "$c:$TOOLS" | bh_py -I -c 'import sys; s=sys.stdin.read(); print(len(s.splitlines()), len(s.split("\n")))')
  echo "$wl $aw $b $last $py"
}
read -r c_wl c_aw c_b c_last c_sl c_sp <<< "$(count "$CORE")"
read -r w_wl w_aw w_b w_last w_sl w_sp <<< "$(count "$WROTE")"
echo "$CORE: wc -l $c_wl; awk NR $c_aw; splitlines() $c_sl; bytes $c_b; last byte '$c_last'"
echo "$WROTE: wc -l $w_wl; awk NR $w_aw; splitlines() $w_sl; bytes $w_b; last byte '$w_last'"
grep -n -F '.splitlines()' "$BH_ROOT/core/tests/test_guidance.py" | head -1 | sed 's#^#core/tests/test_guidance.py:#'

echo "== 3. where $claimed could come from"
echo "$CORE: split('\\n') pieces $c_sp (a file ending in a newline gives one empty piece after its last line)"
first=""; for c in $(G rev-list --reverse "$CORE..$HEAD_C" -- "$TOOLS"); do
  n=$(G show "$c:$TOOLS" | wc -l | tr -d ' ')
  if [ "$n" = "$claimed" ]; then first=$(G log -1 --format='%h %s' "$c" | cut -c1-90); break; fi
done
echo "the first commit after CORE whose TOOLS.md holds $claimed lines: ${first:-none}"
if [ -n "$first" ]; then
  G merge-base --is-ancestor "$WROTE" "${first%% *}" && echo "it comes after $WROTE, the commit that wrote the report's line"
fi

EXP="docs/TOOLS.md at CORE=$CORE holds the $claimed lines $REPORT:82 gives it ('\`docs/TOOLS.md\` whole ($claimed lines)')"
OBS="at $CORE it holds $c_wl lines (wc -l $c_wl, awk NR $c_aw, splitlines() $c_sl; $c_b bytes, the last byte a newline), and $w_wl at $WROTE, the commit that wrote line 82; $claimed is its split('\\n') piece count ($c_sp)"
if [ "$c_wl" != "$claimed" ] && [ "$c_aw" = "$c_wl" ] && [ "$c_sl" = "$c_wl" ] && [ "$c_last" = '\n' ] && [ "$w_wl" = "$c_wl" ]; then
  verdict "$EXP" "$OBS" DEFECT
fi
verdict "$EXP" "$OBS" NO-DEFECT
