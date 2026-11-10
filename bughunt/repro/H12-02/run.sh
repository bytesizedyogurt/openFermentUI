#!/usr/bin/env bash
# H12-02: conformance checks 1, 3, 4, 5 and 8 can be made to hold whatever they read, and no test sees it.
# Run from the repository root: bash bughunt/repro/H12-02/run.sh
#
# In a scratch worktree of 2047f5a (conform's scratch prefix renamed so every database made is bh_r_h12_02_*),
# keyless, on a fresh configured database bh_r_h12_02_cfg and the tests' own bh_r_h12_02_t_* database:
#   1. the suite's conform-reading files run once on the tree as it is, a plugin recording which tests reach each
#      check function (h12_02_reached.py); all pass, and the five probes (test_zz_h12_02_probe.py), each an engine
#      or a service that breaks one check, pass too: each check fails the break it is shown;
#   2. each of the candidate's five mutations (mutate.py) is applied in turn, and the tests that reach the mutated
#      function run beside that check's probe: the suite stays green while the probe fails, so the mutation changes
#      what the check decides and no test of the suite sees it. A control mutation of check 2 is caught.
# The worktree is removed and every bh_r_h12_02_* database dropped when it ends. Exits 0 either way.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
HERE=/home/user/openFermentUI/bughunt/repro/H12-02
TAG="$(date +%s)-$$"
BASE="$BH_WORK/H12-02"
WT="$BASE/wt-$TAG"
OUT="$BASE/out-$TAG"
CFG=bh_r_h12_02_cfg
PY="$BH_ROOT/core/.venv/bin/python"
MARKERS="not live and not sim and not slow and not lit"
FILES=(tests/test_engines.py tests/test_engine_diagnostics.py tests/test_measurements.py tests/test_train.py
       tests/test_pureos_build_tool.py tests/test_finite_inputs.py)
PROBE=tests/test_zz_h12_02_probe.py

drop_ours() {
  local n
  for n in $(psql "$BH_SERVER/postgres" -AtqXc "SELECT datname FROM pg_database WHERE datname LIKE 'bh\_r\_h12\_02\_%'"); do
    bh_db_drop "$n"
  done
}
cleanup() {
  [ -d "$WT" ] && git -C "$BH_ROOT" worktree remove --force "$WT" >/dev/null 2>&1
  git -C "$BH_ROOT" worktree prune >/dev/null 2>&1
  drop_ours
  rm -rf "$OUT"
}
trap cleanup EXIT
mkdir -p "$OUT"
verdict() { echo "EXPECTED: $1"; echo "OBSERVED: $2"; echo "RESULT: $3"; exit 0; }

# ── the scratch worktree ──
git -C "$BH_ROOT" worktree add --detach "$WT" 2047f5a >/dev/null 2>&1 || verdict "a worktree of 2047f5a" "git worktree add failed" NO-DEFECT
echo "worktree: $WT at $(git -C "$WT" rev-parse --short HEAD)"
CONFORM="$WT/core/openferment_core/engine/conform.py"
sed -i 's/^SCRATCH = "openferment_conform"$/SCRATCH = "bh_r_h12_02_cf"/' "$CONFORM"
grep -q '^SCRATCH = "bh_r_h12_02_cf"$' "$CONFORM" || verdict "the scratch prefix renamed" "the SCRATCH line was not found" NO-DEFECT
# The fixture files the tests read that git does not hold (made by the repository's scripts), copied, read only.
cp "$BH_ROOT"/core/tests/fixtures/{units,competence-unrated,competence,fields,lock-digests,resolvers}.json "$WT/core/tests/fixtures/"
cp "$HERE/test_zz_h12_02_probe.py" "$WT/core/$PROBE"
cp "$CONFORM" "$OUT/conform.pristine.py"
echo "the worktree's only change to the code: $(git -C "$WT" diff --stat -- core/openferment_core | tail -1)"
drop_ours
bh_db_fresh "$CFG" 2>/dev/null || verdict "a fresh database $CFG" "bh_db_fresh failed" NO-DEFECT
echo "databases: $CFG made fresh and migrated; the tests make and drop their own bh_r_h12_02_t_* database"

# pytest in the worktree, keyless, its results as JUnit XML in $OUT/$1.xml; the summary line printed.
run_tests() {
  local name="$1"; shift
  (cd "$WT/core" && bh_env PYTHONPATH="$HERE:$WT/core" H12_02_REACHED="$OUT/reached.json" \
     OPENFERMENT_DATABASE_URL="$BH_SERVER/$CFG" OPENFERMENT_TEST_DATABASE_URL="$BH_SERVER/bh_r_h12_02_t" \
     "$PY" -m pytest "$@" -q -p no:randomly -p no:cacheprovider -m "$MARKERS" --junitxml="$OUT/$name.xml" \
     < /dev/null > "$OUT/$name.log" 2>&1)
  tail -1 "$OUT/$name.log"
}
# count <name> passed|failed suite|probe: the tests in $OUT/<name>.xml of that outcome, among the suite's own
# (suite) or H12-02's probes (probe), skipped ones left out; prints "n name...".
count() {
  python3 - "$OUT/$1.xml" "$2" "$3" <<'EOF'
import sys, xml.etree.ElementTree as ET
path, want, among = sys.argv[1], sys.argv[2], sys.argv[3]
out = []
for tc in ET.parse(path).getroot().iter("testcase"):
    bad = any(c.tag in ("failure", "error") for c in tc)
    skipped = any(c.tag == "skipped" for c in tc)
    probe = tc.get("classname", "").endswith("test_zz_h12_02_probe")
    if probe != (among == "probe") or skipped:
        continue
    if (want == "failed") == bad:
        out.append(tc.get("name", ""))
print(len(out), *out)
EOF
}

# ── 1. the tree as it is: the suite's conform-reading files, recorded; then the probes ──
echo "== 1. unmutated: ${FILES[*]}"
echo "   $(run_tests base -p h12_02_reached "${FILES[@]}" -k 'not sigterm_ends_the_command')"
[ -s "$OUT/reached.json" ] || verdict "the recorder's file" "no reached.json was written" NO-DEFECT
read -r BASE_FAILED _ <<<"$(count base failed suite)"
read -r BASE_PASSED _ <<<"$(count base passed suite)"
LOADED=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['conform'])" "$OUT/reached.json")
echo "   conform imported from: $LOADED"
case "$LOADED" in "$WT"/*) ;; *) verdict "conform imported from the worktree" "it came from $LOADED" NO-DEFECT;; esac
python3 - "$OUT/reached.json" <<'EOF'
import json, sys
for fn, nodes in json.load(open(sys.argv[1]))["reached"].items():
    print(f"   {len(nodes):2d} tests reach conform.{fn}")
EOF
echo "   $(run_tests probes "$PROBE")"
read -r PROBES_PASSED _ <<<"$(count probes passed probe)"
echo "   suite: $BASE_PASSED passed, $BASE_FAILED failed; probes on the tree as it is: $PROBES_PASSED of 5 pass"
[ "$BASE_FAILED" = 0 ] && [ "$PROBES_PASSED" = 5 ] \
  || verdict "a green suite and five passing probes on the tree as it is" "suite $BASE_FAILED failed, probes $PROBES_PASSED of 5 passed (see the logs)" NO-DEFECT

# ── 2. each mutation: the tests that reach its function, and its check's probe ──
declare -A PROBE_OF=([M52]=test_probe_check_1_fails_a_door_that_reaches_the_worker_before_it_refuses
                     [M51]=test_probe_check_3_fails_a_run_that_no_row_keeps
                     [M50]=test_probe_check_4_fails_an_output_that_moves_between_two_runs
                     [M53]=test_probe_check_5_fails_a_run_whose_sff_file_does_not_validate
                     [M54]=test_probe_check_8_fails_a_row_whose_created_by_is_not_the_asker)
echo "== 2. one mutation at a time (mutate.py), conform.py restored after each"
SURVIVED=0; SEEN=""; CONTROL=""
while read -r ID CHECK FN; do
  cp "$OUT/conform.pristine.py" "$CONFORM"
  python3 "$HERE/mutate.py" "$CONFORM" "$ID" || { echo "   $ID: did not apply"; continue; }
  mapfile -t T < <(python3 -c "import json,sys; [print(x) for x in json.load(open(sys.argv[1]))['reached'][sys.argv[2]]]" "$OUT/reached.json" "$FN")
  [ -n "${PROBE_OF[$ID]:-}" ] && T+=("$PROBE::${PROBE_OF[$ID]}")
  summary=$(run_tests "$ID" "${T[@]}")
  cp "$OUT/conform.pristine.py" "$CONFORM"
  read -r SF SFN <<<"$(count "$ID" failed suite)"
  read -r SP _ <<<"$(count "$ID" passed suite)"
  read -r PF _ <<<"$(count "$ID" failed probe)"
  line="$ID ${CHECK//_/ } (conform.$FN): suite tests reaching it $SP passed, $SF failed"
  if [ "$ID" = C2 ]; then
    echo "   $line [control] ${SFN:-}"
    [ "$SF" -gt 0 ] && CONTROL=caught || CONTROL=missed
    continue
  fi
  if [ "$PF" = 1 ]; then
    said=$(grep -m1 -E "^E +AssertionError: check" "$OUT/$ID.log" | sed -E 's/^E +AssertionError: //')
    echo "   $line; probe FAILED: $said"
  else
    echo "   $line; probe passed (the mutation left the check's decision as it was)"
  fi
  if [ "$SF" = 0 ] && [ "$SP" -gt 0 ] && [ "$PF" = 1 ]; then SURVIVED=$((SURVIVED + 1)); SEEN="$SEEN ${ID}(${CHECK//_/ })"; fi
  echo "     pytest: $summary"
done < <(python3 "$HERE/mutate.py" "$CONFORM" --list)
cmp -s "$OUT/conform.pristine.py" "$CONFORM" && echo "   conform.py restored"

# ── 3. the sim suite's conformance tests, read: each asserts only that every check holds ──
echo "== 3. core/tests/test_engines_sim.py (marker sim, not run here): its assertions on conform.checks"
grep -n -A2 "conform.checks(" "$BH_ROOT/core/tests/test_engines_sim.py" | grep -E "assert" | sed 's/^/   /'

EXP="under each of the five mutations (check 1 ignoring that the engine was reached, check 3 ignoring the row count, check 4 ignoring the replay, check 5 ignoring an invalid SFF file, check 8 ignoring created_by), some test that reaches the mutated function fails, as test_engines.py:571 does for check 2"
if [ "$CONTROL" = caught ] && [ "$SURVIVED" = 5 ]; then
  verdict "$EXP" "all five survive: every suite test reaching each mutated function passes, while a probe shows each mutated check holding an engine or service that breaks it:$SEEN; the control mutation of check 2 is caught" DEFECT
elif [ "$CONTROL" = caught ] && [ "$SURVIVED" -gt 0 ]; then
  verdict "$EXP" "$SURVIVED of five survive with a probe showing the check's decision changed:$SEEN; the control mutation of check 2 is caught" DEFECT
else
  verdict "$EXP" "survivors with a changed decision: $SURVIVED of 5; control: ${CONTROL:-not run}" NO-DEFECT
fi
