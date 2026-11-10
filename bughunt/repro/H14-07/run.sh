#!/usr/bin/env bash
# H14-07: the bench's capture box (src/engine/capture.ts) strips every comma before it reads a number, so a
# reading said with a decimal comma, "titre came in at 7,4 g/L", is filed as a measurement of 74 g/L.
# The matcher is a pure function of the browser bundle, so this needs no database, no service and no worktree:
# tsx runs bughunt/repro/H14-07/capture.ts over the tree's own src/engine/capture.ts (read-only), and grep shows
# the path from the matcher to the filed entry and the read-back, and that the built app in dist/ carries the
# same comma strip. Keyless, no network. tsx's cache goes to a scratch TMPDIR this script removes.
# usage, from the repository root: bash bughunt/repro/H14-07/run.sh
source /home/user/openFermentUI/bughunt/lib/env.sh
T="$BH_WORK/H14-07/run"
cleanup() { rm -rf "${T:?}"; rmdir "$BH_WORK/H14-07" 2>/dev/null; }
trap cleanup EXIT
rm -rf "${T:?}"; mkdir -p "$T/tmp"
cd "$BH_ROOT" || { echo "RESULT: NO-DEFECT (no repository at $BH_ROOT)"; exit 0; }

echo "EXPECTED: capture.ts:9-13 keeps a doubtful line as words (\"when in doubt this returns null and the text is kept"
echo "EXPECTED: verbatim as an Observation\"), so \"titre came in at 7,4 g/L\" is kept as an observation, or filed as 7.4 g/L;"
echo "EXPECTED: no reading of \"7,4\" (a decimal comma, or a thousands group, which holds three digits) is 74."

# 1. The path, by grep over the tree: the comma strip, the number regex, the panel's preview filed by capture(),
#    the entry's value taken from the match, and the read-back's two lines.
echo "step 1: the path from the capture box to the filed entry"
grep -n "replace(/\[,\]/g, '')" src/engine/capture.ts | sed 's/^/  src\/engine\/capture.ts:/'
grep -n 'const numbers = ' src/engine/capture.ts | sed 's/^/  src\/engine\/capture.ts:/'
grep -n 'matchToSchema(text, schema)\|capture(deposition.id, stepId, raw, preview)' src/components/DepositionPanel.tsx \
  | sed 's/^/  src\/components\/DepositionPanel.tsx:/'
grep -n 'value: match.value,' src/store.ts | sed 's/^/  src\/store.ts:/'
grep -n '{e.value} {e.unit}\|you said: &ldquo;{e.raw}&rdquo;' src/components/DepositionPanel.tsx \
  | sed 's/^/  src\/components\/DepositionPanel.tsx:/'
strip=$(grep -c "replace(/\[,\]/g, '')" src/engine/capture.ts)
wired=$(grep -c 'capture(deposition.id, stepId, raw, preview)' src/components/DepositionPanel.tsx)
filed=$(grep -c 'value: match.value,' src/store.ts)
built=$(grep -l 'toLowerCase().replace(/\[,\]/g,"").replace(/\\s+/g," ").trim()' dist/assets/*.js 2>/dev/null | head -1)
echo "  the built app's bundle with the same normalise: ${built:-none}"

# 2. The matcher over four lines an operator might type, with the read-back text the panel shows.
echo "step 2: matchToSchema and readBackText over a g/L measure labelled \"Ethanol titre\" (a runbook's harvest measure)"
TMPDIR="$T/tmp" node_modules/.bin/tsx bughunt/repro/H14-07/capture.ts > "$T/out.jsonl" 2> "$T/err.txt"
[ -s "$T/out.jsonl" ] || { echo "OBSERVED: tsx gave no output: $(head -c 400 "$T/err.txt")"; echo "RESULT: NO-DEFECT"; exit 0; }
sed 's/^/  /' "$T/out.jsonl"
read -r dot comma zero thou < <(python3 - "$T/out.jsonl" <<'PY'
import json, sys
v = []
for line in open(sys.argv[1]):
    m = json.loads(line)["match"]
    v.append("null" if m is None else repr(m["value"]))
print(*v)
PY
)

echo "OBSERVED: \"titre came in at 7.4 g/L\" files as $dot g/L (the control: a decimal point reads right)"
echo "OBSERVED: \"titre came in at 7,4 g/L\" files as $comma g/L; the read-back beat shows \"Ethanol titre = $comma g/L\" over"
echo "OBSERVED: \"you said: 7,4 g/L\", and \"That is right\" keeps it as the reading a scenario's measurement origin names"
echo "OBSERVED: \"titre came in at 0,74 g/L\" files as $zero g/L; \"titre came in at 1,250 g/L\" files as $thou g/L"
echo "OBSERVED: the comma strip at capture.ts:28 ($strip), the panel files its preview ($wired), the entry takes match.value ($filed)"

if [ "$dot" = "7.4" ] && [ "$comma" = "74" ] && [ "$strip" -ge 1 ] && [ "$wired" -ge 1 ] && [ "$filed" -ge 1 ]; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
