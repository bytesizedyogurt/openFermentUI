#!/usr/bin/env bash
# R1-04: two rows of docs/PROGRESS.md's Departures table disagree on whether the browser keeps the lessons
# finished here. The stage 2 row (line 543) names three preferences, the third "the lessons finished here";
# the E.12 row of the same table (line 502) says "The Durable snapshot keeps no lesson", and the tree at
# 2047f5a writes no lesson into the snapshot.
# bash bughunt/repro/R1-04/run.sh (from the repository root). Keyless, no model call, read-only.
# A static defect: it needs no database and no service, so it makes neither. Every file is read from the
# commit with git show into a temporary directory under $BH_WORK/R1-04/, removed at the end.
#   1. docs/PROGRESS.md at 2047f5a: the stage 2 row with its section, the E.12 row of the same table;
#   2. docs/decisions/ADR-014-durable-write-queue.md at 2047f5a: its opening line on the preferences and its
#      E.12 note;
#   3. the tree at 2047f5a: the keys src/store.ts's snapshotOf writes (the whole object flush() puts in
#      IndexedDB), read with the TypeScript compiler's parser (snapshot_keys.mjs), the DurableSnapshot member
#      learnProgress and its doc comment, and every line of src/ and scripts/ that names learnProgress or
#      completeLesson.
# Prints EXPECTED:, OBSERVED: and one RESULT: line; exits 0 either way.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
C=2047f5a
HERE="$BH_ROOT/bughunt/repro/R1-04"
TMP="$BH_WORK/R1-04/tmp-$$"
cleanup() { rm -rf "$TMP"; rmdir "$BH_WORK/R1-04" 2>/dev/null; true; }
trap cleanup EXIT
nodefect() { echo "OBSERVED: $1"; echo "RESULT: NO-DEFECT"; exit 0; }
mkdir -p "$TMP"
cd "$BH_ROOT" || nodefect "no repository at $BH_ROOT"
for f in docs/PROGRESS.md docs/decisions/ADR-014-durable-write-queue.md src/store.ts src/lib/durable.ts; do
  git show "$C:$f" > "$TMP/$(basename "$f")" || nodefect "cannot read $f at $C"
done
echo "== 0. the checkout against $C (these four files): $(git diff --quiet "$C" -- docs/PROGRESS.md \
  docs/decisions/ADR-014-durable-write-queue.md src/store.ts src/lib/durable.ts && echo identical || echo differs)"
P="$TMP/PROGRESS.md"
cell() { sed -n "${1}p" "$P" | awk -F'|' -v c="$2" '{gsub(/^ +| +$/,"",$c); print $c}'; }
section() { awk -v n="$1" 'NR<=n && /^## /{s=$0} NR==n{print s; exit}' "$P"; }

# ── 1. the two rows ─────────────────────────────────────────────────────
OLD="three preferences, who is deciding, who is acting in Guild, and the lessons finished here"
NEW="The Durable snapshot keeps no lesson"
echo "== 1. docs/PROGRESS.md at $C"
R2=$(grep -n -F "$OLD" "$P" | head -1 | cut -d: -f1)
[ -n "$R2" ] || nodefect "no line of docs/PROGRESS.md at $C says: $OLD"
R12=$(grep -n -F "| $NEW" "$P" | head -1 | cut -d: -f1)
[ -n "$R12" ] || nodefect "no row of docs/PROGRESS.md at $C opens its Departure with: $NEW"
S2=$(section "$R2"); S12=$(section "$R12")
W2=$(cell "$R2" 2); W12=$(cell "$R12" 2)
LATER=$(cell "$R2" 3 | grep -o -E "E\.12|ADR-018|until alpha 2\.2|since alpha 2\.2" | sort -u | tr '\n' ' ')
echo "   line $R2, under \"$S2\", row \"$W2\":"
echo "     $(sed -n "${R2}p" "$P" | grep -o "The browser keeps an outbox[^|]*")"
echo "     later steps this row names (E.12, ADR-018, since/until alpha 2.2): ${LATER:-none}"
echo "   line $R12, under \"$S12\", row \"$W12\":"
echo "     $(sed -n "${R12}p" "$P" | grep -o "$NEW[^:]*"): the modules slice, \`learnProgress\` and \`completeLesson\` leave the store ..."
echo "     $(sed -n "${R12}p" "$P" | grep -o "a snapshot's older \`learnProgress\` loads, and the next save leaves it out[^|]*")"

# ── 2. ADR-014 at the same commit ───────────────────────────────────────
A="$TMP/ADR-014-durable-write-queue.md"
echo "== 2. docs/decisions/ADR-014-durable-write-queue.md at $C"
A14=$(grep -n -F "until alpha 2.2 E.12 the lessons finished here" "$A" | cut -d: -f1)
echo "   line ${A14:-none}: $(sed -n "$((A14-1)),${A14}p" "$A" | tr '\n' ' ' | grep -o "besides the preferences ([^)]*)")"
ANOTE=$(grep -n -F "The snapshot keeps no lesson" "$A" | cut -d: -f1)
echo "   line ${ANOTE:-none}: The snapshot keeps no lesson. ..."
APREF=$(grep -n -F "The preferences the snapshot keeps are" "$A" | cut -d: -f1)
echo "   lines ${APREF:-none}-$((APREF+1)): $(sed -n "${APREF},$((APREF+1))p" "$A" | tr '\n' ' ' | grep -o "The preferences the snapshot keeps are[^.]*\.")"

# ── 3. what the tree writes ─────────────────────────────────────────────
echo "== 3. the tree at $C"
node "$HERE/snapshot_keys.mjs" "$TMP/store.ts" "$TMP/durable.ts" > "$TMP/keys.txt" 2>&1
grep -q '^WRITES ' "$TMP/keys.txt" || nodefect "the key reader found no snapshotOf return: $(head -3 "$TMP/keys.txt")"
TOP=$(grep '^WRITES ' "$TMP/keys.txt" | grep -v '\[legacy rows\]' | sed 's/^WRITES //' | grep -v '^guild\.ledger' | tr '\n' ' ')
LEG=$(grep '^WRITES .*\[legacy rows\]' "$TMP/keys.txt" | sed 's/^WRITES //; s/ \[legacy rows\]//' | tr '\n' ' ')
LESSONKEYS=$(grep '^WRITES ' "$TMP/keys.txt" | grep -i -c -E "lesson|learn")
echo "   src/store.ts snapshotOf writes: $TOP"
echo "     and, while a pre-2.0 snapshot's rows wait for a project: $LEG"
echo "     keys naming a lesson or learning: $LESSONKEYS"
FIELD=$(grep '^FIELD learnProgress ' "$TMP/keys.txt" | awk '{print $3}')
DOC=$(grep '^DOC learnProgress ' "$TMP/keys.txt" | sed 's/^DOC learnProgress //')
LINE=$(grep -n "learnProgress?:" "$TMP/durable.ts" | cut -d: -f1)
echo "   src/lib/durable.ts:$LINE DurableSnapshot.learnProgress, marked ${FIELD:-absent}: \"$DOC\""
git grep -n -E "learnProgress|completeLesson" "$C" -- src scripts > "$TMP/readers.txt"
NREAD=$(wc -l < "$TMP/readers.txt" | tr -d ' ')
# Each line is one of two: the legacy member's type, or check:guild's check that the store holds no lesson.
NTYPE=$(grep -c -F "src/lib/durable.ts:$LINE:  learnProgress?:" "$TMP/readers.txt")
NABS=$(grep -c -F "!('learnProgress' in s()) && !('completeLesson' in s())" "$TMP/readers.txt")
NOTHER=$((NREAD - NTYPE - NABS))
echo "   lines of src/ and scripts/ at $C naming learnProgress or completeLesson: $NREAD"
echo "     the legacy member's type: $NTYPE; check:guild's check that the store keeps no lesson: $NABS; any other reader: $NOTHER"
sed 's/^/     /' "$TMP/readers.txt"

echo "EXPECTED: one account in the Departures table of what the browser's Durable snapshot keeps, true of the tree at $C:"
echo "EXPECTED: two preferences (who is deciding, reviewerName; who is acting in Guild, guild.actingId) and the unacknowledged writes,"
echo "EXPECTED: with no lesson, as row \"$W12\" (line $R12) and ADR-014:${A14:-14} (\"until alpha 2.2 E.12 the lessons finished here\") say"
echo "OBSERVED: line $R2 (\"$W2\") says the browser keeps \"$OLD\" and names no later step (${LATER:-none});"
echo "OBSERVED: line $R12 of the same table says \"$NEW\"; snapshotOf writes $LESSONKEYS key(s) naming a lesson;"
echo "OBSERVED: learnProgress is a ${FIELD:-absent} member of DurableSnapshot (\"nothing reads this, and the next save leaves it out\"); of the $NREAD line(s) of src/ and scripts/ naming it, $NTYPE is its type, $NABS is check:guild's check that the store keeps no lesson, $NOTHER read it"
if [ "$S2" = "## Departures from the execution prompt" ] && [ "$S12" = "$S2" ] && [ -z "$LATER" ] \
   && [ "$LESSONKEYS" = 0 ] && [ "$FIELD" = LEGACY ] && [ "$NTYPE" = 1 ] && [ "$NOTHER" = 0 ]; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
