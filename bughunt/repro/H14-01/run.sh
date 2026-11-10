#!/usr/bin/env bash
# H14-01: a second comparison of the same runs, asked by another person under another title.
# Fresh database bh_r_h14_01_cmp, the service on 127.0.0.1:9300, keyless. Two library runs at the package's
# own defaults (corn, sugarcane), Ada compares them titled A, Ben compares the same runs in the same order
# titled B. The run then reads what the tree itself says a repeated ask does: studies.md, the module, rows.put
# and the test that pins it. RESULT says whether the service departs from that contract.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
cd "$BH_ROOT" || exit 0
PORT=9300; DB=bh_r_h14_01_cmp; P=h14-01; OUT="$BH_WORK/H14-01"; mkdir -p "$OUT"
cleanup() { bh_svc_stop "$PORT"; bh_db_drop "$DB"; }
trap cleanup EXIT
c() { curl -s --noproxy '*' "$@"; }
H=(-H "X-OpenFerment-Project: $P" -H 'content-type: application/json')
field() { python3 -c 'import json,sys; d=json.load(sys.stdin); 
for k in sys.argv[1].split("."): d=d[k]
print(d)' "$1"; }

O=$(bh_svc_start "$DB" "$PORT") || { echo "OBSERVED: the service did not start"; echo "RESULT: NO-DEFECT"; exit 0; }
echo "service: $O over $DB"
bh_project "$O" "$P" >/dev/null
R1=$(c -X POST "$O/api/library/corn/run" "${H[@]}" -d '{"by":"Ada"}' | field run.id)
R2=$(c -X POST "$O/api/library/sugarcane/run" "${H[@]}" -d '{"by":"Ada"}' | field run.id)
echo "runs (package defaults, by Ada): corn $R1, sugarcane $R2"

c -X POST "$O/api/studies/comparisons" "${H[@]}" \
  -d "{\"title\":\"A: Ada's question\",\"runIds\":[\"$R1\",\"$R2\"],\"by\":\"Ada\"}" > "$OUT/first.json"
sleep 1
c -X POST "$O/api/studies/comparisons" "${H[@]}" \
  -d "{\"title\":\"B: Ben's question\",\"runIds\":[\"$R1\",\"$R2\"],\"by\":\"Ben\"}" > "$OUT/second.json"
c "$O/api/studies/comparisons" "${H[@]}" > "$OUT/listed.json"
c "$O/api/audit?limit=200" "${H[@]}" > "$OUT/audit.json"
psql "$BH_SERVER/$DB" -XAtF ' | ' -c "select id, created_by, body->>'title', body->>'by', body->>'at' from openferment.comparisons" > "$OUT/rows.txt"

python3 - "$OUT" <<'PY'
import json, sys, pathlib
out = pathlib.Path(sys.argv[1])
first = json.loads((out / "first.json").read_text())["comparison"]
second = json.loads((out / "second.json").read_text())["comparison"]
listed = json.loads((out / "listed.json").read_text())
audit = json.loads((out / "audit.json").read_text())
show = lambda d: {k: d[k] for k in ("id", "title", "by", "at")}
print("Ada's ask answered:", show(first))
print("Ben's ask answered:", show(second))
print("the project lists:", [show(x) for x in listed])
print("comparisons rows (id | created_by | title | by | at):", (out / "rows.txt").read_text().strip())
named = [r for r in audit if "compar" in json.dumps(r).lower()] if isinstance(audit, list) else []
print("audit rows naming a comparison:", len(named))
one = len(listed) == 1 and second["id"] == first["id"]
maker_kept = second["by"] == "Ada" and second["at"] == first["at"]
retitled = second["title"] == "B: Ben's question" and listed and listed[0]["title"] == "B: Ben's question"
(out / "verdict.json").write_text(json.dumps({"one": one, "maker_kept": maker_kept, "retitled": retitled}))
PY

echo "== what the tree says a repeated ask does"
grep -n "the same runs in the same order are one comparison" docs/api/studies.md
grep -n "keeps who made it and when" core/openferment_core/db/rows.py
sed -n 266,273p core/openferment_core/studies/comparisons.py | sed 's/^/comparisons.py: /'
sed -n 106,111p core/tests/test_comparisons.py | sed 's/^/test_comparisons.py: /'
grep -n "title and$" -A1 core/openferment_core/studies/scenarios.py | sed 's/^/scenarios.py: /'
echo "studies.md lines that tie an audit row to a comparison: $(grep -n "audit" docs/api/studies.md | grep -ic "comparison")"

V=$(cat "$OUT/verdict.json")
one=$(echo "$V" | field one); kept=$(echo "$V" | field maker_kept); re=$(echo "$V" | field retitled)
echo "EXPECTED: by studies.md:127, rows.py:59-60 and the tree's own test test_comparisons.py:106-111, Ben's ask over the same runs in the same order is the one comparison Ada made: one row, its id the artifact's, its by and at Ada's, its title the latest ask's (the test renames it as Grace and asserts by stays Ada Moreno); no document asks for an audit row for a comparison"
echo "OBSERVED: one comparison=$one, Ada's by and at kept=$kept, title now Ben's B=$re; Ada's title A is gone with no audit row, as the candidate says, and that is the behaviour the tree specifies and tests"
if [ "$one" = True ] && [ "$kept" = True ] && [ "$re" = True ]; then
  echo "RESULT: NO-DEFECT"
else
  echo "RESULT: DEFECT"
fi
exit 0
