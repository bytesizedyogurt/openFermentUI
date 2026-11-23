#!/usr/bin/env bash
# H12-15: does test:core on the container's Python 3.13.17 let a real break of
# refused_class's IPv4-mapped rule pass? M57 drops `seen = _v4(address)` from
# core/openferment_core/literature/collectors.py:287 in a scratch worktree of
# 2047f5a; test_sff_url.py and test_collectors.py run under Python 3.12.3 and
# 3.13.17; probe.py asks, for 231,072 IPv4-mapped addresses on each Python,
# what refused_class answers with the line kept and with it dropped.
# Run from the repository root: bash bughunt/repro/H12-15/run.sh
source /home/user/openFermentUI/bughunt/lib/env.sh
HERE=$BH_ROOT/bughunt/repro/H12-15
BASE=$BH_WORK/H12-15
WT=$BASE/wt-$$
OUT=$BASE/out-$$
DB=bh_r_h12_15_gate
PY313=$BH_ROOT/core/.venv/bin/python
PY312=/tmp/claude-0/-home-user-openFermentUI/cfbc5c9f-640a-5002-a705-5ceaf850fdc6/scratchpad/py312/bin/python
FILES=(tests/test_sff_url.py tests/test_collectors.py)

cleanup() {
  git -C "$BH_ROOT" worktree remove --force "$WT" >/dev/null 2>&1
  git -C "$BH_ROOT" worktree prune >/dev/null 2>&1
  rm -rf "$OUT"
  for d in $(psql "$BH_SERVER/postgres" -AtXc "SELECT datname FROM pg_database WHERE datname LIKE 'bh\_r\_h12\_15\_%'"); do
    bh_db_drop "$d"
  done
}
trap cleanup EXIT
mkdir -p "$BASE" "$OUT"

bh_db_fresh "$DB" 2>/dev/null || { echo "RESULT: NO-DEFECT (setup failed: database)"; exit 0; }
git -C "$BH_ROOT" worktree add --detach -q "$WT" 2047f5a || { echo "RESULT: NO-DEFECT (setup failed: worktree)"; exit 0; }
echo "worktree $WT at $(git -C "$WT" rev-parse --short HEAD); test database prefix $DB"

# pytest PY LABEL ARGS...: the selection under one Python, the worktree's code first on the path.
run_tests() {
  local py=$1 label=$2; shift 2
  (cd "$WT/core" && bh_env OPENFERMENT_DATABASE_URL= PYTHONPATH="$WT/core" \
     OPENFERMENT_TEST_DATABASE_URL="$BH_SERVER/$DB" \
     "$py" -m pytest "$@" -q -p no:randomly -p no:cacheprovider -rf \
     -m "not live and not sim and not slow and not lit") > "$OUT/$label.log" 2>&1
  local summary; summary=$(grep -E '^(=+ )?[0-9]+ (passed|failed)' "$OUT/$label.log" | tail -1 | tr -d '=' | sed 's/^ *//')
  echo "  $label: $summary"
  grep '^FAILED' "$OUT/$label.log" | sed 's/^/    /'
}
probe() {
  local py=$1 label=$2
  (cd "$OUT" && bh_env PYTHONPATH="$WT/core" "$py" "$HERE/probe.py" "$OUT/$label.tsv") | sed "s/^/  $label: /"
}

echo "== the kept tree (2047f5a): the two IPv4-mapped rows of REFUSED, both tests"
run_tests "$PY312" kept-3.12 tests/test_sff_url.py -k ffff
run_tests "$PY313" kept-3.13 tests/test_sff_url.py -k ffff
probe "$PY312" kept-3.12
probe "$PY313" kept-3.13

git -C "$WT" apply "$HERE/M57.patch" || { echo "RESULT: NO-DEFECT (setup failed: M57 did not apply)"; exit 0; }
echo "== M57 applied: $(sed -n 287p "$WT/core/openferment_core/literature/collectors.py" | sed 's/^ *//') (collectors.py:287)"
run_tests "$PY312" m57-3.12 "${FILES[@]}"
run_tests "$PY313" m57-3.13 "${FILES[@]}"
probe "$PY312" m57-3.12
probe "$PY313" m57-3.13

failed312=$(grep -cE '^FAILED' "$OUT/m57-3.12.log")
failed313=$(grep -cE '^FAILED' "$OUT/m57-3.13.log")
diff312=$(diff "$OUT/kept-3.12.tsv" "$OUT/m57-3.12.tsv" | grep -c '^>')
diff313=$(diff "$OUT/kept-3.13.tsv" "$OUT/m57-3.13.tsv" | grep -c '^>')
open312=$(paste "$OUT/kept-3.12.tsv" "$OUT/m57-3.12.tsv" | awk -F'\t' '$2!="None" && $4=="None"' | wc -l)
echo "== what dropping the line changes in refused_class's answers"
echo "  3.12.3: $diff312 of 231072 mapped addresses answered in other words ($open312 of them let through); for example:"
diff "$OUT/kept-3.12.tsv" "$OUT/m57-3.12.tsv" | grep '^[<>]' | grep -E '::ffff:(127\.0\.0\.0|10\.0\.0\.0|169\.254\.0\.0)\b' | sed 's/^/    /'
echo "  3.13.17: $diff313 of 231072 mapped addresses answered in other words"

echo "EXPECTED: the candidate's claim, a break of the IPv4-mapped rule that the container's gate (3.13.17) lets pass: with M57 applied, test_sff_url.py and test_collectors.py fail on 3.12.3 and pass on 3.13.17 while refused_class answers some mapped address in other words on 3.13.17"
echo "OBSERVED: with M57 applied, $failed312 tests fail on 3.12.3 and $failed313 on 3.13.17; refused_class answers $diff312 mapped addresses in other words on 3.12.3 and $diff313 on 3.13.17, where every IPv6Address property it reads defers to ipv4_mapped beside is_site_local, which no mapped address holds in either form (probe line above), so on 3.13.17 the dropped line changes no answer for a test to see, and CI's 3.12.3 run catches the drop"
if [ "$failed312" -gt 0 ] && [ "$failed313" -eq 0 ] && [ "$diff313" -gt 0 ]; then
  echo "RESULT: DEFECT"
elif [ "$failed312" -eq 0 ] && [ "$diff312" -gt 0 ]; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
