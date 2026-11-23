#!/usr/bin/env bash
# H12-13: is_measurement's rule that a reading's note says when it was measured is untested.
# bash bughunt/repro/H12-13/run.sh (from the repository root). Keyless, no model call, no service.
# In a scratch worktree of 2047f5a it
#   1. prints the contract (basis.py:195-202, ADR-006:188-192);
#   2. lists, from the test sources' syntax trees, every deposition basis source a test under core/tests builds
#      (BasisSource(kind="deposition"), measurement_source, fermos.fit) with the id and note it carries, and
#      counts those whose id is reading-shaped and whose note begins with something other than `measured on`:
#      the only sources the note clause decides;
#   3. makes a fresh database bh_r_h12_13_probe and asks, on the tree and with mutation M05 (the note clause
#      dropped), what a deposition source with a reading-shaped id and fermOS's series note is: is_measurement,
#      origin_of, is_set, basis_provenance, and the provenance of the fit fermos.fit keeps for a depositionId
#      "dep-b1/de-1" (the id POST /api/fermos/fit takes as the request names it);
#   4. runs the hunt's eight test files for M05 and the two test_engines tests that build a reading, with M05
#      applied and a counter beside it that writes a line for each call whose answer the note clause decides.
# DEFECT: M05 changes what the probe is told (a fit read as measured), no test builds a source the clause
# decides, no call in the test run is one, and the selection passes with M05. Every database made is
# bh_r_h12_13_*; all are dropped and the worktree removed at the end.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
N="$BH_ROOT/bughunt/notes/H12"
BASE="$BH_WORK/H12-13"
WT="$BASE/wt-$$"
DB=bh_r_h12_13_probe
TESTDB=bh_r_h12_13_t
PY="$BH_ROOT/core/.venv/bin/python"
TMP="$BASE/tmp-$$"

cleanup() {
  for d in $(psql "$BH_SERVER/postgres" -XAtc "SELECT datname FROM pg_database WHERE datname LIKE 'bh\_r\_h12\_13\_%'" 2>/dev/null); do
    bh_db_drop "$d" >/dev/null 2>&1
  done
  git -C "$BH_ROOT" worktree remove --force "$WT" >/dev/null 2>&1
  git -C "$BH_ROOT" worktree prune >/dev/null 2>&1
  rm -rf "$TMP"
}
trap cleanup EXIT

nodefect() { echo "$1"; echo "RESULT: NO-DEFECT"; exit 0; }

mkdir -p "$BASE" "$TMP/data"
git -C "$BH_ROOT" worktree add --detach "$WT" 2047f5a >/dev/null 2>&1 || nodefect "worktree add failed"
# untracked test fixtures the suite reads (as survivor.sh copies them), and the conform scratch prefix
# renamed so any database the checks make is bh_r_h12_13_* (survivor.sh's base patch, the name changed)
cp "$BH_ROOT"/core/tests/fixtures/{units,competence-unrated,competence,fields,lock-digests,resolvers}.json "$WT/core/tests/fixtures/" 2>/dev/null
sed -i 's/^SCRATCH = "openferment_conform"$/SCRATCH = "bh_r_h12_13_conform"/' "$WT/core/openferment_core/engine/conform.py"
echo "== worktree $WT at $(git -C "$WT" rev-parse --short HEAD), diff: $(git -C "$WT" diff --stat | tail -1)"

# ── 1. the contract ────────────────────────────────────────────────────
echo "== 1. the contract"
sed -n '195,202p' "$WT/core/openferment_core/basis.py" | sed 's#^#   basis.py: #'
sed -n '188,192p' "$WT/docs/decisions/ADR-006-quantities-and-estimates.md" | sed 's#^#   ADR-006: #'

# ── 2. every deposition basis source the tests build ──────────────────
cat > "$TMP/scan.py" <<'EOF'
"""Every deposition basis source a test under core/tests builds, with its id and note as the test writes them,
and every fermOS fit a test asks for, with the deposition id it names (its note is fermOS's own). A source the
note clause of basis.is_measurement decides is one whose id is reading-shaped (<deposition id>/<entry id>) and
whose note begins with something other than `measured on`."""
import ast, pathlib, re, sys

READING_REF = re.compile(r"^[^/\s]{1,200}/[^/\s]{1,200}$")  # models.py:739
root = pathlib.Path(sys.argv[1])

CONSTANTS = {}  # a test module's own `NAME = "..."` lines, read before its calls


def text(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name) and node.id in CONSTANTS:
        return CONSTANTS[node.id]
    if isinstance(node, ast.JoinedStr):
        return "".join(v.value if isinstance(v, ast.Constant) else "{...}" for v in node.values)
    return None if node is None else "<" + ast.unparse(node) + ">"

def name(func):
    return func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")

rows, deciding, fit_requests = [], 0, 0
for path in sorted(root.glob("test_*.py")):
    tree = ast.parse(path.read_text(), str(path))
    CONSTANTS.clear()
    CONSTANTS.update({t.id: a.value.value for a in tree.body if isinstance(a, ast.Assign)
                      and isinstance(a.value, ast.Constant) and isinstance(a.value.value, str)
                      for t in a.targets if isinstance(t, ast.Name)})
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            keys = [text(k) if k is not None else None for k in node.keys]
            if "depositionId" in keys and "series" in keys:  # a POST /api/fermos/fit body
                sid = text(node.values[keys.index("depositionId")])
                if sid is not None and READING_REF.fullmatch(sid):
                    fit_requests += 1
                    rows.append(f"{path.name}:{node.lineno}  fit request  depositionId={sid!r}  <- the note clause decides")
            continue
        if not isinstance(node, ast.Call):
            continue
        kw = {k.arg: k.value for k in node.keywords if k.arg}
        f = name(node.func)
        if f == "BasisSource" and text(kw.get("kind")) == "deposition":
            how, sid, note = "BasisSource", text(kw.get("id")), text(kw.get("note")) or ""
        elif f == "measurement_source":
            how, sid = "measurement_source", text(node.args[0]) if node.args else text(kw.get("ref"))
            note = "measured on ... (measurement_source stamps it, basis.py:103)"
        elif f == "fit" and isinstance(node.func, ast.Attribute) and getattr(node.func.value, "id", "") == "fermos":
            how, sid = "fermos.fit", text(node.args[0]) if node.args else None
            note = "the readings as the browser sent them; ... (fermos.py:368)"
        else:
            continue
        shaped = sid is not None and bool(READING_REF.fullmatch(sid))
        decides = shaped and not note.startswith("measured on")
        deciding += decides
        rows.append(f"{path.name}:{node.lineno}  {how}  id={sid!r}  reading-shaped={shaped}  note={note!r}"
                    + ("  <- the note clause decides" if decides else ""))
print("\n".join(rows))
print(f"SOURCES {len(rows)} DECIDING {deciding + fit_requests}")
EOF
echo "== 2. every deposition basis source the tests build (syntax trees of core/tests/test_*.py)"
"$PY" -I "$TMP/scan.py" "$WT/core/tests" > "$TMP/scan.txt" 2>&1 || nodefect "the scan failed: $(tail -1 "$TMP/scan.txt")"
grep -v '^SOURCES' "$TMP/scan.txt" | sed 's#^#   #'
read -r _ SOURCES _ DECIDING < <(grep '^SOURCES' "$TMP/scan.txt")
echo "   sources and fits: $SOURCES; with a reading-shaped id and a note other than 'measured on': $DECIDING"

# ── 3. a series source with a reading-shaped id, on the tree and with M05 ──
cat > "$TMP/probe.py" <<'EOF'
import sys
import numpy as np
from openferment_core import artifacts, basis, fermos, projects
from openferment_core.models import BasisInput, BasisSource, ComputedBasis, FermosPoint, FermosSeries, ProjectCreate

pid, by = sys.argv[1], "Ada Moreno"
if not any(p.id == pid for p in projects.listed()):
    projects.create(ProjectCreate(id=pid, name=pid, by=by))

def said(f):
    try:
        return str(f())
    except Exception as e:  # what the call raises, by its class
        return f"raises {e.__class__.__name__}"

# A deposition source with a reading-shaped id and the note fermOS writes for a whole series (fermos.py:367-368).
NOTE = "the readings as the browser sent them; the service cannot see the deposition itself"
src = BasisSource(kind="deposition", id="dep-b1/de-1", note=NOTE)
inp = BasisInput(name="biomass series", value="[]", unit="g L-1", source=src)
alone = said(lambda: basis.basis_provenance(ComputedBasis(tool="t", toolVersion="v", inputs=[inp], artifactId="a",
                                                          at="2026-11-03"), {}, {}))

def series(role, t, v):
    return FermosSeries(measureId=f"m-{role}", label=role, unit="g L-1", role=role,
                        points=[FermosPoint(t=float(a), value=float(b), entryId=f"{role}-{i}", confirmed=True)
                                for i, (a, b) in enumerate(zip(t, v))])

# A placeholder biomass series, built here from parameters chosen here (as test_fermos.py builds its own).
t = np.linspace(0, 30, 10)
x, _ = fermos.logistic(t, 0.1, 0.35, 8.0)
with projects.using(pid):
    # fermOS's fit as POST /api/fermos/fit makes it, its depositionId as the request names it (models.py FermosFitRequest)
    fit = said(lambda: artifacts.get(fermos.fit("dep-b1/de-1", [series("biomass", t, x)]).kineticArtifactId).provenance)
    plain = said(lambda: artifacts.get(fermos.fit("dep-b1", [series("biomass", t, x)]).kineticArtifactId).provenance)
print("\t".join([said(lambda: basis.is_measurement(src)), said(lambda: basis.origin_of(src).kind),
                 said(lambda: basis.is_set(src)), alone, fit, plain, basis.__file__]))
EOF
probe() {
  (cd "$WT/core" && bh_env PYTHONPATH="$WT/core" PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 \
     OPENFERMENT_DATABASE_URL="$BH_SERVER/$DB" OPENFERMENT_DATA_DIR="$TMP/data" OPENFERMENT_PROJECT= \
     BH_H12_13_DECIDED="$2" "$PY" "$TMP/probe.py" "$1" 2>"$TMP/probe-$1.err")
}
echo "== 3. a deposition source dep-b1/de-1 with fermOS's series note, on $DB"
bh_db_fresh "$DB" 2>/dev/null || nodefect "bh_db_fresh failed"
IFS=$'\t' read -r IS0 ORIGIN0 SET0 ALONE0 FIT0 PLAIN0 FILE0 < <(probe h12-13-tree "$TMP/decided-probe-tree.txt")
[ -n "${FILE0:-}" ] || nodefect "the probe on the tree failed: $(tail -1 "$TMP/probe-h12-13-tree.err")"
echo "   module: ${FILE0#$WT/}"
echo "   as it stands: is_measurement=$IS0 origin_of=$ORIGIN0 is_set=$SET0 basis_provenance=$ALONE0"
echo "                 fermos.fit('dep-b1/de-1') kept as $FIT0; fermos.fit('dep-b1') kept as $PLAIN0"

(cd "$WT" && git apply "$N/mutations/M05.patch") || nodefect "M05 does not apply"
echo "   M05 applied:  $(cd "$WT" && git diff -U0 -- core/openferment_core/basis.py | grep '^[-+] ' | tr -s ' ' | paste -sd' ' -)"
# The counter: it returns what M05's is_measurement returns, and writes a line for each call whose answer
# the note clause decides. Appended after the module's own definitions, it is the global every caller reads.
cat >> "$WT/core/openferment_core/basis.py" <<'EOF'


# bughunt H12-13: a counter beside M05. It returns what M05's is_measurement returns, and writes one line for
# each call whose answer the note clause decides (a deposition, its id reading-shaped, its note another).
_bh_m05_is_measurement = is_measurement


def is_measurement(source: BasisSource) -> bool:
    got = _bh_m05_is_measurement(source)
    if (source.kind == "deposition" and READING_REF.fullmatch(source.id or "")
            and not _MEASURED.match(source.note or "")):
        import os
        with open(os.environ["BH_H12_13_DECIDED"], "a") as f:
            f.write(f"{source.id!r} {source.note!r}\n")
    return got
EOF
: > "$TMP/decided-probe.txt"
IFS=$'\t' read -r IS1 ORIGIN1 SET1 ALONE1 FIT1 PLAIN1 FILE1 < <(probe h12-13-m05 "$TMP/decided-probe.txt")
[ -n "${FILE1:-}" ] || nodefect "the probe with M05 failed: $(tail -1 "$TMP/probe-h12-13-m05.err")"
PROBE_DECIDED=$(wc -l < "$TMP/decided-probe.txt")
echo "   with M05:     is_measurement=$IS1 origin_of=$ORIGIN1 is_set=$SET1 basis_provenance=$ALONE1"
echo "                 fermos.fit('dep-b1/de-1') kept as $FIT1; fermos.fit('dep-b1') kept as $PLAIN1"
echo "                 calls the counter saw the note clause decide in the probe: $PROBE_DECIDED"

# ── 4. the tests with M05 and the counter ───────────────────────────────
TESTS=(tests/test_basis.py tests/test_estimates.py tests/test_measurements.py tests/test_finite_inputs.py
       tests/test_params.py tests/test_fermos.py tests/test_exports.py tests/test_comparisons.py
       "tests/test_engines.py::test_a_kept_trains_defaults_each_name_one_of_the_five_default_origins_by_every_path_that_keeps_one"
       "tests/test_engines.py::test_the_copy_holds_every_row_a_trains_resolution_reads_and_resolves_each_train_as_the_project_does")
echo "== 4. pytest, M05 with the counter: the hunt's eight files for M05 and the two test_engines tests that build a reading"
: > "$TMP/decided-tests.txt"
(cd "$WT/core" && bh_env PYTHONPATH="$WT/core" PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 OPENFERMENT_DATA_DIR="$TMP/data" \
   BH_H12_13_DECIDED="$TMP/decided-tests.txt" OPENFERMENT_TEST_DATABASE_URL="$BH_SERVER/$TESTDB" \
   "$PY" -m pytest "${TESTS[@]}" -q -p no:randomly -p no:cacheprovider \
   -m "not live and not sim and not slow and not lit" > "$TMP/m05.txt" 2>&1)
M05_RC=$?
SUMMARY=$(tail -1 "$TMP/m05.txt")
TEST_DECIDED=$(wc -l < "$TMP/decided-tests.txt")
echo "   $SUMMARY (exit $M05_RC)"
echo "   calls the counter saw the note clause decide in the test run: $TEST_DECIDED"
(cd "$WT" && git checkout -q -- core/openferment_core/basis.py)

echo "EXPECTED: a test builds a deposition source with a reading-shaped id and a note other than 'measured on <at>' (basis.py:195-200: a reading's note says when it was taken; ADR-006:188-192) and holds it to the bench's record, so the fit resting on it stays computed; dropping the note clause (M05) fails that test"
echo "OBSERVED: tree: is_measurement=$IS0, origin $ORIGIN0, fit $FIT0; M05: is_measurement=$IS1, origin_of $ORIGIN1, fit $FIT1; tests building a source the clause decides: $DECIDING of $SOURCES; calls it decided in the test run: $TEST_DECIDED (the probe's: $PROBE_DECIDED); the selection with M05: $SUMMARY (exit $M05_RC)"
if [ "$IS0" = False ] && [ "$ORIGIN0" = record ] && [ "$FIT0" = computed ] && [ "$IS1" = True ] && [ "$FIT1" = measured ] \
   && [ "$PROBE_DECIDED" -gt 0 ] && [ "$DECIDING" = 0 ] && [ "$TEST_DECIDED" = 0 ] && [ "$M05_RC" = 0 ]; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
