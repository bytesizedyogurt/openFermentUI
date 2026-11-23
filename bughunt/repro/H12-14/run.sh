#!/usr/bin/env bash
# H12-14: the rank of `user` against `industry-estimate` is held by nothing but the two copies agreeing.
# bash bughunt/repro/H12-14/run.sh (from the repository root). Keyless, no model call, no service.
# In a scratch worktree of 2047f5a it
#   1. prints the contract (models.py's comments, check-plan.mjs's three relations, test_basis's pin);
#   2. runs check:plan on the tree, then with G1 (PROVENANCE_RANK swapped alone) and G2
#      (PROVENANCE_ORDER swapped alone): the check discriminates each copy on its own;
#   3. applies G4 (user and industry-estimate swapped in PROVENANCE_ORDER and PROVENANCE_RANK together,
#      the Provenance Literal left as it is), runs check:plan, asks weakest_provenance and
#      basis_provenance about a basis resting on a `user` artifact and an `industry-estimate` record
#      (on the tree and with G4), and reads the Literal's order against PROVENANCE_ORDER;
#   4. runs test_basis.py, test_validate.py, test_evidence_pool.py, test_postdoc_agent.py and
#      test_openapi.py with G4 applied, then test_openapi.py with G3 (the Literal swapped too) as the
#      control that the run reads the mutated worktree.
# DEFECT: check:plan passes G4, the five files pass G4, and the class a claim on those two sources
# carries moves from industry-estimate to user. Every database made is bh_r_h12_14_*; all are dropped
# and the worktree removed at the end.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
# A mutation swaps two lines, so the source keeps its size, and git apply can land in the second the
# module was compiled in; a cached .pyc would then pass for the mutated source. No bytecode is kept.
export PYTHONDONTWRITEBYTECODE=1
N="$BH_ROOT/bughunt/notes/H12"
BASE="$BH_WORK/H12-14"
WT="$BASE/wt-$$"
DB=bh_r_h12_14_probe
TESTDB=bh_r_h12_14_t
PY="$BH_ROOT/core/.venv/bin/python"
LOG="$BASE/log-$$"

cleanup() {
  bh_db_drop "$DB" >/dev/null 2>&1
  for d in $(psql "$BH_SERVER/postgres" -XAtc "SELECT datname FROM pg_database WHERE datname LIKE 'bh\_r\_h12\_14\_%'" 2>/dev/null); do
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
# renamed so any database the checks make is bh_r_h12_14_* (survivor.sh's base patch, the name changed)
cp "$BH_ROOT"/core/tests/fixtures/{units,competence-unrated,competence,fields,lock-digests,resolvers}.json "$WT/core/tests/fixtures/" 2>/dev/null
sed -i 's/^SCRATCH = "openferment_conform"$/SCRATCH = "bh_r_h12_14_conform"/' "$WT/core/openferment_core/engine/conform.py"
echo "== worktree $WT at $(git -C "$WT" rev-parse --short HEAD), diff: $(git -C "$WT" diff --stat | tail -1)"
bh_db_fresh "$DB" 2>/dev/null || nodefect "bh_db_fresh failed"
echo "== fresh database $DB made and migrated (the probe runs with it as OPENFERMENT_DATABASE_URL)"

# ── 1. the contract ─────────────────────────────────────────────────────
echo "== 1. the contract"
sed -n '23,27p' "$WT/core/openferment_core/models.py" | sed 's#^#   models.py: #'
sed -n '41,42p' "$WT/core/openferment_core/models.py" | sed 's#^#   models.py: #'
sed -n '10,14p' "$WT/scripts/check-plan.mjs" | sed 's#^#   check-plan.mjs: #'
sed -n '88,92p' "$WT/core/tests/test_basis.py" | sed 's#^#   test_basis.py: #'
PAIR=$(grep -rln --include='*.py' -E "industry-estimate" "$WT/core/tests" | xargs -r grep -ln -E "provenance[=:\"' ]+\"?user\"" 2>/dev/null | wc -l)
echo "   test files holding a 'user' class beside an 'industry-estimate' one: $PAIR"

# ── 2. check:plan on the tree and on each copy swapped alone ────────────
plan() { (cd "$WT" && node scripts/check-plan.mjs > "$LOG/plan-$1.txt" 2>&1); echo $?; }
PLAN_TREE=$(plan tree)
(cd "$WT" && git apply "$N/mutations/G1-provenance-rank-swap.patch") || nodefect "G1 does not apply"
echo "== 2. G1: $(cd "$WT" && git diff -U0 -- src/store.ts | grep '^[-+] ' | tr -s ' ' | paste -sd' ' -)"
PLAN_G1=$(plan g1)
(cd "$WT" && git apply -R "$N/mutations/G1-provenance-rank-swap.patch")
(cd "$WT" && git apply "$N/mutations/G2-provenance-order-swap.patch") || nodefect "G2 does not apply"
echo "   G2: PROVENANCE_ORDER's \"user\" moved below \"industry-estimate\" ($(cd "$WT" && git diff --stat -- core/openferment_core/models.py | tail -1 | sed 's/^ *//'))"
PLAN_G2=$(plan g2)
(cd "$WT" && git apply -R "$N/mutations/G2-provenance-order-swap.patch")
echo "   check:plan exit: tree $PLAN_TREE; G1 (rank alone) $PLAN_G1; G2 (order alone) $PLAN_G2"
grep -h -E '^\s+- ' "$LOG/plan-g1.txt" "$LOG/plan-g2.txt" | sed 's#^ *#   caught: #'

# ── 3. G4: both copies swapped together ─────────────────────────────────
ask() {
  (cd "$WT/core" && bh_env PYTHONPATH="$WT/core" HF_HUB_OFFLINE=1 OPENFERMENT_DATABASE_URL="$BH_SERVER/$DB" \
     OPENFERMENT_PROJECT= "$PY" - <<'EOF'
from openferment_core import models
from openferment_core.basis import basis_provenance
from openferment_core.models import BasisInput, BasisSource, ComputedBasis, PROVENANCE_ORDER, Provenance, weakest_provenance

basis = ComputedBasis(tool="t", toolVersion="v", artifactId="a", at="2026-11-11T00:00:00Z", inputs=[
    BasisInput(name="a person's artifact", value="x", unit="", source=BasisSource(kind="artifact", id="a-user")),
    BasisInput(name="a vendor figure", value="x", unit="", source=BasisSource(kind="record", id="r-industry"))])
got = basis_provenance(basis, {"r-industry": {"provenance": "industry-estimate"}}, {"a-user": {"provenance": "user"}})
lit = list(Provenance.__args__)
print("\t".join([weakest_provenance(["user", "industry-estimate"]), got,
                 " > ".join(lit[5:]), " > ".join(PROVENANCE_ORDER[5:]), "same" if lit == PROVENANCE_ORDER else "differ",
                 models.__file__]))
EOF
  )
}
IFS=$'\t' read -r W0 B0 LIT0 ORD0 SAME0 FILE0 < <(ask)
echo "== 3. module: ${FILE0#$WT/}"
echo "   tree: weakest(user, industry-estimate) = $W0; basis_provenance(user artifact + industry record) = $B0"
echo "         Literal tail $LIT0; PROVENANCE_ORDER tail $ORD0 ($SAME0)"
(cd "$WT" && git apply "$N/mutations/G4-user-industry-swap-order-and-rank.patch") || nodefect "G4 does not apply"
find "$WT" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null
echo "   G4 applied:$(cd "$WT" && git diff --stat -- src/store.ts core/openferment_core/models.py | tail -1) (PROVENANCE_ORDER and PROVENANCE_RANK; the Literal untouched)"
PLAN_G4=$(plan g4)
IFS=$'\t' read -r W1 B1 LIT1 ORD1 SAME1 FILE1 < <(ask)
echo "   G4:   weakest(user, industry-estimate) = $W1; basis_provenance(user artifact + industry record) = $B1"
echo "         Literal tail $LIT1; PROVENANCE_ORDER tail $ORD1 ($SAME1)"
echo "   check:plan with G4: exit $PLAN_G4, '$(grep -E '✓|✗' "$LOG/plan-g4.txt" | head -1 | sed 's/^ *//')'"

# ── 4. the tests over the provenance readers with G4 ────────────────────
echo "== 4. pytest test_basis.py test_validate.py test_evidence_pool.py test_postdoc_agent.py test_openapi.py with G4"
(cd "$WT/core" && bh_env PYTHONPATH="$WT/core" HF_HUB_OFFLINE=1 OPENFERMENT_DATABASE_URL= \
   OPENFERMENT_TEST_DATABASE_URL="$BH_SERVER/$TESTDB" \
   "$PY" -m pytest tests/test_basis.py tests/test_validate.py tests/test_evidence_pool.py tests/test_postdoc_agent.py \
   tests/test_openapi.py -q -p no:randomly -p no:cacheprovider -m "not live and not sim and not slow and not lit" \
   > "$LOG/g4-pytest.txt" 2>&1)
G4_RC=$?
tail -1 "$LOG/g4-pytest.txt" | sed 's#^#   #'
(cd "$WT" && git apply -R "$N/mutations/G4-user-industry-swap-order-and-rank.patch")
# the control: G3 swaps the Literal too, and test_openapi sees the generated document move
(cd "$WT" && git apply "$N/mutations/G3-user-industry-swap-both.patch") || nodefect "G3 does not apply"
find "$WT" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null
(cd "$WT/core" && bh_env PYTHONPATH="$WT/core" HF_HUB_OFFLINE=1 OPENFERMENT_DATABASE_URL= \
   OPENFERMENT_TEST_DATABASE_URL="$BH_SERVER/$TESTDB" \
   "$PY" -m pytest tests/test_openapi.py -q -p no:randomly -p no:cacheprovider \
   -m "not live and not sim and not slow and not lit" > "$LOG/g3-pytest.txt" 2>&1)
G3_RC=$?
echo "   control G3 (the Literal swapped too), test_openapi.py: $(tail -1 "$LOG/g3-pytest.txt") (exit $G3_RC)"
grep -m1 -E '^FAILED' "$LOG/g3-pytest.txt" | sed 's#^#   #'
(cd "$WT" && git apply -R "$N/mutations/G3-user-industry-swap-both.patch")

echo "EXPECTED: a check or test that holds user above industry-estimate, as the Literal (strongest first) and PROVENANCE_RANK order them, so swapping the two in both ranking copies fails something (models.py:23-27, 41-42; check-plan.mjs:10-14)"
echo "OBSERVED: check:plan exit tree $PLAN_TREE, G1 $PLAN_G1, G2 $PLAN_G2, G4 $PLAN_G4; with G4 a basis on a user artifact and an industry-estimate record is '$B1' (tree '$B0'), the Literal and PROVENANCE_ORDER $SAME1, and the five files: $(tail -1 "$LOG/g4-pytest.txt") (exit $G4_RC); the control G3 fails test_openapi (exit $G3_RC)"
if [ "$PLAN_TREE" = 0 ] && [ "$PLAN_G1" != 0 ] && [ "$PLAN_G2" != 0 ] && [ "$PLAN_G4" = 0 ] && [ "$G4_RC" = 0 ] \
   && [ "$W0" = "industry-estimate" ] && [ "$B0" = "industry-estimate" ] && [ "$W1" = "user" ] && [ "$B1" = "user" ] \
   && [ "$SAME0" = same ] && [ "$SAME1" = differ ] && [ "$G3_RC" != 0 ]; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
