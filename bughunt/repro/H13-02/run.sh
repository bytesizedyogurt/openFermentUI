#!/usr/bin/env bash
# H13-02: `pnpm lit:report` erases the hand-written sections of the committed retrieval report.
# A scratch worktree at 2047f5a holds the committed pair docs/reports/literature-retrieval.{md,json}.
#   1. the contract as the tree holds it: the report's line 1 and line 91, CLAUDE.md:106, and the sections
#      report.render() writes for a project's part.
#   2. no database: report.write() of the committed JSON's own `ethanol` part (the step
#      `pnpm lit:report --project ethanol ... --render` ends with) over a copy of the committed pair; the
#      copy is diffed against the committed file.
#   3. `pnpm lit:report` whole (literature_live.main(["report"]), the kit's demo, offline, keyless, no model),
#      its scratch database a fresh bh_r_h13_02_demo; the worktree's file is diffed against the commit.
# The main checkout's pair is hashed before and after: nothing here writes it.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
cd "$BH_ROOT" || exit 0
SHA=2047f5a; DB=bh_r_h13_02_demo
HERE="$BH_ROOT/bughunt/repro/H13-02"; OUT="$BH_WORK/H13-02"; W="$OUT/wt"; PY="$BH_ROOT/core/.venv/bin/python"
REL=docs/reports/literature-retrieval
S1="### What this run measured"; S2="### What waits on the account"
COMMENT="<!-- Added by hand at alpha 2.2 F.5"
sums() { sha256sum "$BH_ROOT/$REL.md" "$BH_ROOT/$REL.json" | sha256sum | cut -c1-16; }
cleanup() {
  bh_db_drop "$DB"
  git -C "$BH_ROOT" worktree remove --force "$W" >/dev/null 2>&1; rm -rf "$OUT"; git -C "$BH_ROOT" worktree prune
}
trap cleanup EXIT
MAIN_BEFORE=$(sums)
cleanup; mkdir -p "$OUT/render" "$OUT/data"
git -C "$BH_ROOT" worktree add --detach "$W" "$SHA" >/dev/null 2>&1 || { echo "OBSERVED: no worktree"; echo "RESULT: NO-DEFECT"; exit 0; }
drive() {
  (cd "$W/core" && bh_env PYTHONPATH="$W/core" HF_HUB_OFFLINE=1 OPENFERMENT_DATA_DIR="$OUT/data" \
     OPENFERMENT_TEST_DATABASE_URL="$BH_SERVER/$DB" "$PY" "$HERE/drive.py" "$@")
}
has() { grep -cF -- "$1" "$2"; }
echo "worktree: $W at $(git -C "$W" rev-parse --short HEAD)"
drive check "$W" | sed 's/^/   /' || { echo "OBSERVED: the worktree's package is not the one imported"; echo "RESULT: NO-DEFECT"; exit 0; }

echo; echo "== 1. the contract and the generator, as 2047f5a holds them"
C="$W/$REL.md"
sed -n 1p "$C" | sed "s|^|   $REL.md:1: |"
sed -n 91p "$C" | sed "s|^|   $REL.md:91: |"
sed -n 106p "$W/CLAUDE.md" | cut -c1-120 | sed 's|^|   CLAUDE.md:106: |'
LINES_COMMITTED=$(grep -c '' "$C")
echo "   the committed file: $LINES_COMMITTED lines; its '$S1' at line $(grep -nF -- "$S1" "$C" | cut -d: -f1), '$S2' at line $(grep -nF -- "$S2" "$C" | cut -d: -f1)"
echo "   the sections report.render() writes (core/openferment_core/literature/report.py:732-822):"
grep -n '"### ' "$W/core/openferment_core/literature/report.py" | sed -E 's/^([0-9]+):.*"(### [^"]*)".*/      report.py:\1 \2/'
GEN_S1=$(grep -cF -- "${S1#\#\#\# }" "$W/core/openferment_core/literature/report.py")
GEN_S2=$(grep -cF -- "${S2#\#\#\# }" "$W/core/openferment_core/literature/report.py")
echo "   lines of report.py naming 'What this run measured': $GEN_S1; naming 'What waits on the account': $GEN_S2"

echo; echo "== 2. a project render (report.write of the committed JSON's own part), no database"
R="$OUT/render/literature-retrieval"
cp "$W/$REL.md" "$R.md"; cp "$W/$REL.json" "$R.json"
drive render "$W" "$R" 2>&1 | sed 's/^/   /'
diff "$C" "$R.md" > "$OUT/render.diff"
R_DEL=$(grep -c '^< ' "$OUT/render.diff"); R_ADD=$(grep -c '^> ' "$OUT/render.diff")
R_S1=$(has "$S1" "$R.md"); R_S2=$(has "$S2" "$R.md"); R_LINES=$(grep -c '' "$R.md")
JSON_SAME=$(cmp -s "$W/$REL.json" "$R.json" && echo yes || echo no)
echo "   the rendered file: $R_LINES lines; against the committed file $R_DEL lines gone, $R_ADD added; the JSON unchanged: $JSON_SAME"
echo "   diff hunks: $(grep -E '^[0-9]' "$OUT/render.diff" | tr '\n' ' ')"
echo "   '$S1' in it: $R_S1; '$S2' in it: $R_S2"

echo; echo "== 3. \`pnpm lit:report\` (the kit's demo, offline, keyless), its database a fresh $DB"
bh_db_fresh "$DB" || echo "   bh_db_fresh failed"
T0=$(date +%s)
drive demo "$W" "$BH_SERVER/$DB" > "$OUT/demo.log" 2>&1; DEMO_RC=$?
echo "   exit $DEMO_RC in $(( $(date +%s) - T0 )) s; its last line: $(grep -v '^$' "$OUT/demo.log" | tail -1)"
[ "$DEMO_RC" = 0 ] || tail -15 "$OUT/demo.log" | sed 's/^/   | /'
D_LINES=$(grep -c '' "$C")
D_S1=$(has "$S1" "$C"); D_S2=$(has "$S2" "$C"); D_C=$(has "$COMMENT" "$C")
echo "   the report: $LINES_COMMITTED lines before, $D_LINES after"
git -C "$W" diff --stat -- docs/reports/ | sed 's/^/   /'
echo "   lines removed from the Markdown, beside the date line:"
git -C "$W" diff -U0 -- "$REL.md" | grep -E '^-[^-]' | grep -v "as openFerment runs the kit" | cut -c1-110 | sed 's/^/      /' | head -40
echo "   lines added to the Markdown: $(git -C "$W" diff -U0 -- "$REL.md" | grep -E '^\+[^+]' | cut -c1-110)"
echo "   fields that moved in the JSON: $(git -C "$W" diff -U0 -- "$REL.json" | grep -E '^\+[^+]' | sed -E 's/^\+ *"([^"]+)".*/\1/' | tr '\n' ' ')"
echo "   '$S1' after: $D_S1; '$S2' after: $D_S2; the hand's comment after: $D_C"

MAIN_AFTER=$(sums)
echo; echo "the main checkout's report pair: $MAIN_BEFORE before, $MAIN_AFTER after"

echo
echo "EXPECTED: by $REL.md:1 (\"Written by \`pnpm lit:report\` ...; regenerate, do not edit\") the committed file is its generator's output, so regenerating it moves only what the generator owns (the date and the commit) and keeps every section; by line 91 a project render (\"--render writes this project's part whole ..., these two sections with it\") writes '$S1' and '$S2'"
echo "OBSERVED: the committed file holds $LINES_COMMITTED lines, $R_DEL of them past what the generator writes from the committed JSON (a project render of its own part: $R_DEL gone, $R_ADD added, '$S1' $R_S1, '$S2' $R_S2; report.py names neither section: $GEN_S1, $GEN_S2); \`pnpm lit:report\` exits $DEMO_RC and leaves $D_LINES lines, '$S1' $D_S1, '$S2' $D_S2, the hand's comment $D_C"
if [ "$DEMO_RC" = 0 ] && [ "$D_S1" = 0 ] && [ "$D_S2" = 0 ] && [ "$D_C" = 0 ] && [ "$D_LINES" -lt "$LINES_COMMITTED" ] \
   && [ "$R_S1" = 0 ] && [ "$R_S2" = 0 ] && [ "$R_ADD" = 0 ] && [ "$R_DEL" -gt 0 ] && [ "$GEN_S1" = 0 ] && [ "$GEN_S2" = 0 ] \
   && [ "$MAIN_BEFORE" = "$MAIN_AFTER" ]; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
