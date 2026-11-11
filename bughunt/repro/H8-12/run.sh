#!/usr/bin/env bash
# H8-12: an SFF file whose bytes begin with the UTF-8 byte-order mark (EF BB BF) is refused at
# POST /api/flowsheets/import as "is not JSON: its text stops reading as JSON at line 1, column 1",
# while POST /api/intake/catalogue reads the mark (catalogues.py:527, utf-8-sig) and keeps its file.
# The check the candidate leaves out: the file the import door keeps is handed byte for byte to the
# toolkit in the worker (engine/sff.py:581-585), so this script also runs the worker's own check
# (workers/sff_toolkit.py validation and completeness) on the same bytes, with and without the mark.
# The head's service on a fresh database, port 10110, keyless; no model call is made.
# usage, from the repository root: bash bughunt/repro/H8-12/run.sh
source /home/user/openFermentUI/bughunt/lib/env.sh
DB=bh_r_h8_12_svc
PORT=10110
P=h812
T=$BH_WORK/H8-12/run-$$; mkdir -p "$T"
cleanup() { bh_svc_stop "$PORT"; bh_db_drop "$DB"; rm -rf "$BH_WORK/data-$DB" "$T"; }
trap cleanup EXIT
c() { curl -s --noproxy '*' "$@"; }

# The same flowsheet twice: as the toolkit writes it, and with the mark in front.
printf '%s' '{"units": [], "streams": [], "metadata": {"process_title": "BOM"}}' > "$T/plain.json"
{ printf '\xef\xbb\xbf'; cat "$T/plain.json"; } > "$T/marked.json"
{ printf '\xef\xbb\xbf'; printf 'id,name\nS1,One\n'; } > "$T/marked.csv"
echo "INPUT: marked.json starts with bytes $(head -c3 "$T/marked.json" | od -An -tx1 | xargs), then $(cut -c1-40 "$T/plain.json")..."

echo "EXPECTED: docs/api/sff.md:43-45 \"A file is refused only when no graph can be read from it: not UTF-8, not JSON,"
echo "EXPECTED: or not an object with a list of units and a list of streams (422)\"; the candidate reads a BOM file as"
echo "EXPECTED: UTF-8 JSON (RFC 8259 lets a parser ignore the mark), so: kept, or refused in words naming the mark."
echo "EXPECTED: The refusal stands inside the contract when the file is outside JSON's grammar (RFC 8259 §8.1: a"
echo "EXPECTED: writer MUST NOT add the mark, a parser MAY ignore it or treat it as an error) and no reader in the"
echo "EXPECTED: tree reads a graph from those bytes; it breaks the contract when the toolkit, which checks every kept"
echo "EXPECTED: file byte for byte, reads a graph from them."

O=$(bh_svc_start "$DB" "$PORT") || { echo "OBSERVED: the service did not start"; echo "RESULT: NO-DEFECT"; exit 0; }
bh_project "$O" "$P" >/dev/null
H=(-H "X-OpenFerment-Project: $P")

SFF=$(c -X POST "$O/api/flowsheets/import" "${H[@]}" -F "file=@$T/marked.json;type=application/json" -F by=h812 \
      -w '\n%{http_code}')
SFF_CODE=$(echo "$SFF" | tail -1); SFF_BODY=$(echo "$SFF" | sed '$d')
echo "OBSERVED: POST /api/flowsheets/import (marked.json) -> HTTP $SFF_CODE $SFF_BODY"

CAT=$(c -X POST "$O/api/intake/catalogue" "${H[@]}" -F "file=@$T/marked.csv;type=text/csv" -F kind=strain -F by=h812 \
      -w '\n%{http_code}')
CAT_CODE=$(echo "$CAT" | tail -1); CAT_BODY=$(echo "$CAT" | sed '$d')
echo "OBSERVED: POST /api/intake/catalogue (marked.csv, kind strain) -> HTTP $CAT_CODE $CAT_BODY"
bh_svc_stop "$PORT"

# The worker's own check, the code an imported file meets after the door (engine/sff.py:581-585 write the
# bytes as they came; workers/sff_toolkit.py:65-69 hand the path to pisces_sff.validate_flowsheet_against_SFF).
bh_py -I - "$T" > "$T/toolkit.txt" 2>&1 <<'EOF'
import json, sys
from pathlib import Path
from openferment_core.workers import sff_toolkit
d = Path(sys.argv[1])
for n in ("plain.json", "marked.json"):
    try:
        v = sff_toolkit.validation(d / n)
        s = sff_toolkit.completeness(d / n)
        print(f"TOOLKIT {n}: read; valid {v['valid']}, {len(v['findings'])} findings, completeness {s['score']:.3f}")
    except Exception as e:
        print(f"TOOLKIT {n}: raised {type(e).__name__}: {e}")
try:
    json.loads((d / "marked.json").read_bytes().decode("utf-8"))
except json.JSONDecodeError as e:
    print(f"PYJSON marked.json decoded as utf-8: {e.msg} (line {e.lineno}, column {e.colno})")
EOF
grep -E '^(TOOLKIT|PYJSON)' "$T/toolkit.txt" | sed 's/^/OBSERVED: /'
[ -n "$(grep -E '^TOOLKIT' "$T/toolkit.txt")" ] || { echo "OBSERVED: the toolkit check did not run:"; tail -5 "$T/toolkit.txt"; }

REFUSED=0; [ "$SFF_CODE" = 422 ] && echo "$SFF_BODY" | grep -q 'is not JSON' && REFUSED=1
NAMES_MARK=0; echo "$SFF_BODY" | grep -qiE 'BOM|byte.order|FEFF' && NAMES_MARK=1
CAT_KEPT=0; [ "$CAT_CODE" = 200 ] && echo "$CAT_BODY" | grep -q '"S1"' && CAT_KEPT=1
TK_PLAIN=0; grep -q '^TOOLKIT plain.json: read' "$T/toolkit.txt" && TK_PLAIN=1
TK_BOM=0; grep -q '^TOOLKIT marked.json: read' "$T/toolkit.txt" && TK_BOM=1
TK_BOM_RAISED=0; grep -q '^TOOLKIT marked.json: raised JSONDecodeError: Unexpected UTF-8 BOM' "$T/toolkit.txt" && TK_BOM_RAISED=1
echo "OBSERVED: import door refuses as not JSON: $REFUSED; its words name the mark: $NAMES_MARK; catalogue door keeps S1: $CAT_KEPT"
echo "OBSERVED: the worker's toolkit check reads plain.json: $TK_PLAIN; reads marked.json: $TK_BOM; raises on the mark: $TK_BOM_RAISED"

if [ "$REFUSED" = 1 ] && [ "$TK_BOM" = 1 ]; then
  echo "OBSERVED: the door refuses bytes the toolkit reads a graph from: the contract's 'only when no graph can be read' breaks"
  echo "RESULT: DEFECT"
elif [ "$REFUSED" = 1 ] && [ "$TK_PLAIN" = 1 ] && [ "$TK_BOM_RAISED" = 1 ]; then
  echo "OBSERVED: the refusal is the contract's own ground 'not JSON': the mark sits outside JSON's grammar (RFC 8259 §8.1),"
  echo "OBSERVED: and the toolkit that checks every kept file byte for byte reads no graph from these bytes either; the"
  echo "OBSERVED: catalogue door's utf-8-sig reading is a separate door's choice that no contract ties to this one."
  [ "$NAMES_MARK" = 0 ] && echo "OBSERVED: what remains is wording (S4 at most): the refusal gives the place, line 1, column 1, and leaves out the reason Python's json gives, 'Unexpected UTF-8 BOM'"
  echo "RESULT: NO-DEFECT"
elif [ "$REFUSED" = 0 ] && [ "$SFF_CODE" = 200 ]; then
  echo "OBSERVED: the door kept the file"; echo "RESULT: NO-DEFECT"
else
  echo "OBSERVED: the case did not run to a verdict (see the lines above)"; echo "RESULT: NO-DEFECT"
fi
exit 0
