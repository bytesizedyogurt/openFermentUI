#!/usr/bin/env bash
# H9-03: the spend gate's two tests stub extract.extract_paper with llm.BudgetExhausted, an exception the real
# extract_paper never lets out, so they pass while the gate keeps no proposal on the real path.
# Run from the repository root: bash bughunt/repro/H9-03/run.sh
#
# In a scratch worktree of 2047f5a, keyless, with no service and no network (a stand-in client fails any send),
# on a fresh configured database bh_r_h9_03_cfg and the tests' own bh_r_h9_03_t_* database (made and dropped by
# the suite's conftest), one pytest session a tree, each running four tests:
#   T1 test_writes.py::test_an_extraction_the_budget_refuses_becomes_a_spend_proposal   (the suite's own)
#   T2 test_proposals_review.py::test_a_spend_proposals_why_holds_no_number             (the suite's own)
#   P1 the real extract_paper under a 0.001 USD cap: does it raise llm.BudgetExhausted, T1's and T2's stub?
#   P2 T1's assertions with the refusal raised by llm.call's reservation: a spend proposal kept?
#   1. the tree as it is;
#   2. a control: the same tree with one change, call_model letting llm.BudgetExhausted through
#      (extract.py:340), the way T1's and T2's stub assumes.
# A hollow test: T1 and T2 pass on both trees, P2 fails on the first and passes on the second.
# The worktree is removed and every bh_r_h9_03_* database dropped when it ends. Exits 0 either way.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
HERE=/home/user/openFermentUI/bughunt/repro/H9-03
TAG="$(date +%s)-$$"
BASE="$BH_WORK/H9-03"
WT="$BASE/wt-$TAG"
OUT="$BASE/out-$TAG"
CFG=bh_r_h9_03_cfg
PY="$BH_ROOT/core/.venv/bin/python"
T1=tests/test_writes.py::test_an_extraction_the_budget_refuses_becomes_a_spend_proposal
T2=tests/test_proposals_review.py::test_a_spend_proposals_why_holds_no_number
PROBE=tests/test_zz_h9_03_probe.py
P1=test_probe_extract_paper_raises_budget_exhausted_under_the_cap
P2=test_probe_the_spend_gate_through_the_real_extract_path

drop_ours() {
  local n
  for n in $(psql "$BH_SERVER/postgres" -AtqXc "SELECT datname FROM pg_database WHERE datname LIKE 'bh\_r\_h9\_03\_%'"); do
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
# The fixture files the tests read that git does not hold (made by the repository's scripts), copied, read only.
cp "$BH_ROOT"/core/tests/fixtures/{units,competence-unrated,competence,fields,lock-digests,resolvers}.json "$WT/core/tests/fixtures/"
cp "$HERE/test_zz_h9_03_probe.py" "$WT/core/$PROBE"
drop_ours
bh_db_fresh "$CFG" 2>/dev/null || verdict "a fresh database $CFG" "bh_db_fresh failed" NO-DEFECT
echo "databases: $CFG made fresh and migrated; each pytest session makes and drops its own bh_r_h9_03_t_* database"

echo "== the code the candidate names (2047f5a)"
grep -n 'raise llm.BudgetExhausted\|monkeypatch.setattr(extract, "extract_paper", broke)' "$WT/core/tests/test_writes.py" \
  | sed 's|^|   core/tests/test_writes.py:|'
awk 'NR>=73 && NR<=77 && /BudgetExhausted|extract_paper/ {print "   core/tests/test_proposals_review.py:" NR ":" $0}' \
  "$WT/core/tests/test_proposals_review.py"
grep -n '^class BudgetExhausted' "$WT/core/openferment_core/llm.py" | sed 's|^|   core/openferment_core/llm.py:|'
grep -n 'except llm.ModelUnavailable as e:\|raise ExtractUnavailable(f"{e}{spent}")' "$WT/core/openferment_core/extract.py" \
  | sed 's|^|   core/openferment_core/extract.py:|'
grep -n 'except llm.BudgetExhausted:' "$WT/core/openferment_core/tools/writes.py" | sed 's|^|   core/openferment_core/tools/writes.py:|'

# pytest in the worktree, keyless, one session; results as JUnit XML in $OUT/$1.xml, probes' notes in $OUT/$1.jsonl.
run_tests() {
  local name="$1"
  : > "$OUT/$name.jsonl"
  (cd "$WT/core" && bh_env PYTHONDONTWRITEBYTECODE=1 H9_03_OUT="$OUT/$name.jsonl" \
     OPENFERMENT_DATABASE_URL="$BH_SERVER/$CFG" OPENFERMENT_TEST_DATABASE_URL="$BH_SERVER/bh_r_h9_03_t" \
     "$PY" -m pytest "$T1" "$T2" "$PROBE" -q -p no:randomly -p no:cacheprovider --junitxml="$OUT/$name.xml" \
     < /dev/null > "$OUT/$name.log" 2>&1)
  echo "   pytest: $(tail -1 "$OUT/$name.log")"
}
# outcome <name> <test name>: passed, failed or missing.
outcome() {
  python3 - "$OUT/$1.xml" "$2" <<'EOF'
import sys, xml.etree.ElementTree as ET
try:
    root = ET.parse(sys.argv[1]).getroot()
except Exception:
    print("missing"); raise SystemExit
for tc in root.iter("testcase"):
    if tc.get("name") == sys.argv[2]:
        bad = any(c.tag in ("failure", "error") for c in tc)
        skipped = any(c.tag == "skipped" for c in tc)
        print("skipped" if skipped else "failed" if bad else "passed"); raise SystemExit
print("missing")
EOF
}
# said <name> <probe>: what that probe noted, in one line.
said() {
  python3 - "$OUT/$1.jsonl" "$2" <<'EOF'
import json, sys
for line in open(sys.argv[1], encoding="utf-8"):
    d = json.loads(line)
    if d.get("probe") != sys.argv[2]:
        continue
    if d["probe"] == "extract_paper":
        print(f"raised {d.get('raised')} (BudgetExhausted: {d.get('isBudgetExhausted')}; from {d.get('cause')}): "
              f"{d.get('words')!r}; module {d.get('module')}")
    else:
        print(f"error {d.get('error')!r} | summary {d.get('summary')} | proposals kept {d.get('proposals')}")
    raise SystemExit
print("(no note)")
EOF
}
report() {
  local name="$1"
  R_T1=$(outcome "$name" test_an_extraction_the_budget_refuses_becomes_a_spend_proposal)
  R_T2=$(outcome "$name" test_a_spend_proposals_why_holds_no_number)
  R_P1=$(outcome "$name" "$P1"); R_P2=$(outcome "$name" "$P2")
  echo "   T1 $R_T1 | T2 $R_T2 | P1 $R_P1 | P2 $R_P2"
  echo "   P1 extract_paper under the cap: $(said "$name" extract_paper)"
  echo "   P2 intake_write extract under the cap: $(said "$name" intake_write)"
}

# ── 1. the tree as it is ──
echo "== 1. the tree as it is (2047f5a)"
run_tests base
report base
A_T1=$R_T1; A_T2=$R_T2; A_P1=$R_P1; A_P2=$R_P2
MOD=$(python3 -c "import json,sys; print(next((json.loads(l).get('module','') for l in open(sys.argv[1]) if 'module' in l), ''))" "$OUT/base.jsonl")
case "$MOD" in "$WT"/*) ;; *) verdict "openferment_core imported from the worktree" "it came from '${MOD}'" NO-DEFECT;; esac

# ── 2. the control: call_model lets llm.BudgetExhausted through, as the stub assumes ──
echo "== 2. control: extract.call_model re-raises llm.BudgetExhausted before its ModelUnavailable branch"
python3 - "$WT/core/openferment_core/extract.py" <<'EOF' || verdict "the control change applied" "extract.py's ModelUnavailable branch was not found" NO-DEFECT
import sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
old = "    except llm.ModelUnavailable as e:\n        spent = f\" (${e.usage.costUsd:.4f} spent first)\""
assert s.count(old) == 1, s.count(old)
s = s.replace(old, "    except llm.BudgetExhausted:\n        raise\n" + old)
open(p, "w", encoding="utf-8").write(s)
EOF
echo "   $(git -C "$WT" diff --stat -- core/openferment_core | tail -1)"
run_tests control
report control
B_T1=$R_T1; B_T2=$R_T2; B_P1=$R_P1; B_P2=$R_P2

EXP="the spend gate's two tests (test_writes.py:360, test_proposals_review.py:73) fail on a tree whose real extraction path keeps no spend proposal when the daily cap refuses: they pass only where the budget refusal through extract_paper becomes a proposal, as P2 asks"
if [ "$A_T1" = passed ] && [ "$A_T2" = passed ] && [ "$A_P1" = failed ] && [ "$A_P2" = failed ] \
   && [ "$B_T1" = passed ] && [ "$B_T2" = passed ] && [ "$B_P1" = passed ] && [ "$B_P2" = passed ]; then
  verdict "$EXP" "on 2047f5a T1 and T2 pass while the real extract_paper under the cap raises ExtractUnavailable (from BudgetExhausted) and intake_write extract answers an error with no proposal kept (P1, P2 fail); with call_model letting BudgetExhausted through, P1 and P2 pass and T1 and T2 pass alike, so their outcome does not depend on whether the gate works" DEFECT
else
  verdict "$EXP" "tree as is: T1 $A_T1, T2 $A_T2, P1 $A_P1, P2 $A_P2; control: T1 $B_T1, T2 $B_T2, P1 $B_P1, P2 $B_P2 (see the logs)" NO-DEFECT
fi
