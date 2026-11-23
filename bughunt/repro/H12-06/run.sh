#!/usr/bin/env bash
# H12-06: no test keeps biorefineries out of the service process. CLAUDE.md:41 holds that "the service process imports
# none of" BioSTEAM, thermosteam, biorefineries, the SFF toolkit and cobra, citing core/tests/test_boundaries.py; that
# file's docstring hands the worker side to test_workers.py ("test_workers.py names each file"). test_workers.py's grep
# (ALLOWED) holds cobra, biosteam, thermosteam, scipy and pisces_sff and has no row for biorefineries, and
# test_boundaries.py's NEVER rows hold db/, projects/, literature/, engine/ and studies/ alone, so a top-level service
# module such as proforma.py is held by neither. In a worktree of 2047f5a of this run's own (the repository's venv
# linked in) it runs:
#   1. the guard's map, read from the two test files by ast;
#   2. a probe on the tree as it is: the service imported, retired_entry_of called, the worker libraries listed;
#   3. a control: proforma.retired_entry_of gains a function-level `import biosteam` (control.patch), and
#      test_workers.py's grep should fail on it;
#   4. the plant: the same line imports biorefineries (mutation.patch, the hunt's N09), and the tests the candidate
#      names (test_workers, test_boundaries, test_proforma, test_proforma_runs, test_engines) are run;
#   5. the probe again on the planted tree.
# A fresh database of its own (bh_r_h12_06_db) stands in OPENFERMENT_DATABASE_URL, the tests' session databases are
# made under the prefix bh_r_h12_06_t, and conform's scratch databases (test_engines) under bh_r_h12_06_cf (the
# worktree's conform.py SCRATCH renamed); all are dropped, and the worktree removed, at the end.
#   bash bughunt/repro/H12-06/run.sh        (from the repository root; exits 0 either way)
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PYTHONDONTWRITEBYTECODE=1 PGOPTIONS='-c client_min_messages=warning'
R=$BH_ROOT/bughunt/repro/H12-06
DB=bh_r_h12_06_db
TPREFIX=bh_r_h12_06_t
CFPREFIX=bh_r_h12_06_cf
S=$BH_WORK/H12-06; mkdir -p "$S"
WT=$S/wt-$$
T=$(mktemp -d "$S/run.XXXXXX")
cleanup() {
  for d in $(psql "$BH_SERVER/postgres" -XAtc "select datname from pg_database where datname like 'bh\_r\_h12\_06\_%'" 2>/dev/null); do
    bh_db_drop "$d"; done
  git -C "$BH_ROOT" worktree remove --force "$WT" >/dev/null 2>&1; git -C "$BH_ROOT" worktree prune
  rm -rf "$T" "$WT"; rmdir "$S" 2>/dev/null
}
trap cleanup EXIT
fail() { echo "the steps did not complete: $*"; echo "RESULT: NO-DEFECT"; exit 0; }

git -C "$BH_ROOT" worktree add --detach "$WT" 2047f5a >/dev/null 2>&1 || fail "no worktree at 2047f5a"
ln -s "$BH_ROOT/core/.venv" "$WT/core/.venv"
# The fixtures the export scripts write (gitignored), as survivor.sh copies them.
cp "$BH_ROOT"/core/tests/fixtures/{units,competence-unrated,competence,fields,lock-digests,resolvers}.json "$WT/core/tests/fixtures/"
# conform's scratch databases take this run's prefix (test_engines makes them).
sed -i "s/^SCRATCH = \"openferment_conform\"$/SCRATCH = \"$CFPREFIX\"/" "$WT/core/openferment_core/engine/conform.py"
grep -q "^SCRATCH = \"$CFPREFIX\"$" "$WT/core/openferment_core/engine/conform.py" || fail "conform's SCRATCH not renamed"
bh_db_fresh "$DB" || fail "bh_db_fresh $DB"
echo "worktree $WT at $(git -C "$WT" rev-parse --short HEAD); database $DB (fresh)"

wtpy() {   # the worktree's package, keyless, on this run's databases
  (cd "$WT/core" && bh_env OPENFERMENT_DATABASE_URL="$BH_SERVER/$DB" OPENFERMENT_TEST_DATABASE_URL="$BH_SERVER/$TPREFIX" \
     PYTHONPATH="$WT/core" timeout 900 .venv/bin/python "$@" 2>&1)
}
wttest() { wtpy -m pytest "$@" -q -p no:randomly -p no:cacheprovider -m "not live and not sim and not slow and not lit"; }

echo "contract, CLAUDE.md:41: $(sed -n 41p "$BH_ROOT/CLAUDE.md" | cut -c1-230)"

# 1. The guard's map, read by ast from the worktree's two test files.
wtpy - "$WT/core/tests" <<'EOF'
import ast, sys
from pathlib import Path
tests = Path(sys.argv[1])
def dict_keys(file, name):
    for n in ast.parse((tests / file).read_text()).body:
        t = n.targets[0] if isinstance(n, ast.Assign) else getattr(n, "target", None)
        if isinstance(t, ast.Name) and t.id == name and isinstance(n.value, ast.Dict):
            return [ast.literal_eval(k) for k in n.value.keys]
w = dict_keys("test_workers.py", "ALLOWED"); b = dict_keys("test_boundaries.py", "NEVER")
print("1. test_workers.py ALLOWED (the grep's libraries):", sorted(w), "| biorefineries among them:", "biorefineries" in w)
print("1. test_boundaries.py NEVER (the packages held from SIMULATION):", sorted(b), "| proforma.py's top level among them:", "proforma" in b)
EOF

# 2. The probe on the tree as it is.
wtpy "$R/probe.py" > "$T/probe-head.log"
HEAD_SEEN=$(sed -n 's/^PROBE-SEEN //p' "$T/probe-head.log")
grep '^probe:' "$T/probe-head.log" | sed 's/^/2. head: /'
grep -q '^PROBE-SEEN' "$T/probe-head.log" || { tail -5 "$T/probe-head.log"; fail "the probe did not run on the head"; }

# 3. Control: a function-level `import biosteam` at the same place.
(cd "$WT" && git apply "$R/control.patch") || fail "control.patch does not apply"
wttest tests/test_workers.py -k heavy_libraries > "$T/control.log"; CONTROL=$?
(cd "$WT" && git apply -R "$R/control.patch") || fail "control.patch does not reverse"
echo "3. control (import biosteam in proforma.retired_entry_of), test_workers.py -k heavy_libraries: exit $CONTROL, $(tail -1 "$T/control.log")"
grep -o "biosteam is imported outside its worker: \[[^]]*\]" "$T/control.log" | head -1 | sed 's/^/3.   /'

# 4. The plant: a function-level `import biorefineries` at the same place.
(cd "$WT" && git apply "$R/mutation.patch") || fail "mutation.patch does not apply"
echo "4. planted: $(cd "$WT" && git diff -U0 core/openferment_core/proforma.py | grep '^+ ' | sed 's/^+ *//')"
wttest tests/test_workers.py tests/test_boundaries.py tests/test_proforma.py tests/test_proforma_runs.py tests/test_engines.py \
  -k "not sigterm_ends_the_command" > "$T/plant.log"; PLANT=$?
echo "4. test_workers, test_boundaries, test_proforma, test_proforma_runs, test_engines on the planted tree: exit $PLANT, $(tail -1 "$T/plant.log")"
grep -E "^(FAILED|ERROR)" "$T/plant.log" | head -5 | sed 's/^/4.   /'

# 5. The probe on the planted tree.
wtpy "$R/probe.py" > "$T/probe-plant.log"
PLANT_SEEN=$(sed -n 's/^PROBE-SEEN //p' "$T/probe-plant.log")
grep '^probe:' "$T/probe-plant.log" | sed 's/^/5. planted: /'
grep -q '^PROBE-SEEN' "$T/probe-plant.log" || { tail -5 "$T/probe-plant.log"; fail "the probe did not run on the planted tree"; }
(cd "$WT" && git apply -R "$R/mutation.patch")

echo "EXPECTED: a service module (proforma.py) importing biorefineries fails a boundary test, as the control's import of biosteam fails test_workers.py's grep; the service process holds none of the worker libraries"
echo "OBSERVED: control exit $CONTROL; planted tree exit $PLANT ($(tail -1 "$T/plant.log")); worker libraries in the service process after retired_entry_of: head [${HEAD_SEEN}], planted [${PLANT_SEEN}]"
if [ "$CONTROL" -ne 0 ] && grep -q "proforma.py" "$T/control.log" && [ "$PLANT" -eq 0 ] && [ -z "$HEAD_SEEN" ] \
   && [[ ",$PLANT_SEEN," == *",biorefineries,"* ]]; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
