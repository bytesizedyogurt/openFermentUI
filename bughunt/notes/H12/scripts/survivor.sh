#!/usr/bin/env bash
# survivor.sh ID [WT]: show that H12's mutation ID survives the tests named for it. In a worktree of 2047f5a
# (made under $BH_WORK/H12/repro-wt when none is given and none stands there), with the conform scratch prefix
# renamed so every database made is bh_h12_* (mutations/BASE-scratch-name.patch; the one test that asserts the
# old prefix is left out), apply mutations/ID.patch, run the tests recorded for ID in mutations*.json, keyless,
# on test databases bh_h12_r_*, and reverse the patch. A green run is the finding: the break goes unseen.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
ID=${1:?mutation id}
N=/home/user/openFermentUI/bughunt/notes/H12
WT=${2:-$BH_WORK/H12/repro-wt}
if [ ! -d "$WT" ]; then
  git -C "$BH_ROOT" worktree add --detach "$WT" 2047f5a >/dev/null 2>&1 || exit 2
  (cd "$WT" && git apply "$N/mutations/BASE-scratch-name.patch") || exit 2
  cp "$BH_ROOT"/core/tests/fixtures/{units,competence-unrated,competence,fields,lock-digests,resolvers}.json "$WT/core/tests/fixtures/"
fi
read -r -a ARGS < <(python3 - "$ID" "$N" <<'EOF'
import glob, json, sys
id_, notes = sys.argv[1], sys.argv[2]
for f in sorted(glob.glob(f"{notes}/mutations*.json")):
    for m in json.load(open(f)):
        if m["id"] == id_:
            tests = list(m["tests"])
            if "tests/test_engines.py" in tests and "-k" not in tests:
                tests += ["-k", "not sigterm_ends_the_command"]
            print(" ".join(t.replace(" ", "\x01") for t in tests))
            raise SystemExit(0)
raise SystemExit(f"no mutation {id_}")
EOF
)
ARGS=("${ARGS[@]//$'\x01'/ }")
PY="$WT/core/.venv/bin/python"; [ -x "$PY" ] || PY="$BH_ROOT/core/.venv/bin/python"
(cd "$WT" && git apply "$N/mutations/$ID.patch") || { echo "the patch for $ID does not apply"; exit 2; }
echo "== $ID applied: $(cd "$WT" && git diff --stat | tail -1)"
(cd "$WT/core" && bh_env PYTHONPATH="$WT/core" OPENFERMENT_TEST_DATABASE_URL="$BH_SERVER/bh_h12_r" \
   "$PY" -m pytest "${ARGS[@]}" -q -p no:randomly -p no:cacheprovider -m "not live and not sim and not slow and not lit" 2>&1 | tail -2)
(cd "$WT" && git apply -R "$N/mutations/$ID.patch")
echo "== $ID reversed"
