#!/usr/bin/env bash
# H12-12: a reading corrected twice is said to be corrected by its first correction, and no test sees it.
# bash bughunt/repro/H12-12/run.sh (from the repository root). Keyless, no model call, no service.
# In a scratch worktree of 2047f5a it
#   1. lists every test that asks which entry corrects a reading, with the corrections each one's
#      deposition holds after the reading it asks about (each holds one);
#   2. makes a fresh database bh_r_h12_12_probe and, in a project of its own, deposits one flow read
#      three times (de-1 confirmed, its correction de-3 read back, a second correction de-10 still
#      waiting to be read back), then asks measurements.corrected_by and looked_up about de-1: on the
#      tree as it stands, then with mutation M37 (`later[-1]` -> `later[0]`, the first correction named);
#   3. runs test_measurements.py, test_basis.py and test_finite_inputs.py with M37 applied.
# DEFECT: the tree names de-10, M37 names de-3 (the mutation changes what a person is told), and the
# three files pass with M37 applied. Every database made is bh_r_h12_12_*; all are dropped and the
# worktree removed at the end.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
N="$BH_ROOT/bughunt/notes/H12"
BASE="$BH_WORK/H12-12"
WT="$BASE/wt-$$"
DB=bh_r_h12_12_probe
TESTDB=bh_r_h12_12_t
PY="$BH_ROOT/core/.venv/bin/python"
LOG="$BASE/pytest-$$"

cleanup() {
  bh_db_drop "$DB" >/dev/null 2>&1
  for d in $(psql "$BH_SERVER/postgres" -XAtc "SELECT datname FROM pg_database WHERE datname LIKE 'bh\_r\_h12\_12\_%'" 2>/dev/null); do
    bh_db_drop "$d" >/dev/null 2>&1
  done
  git -C "$BH_ROOT" worktree remove --force "$WT" >/dev/null 2>&1
  git -C "$BH_ROOT" worktree prune >/dev/null 2>&1
  rm -rf "$LOG"
}
trap cleanup EXIT

nodefect() { echo "$1"; echo "RESULT: NO-DEFECT"; exit 0; }

mkdir -p "$BASE" "$LOG"
git -C "$BH_ROOT" worktree add --detach "$WT" 2047f5a >/dev/null 2>&1 || nodefect "worktree add failed"
# untracked test fixtures the suite reads (as survivor.sh copies them), and the conform scratch prefix
# renamed so any database the checks make is bh_r_h12_12_* (survivor.sh's base patch, the name changed)
cp "$BH_ROOT"/core/tests/fixtures/{units,competence-unrated,competence,fields,lock-digests,resolvers}.json "$WT/core/tests/fixtures/" 2>/dev/null
sed -i 's/^SCRATCH = "openferment_conform"$/SCRATCH = "bh_r_h12_12_conform"/' "$WT/core/openferment_core/engine/conform.py"
echo "== worktree $WT at $(git -C "$WT" rev-parse --short HEAD), diff: $(git -C "$WT" diff --stat | tail -1)"

# ── 1. the tests that ask which entry corrects a reading ────────────────
echo "== 1. the contract, and the tests that ask which entry corrects a reading"
sed -n '90,95p' "$WT/core/openferment_core/measurements.py" | sed 's#^#   measurements.py: #'
grep -rn --include='*.py' -E "corrected_by\(|was corrected by" "$WT/core/tests" | sed "s#$WT/##; s#^#   #"
echo "   each asks about a reading whose deposition holds one correction after it:"
echo "     ENTRIES: de-1 -> de-3 (m-flow, no time), de-5 -> de-7 (m-series at sample time 1)"
echo "     [*ENTRIES, de-10]: the lookup asks about de-3, whose one correction is de-10"
TWICE=$(grep -c -E "corrected_by\(body, by_id\[\"de-1\"\]\) == \"de-10\"|reading dep-1/de-1 was corrected by dep-1/de-10" \
        "$WT/core/tests/test_measurements.py")
echo "   tests asking about a reading corrected twice (de-1 with de-3 and de-10 after it): $TWICE"

# ── 2. a reading corrected twice, asked about on the tree and with M37 ──
echo "== 2. a flow read three times on $DB: de-1, its correction de-3, a second correction de-10 waiting"
bh_db_fresh "$DB" 2>/dev/null || nodefect "bh_db_fresh failed"
ask() {
  (cd "$WT/core" && bh_env PYTHONPATH="$WT/core" HF_HUB_OFFLINE=1 OPENFERMENT_DATABASE_URL="$BH_SERVER/$DB" \
     OPENFERMENT_PROJECT= "$PY" - "$1" <<'EOF'
import sys
from openferment_core import measurements, project_state, projects
from openferment_core.models import EngineInput, ProjectCreate

pid, by, taken = "h12-12-probe", "Ada Moreno", "2026-11-03T09:00:00Z"
if not any(p.id == pid for p in projects.listed()):
    projects.create(ProjectCreate(id=pid, name="H12-12 probe", by=by))

def entry(i, value, confirmed, corrected=None):
    return {"id": i, "measureId": "m-flow", "stepId": "s-1", "at": taken, "value": value, "unit": "kg/hr",
            "raw": "a placeholder reading", "confirmed": confirmed, "correctedAt": corrected}

with projects.using(pid):
    dep = sys.argv[1]
    body = {"id": dep, "runbookId": "rb-1", "protocolId": None, "operatorId": None, "state": "running",
            "startedAt": "2026-11-03T08:00:00Z", "closedAt": None, "observations": [], "reconciliation": None,
            "sampleTimes": {}, "entries": [
                entry("de-1", 2.0, True),
                entry("de-3", 3.0, True, "2026-11-03T09:10:00Z"),
                entry("de-10", 3.1, False, "2026-11-03T09:20:00Z")]}
    project_state.put("depositions", dep, body, by=by)
    held, kept_by = project_state.deposited(dep)[0]
    ids = {e["id"]: e for e in held["entries"]}
    named = measurements.corrected_by(held, ids["de-1"])
    first = measurements.corrected_by(held, ids["de-3"])
    value = EngineInput.model_validate({"name": "stream.sugarcane.F_mass", "quantity": {
        "value": 2.0, "unit": "kg/hr", "origin": {"kind": "measurement", "ref": f"{dep}/de-1"}}})
    try:
        measurements.looked_up(value, "kg/hr")
        said = "taken (no refusal)"
    except measurements.MeasurementRefused as e:
        said = str(e)
    print(f"{named}\t{first}\t{said}\t{measurements.__file__}")
EOF
  )
}
IFS=$'\t' read -r NAMED0 FIRST0 SAID0 FILE0 < <(ask dep-asis)
echo "   module: ${FILE0#$WT/}"
echo "   as it stands:  corrected_by(de-1) = $NAMED0; corrected_by(de-3) = $FIRST0"
echo "                  looked_up(de-1) refused: $SAID0"
(cd "$WT" && git apply "$N/mutations/M37.patch") || nodefect "M37 does not apply"
echo "   M37 applied:   $(cd "$WT" && git diff -U0 -- core/openferment_core/measurements.py | grep '^[-+] ' | tr -s ' ' | paste -sd' ' -)"
IFS=$'\t' read -r NAMED1 FIRST1 SAID1 FILE1 < <(ask dep-m37)
echo "   with M37:      corrected_by(de-1) = $NAMED1; corrected_by(de-3) = $FIRST1"
echo "                  looked_up(de-1) refused: $SAID1"

# ── 3. the three test files with M37 applied ────────────────────────────
echo "== 3. pytest test_measurements.py test_basis.py test_finite_inputs.py with M37"
(cd "$WT/core" && bh_env PYTHONPATH="$WT/core" HF_HUB_OFFLINE=1 OPENFERMENT_TEST_DATABASE_URL="$BH_SERVER/$TESTDB" \
   "$PY" -m pytest tests/test_measurements.py tests/test_basis.py tests/test_finite_inputs.py -q -p no:randomly \
   -p no:cacheprovider -m "not live and not sim and not slow and not lit" > "$LOG/m37.txt" 2>&1)
M37_RC=$?
tail -1 "$LOG/m37.txt" | sed 's#^#   #'
(cd "$WT" && git apply -R "$N/mutations/M37.patch")

echo "EXPECTED: corrected_by names the latest correction of a reading corrected twice (de-10, measurements.py:90-95), the refusal says de-10 waits, and a test of a reading with two corrections fails when the first (de-3) is named"
echo "OBSERVED: tree names $NAMED0; M37 names $NAMED1 and says \"${SAID1#*was corrected by }\"; tests asking about a reading corrected twice: $TWICE; the three files with M37: $(tail -1 "$LOG/m37.txt") (exit $M37_RC)"
if [ "$NAMED0" = "de-10" ] && [ "$NAMED1" = "de-3" ] && [ "$M37_RC" = 0 ] && [ "$TWICE" = 0 ]; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
