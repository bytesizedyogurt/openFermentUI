#!/usr/bin/env bash
# H14-02: a strain kept in the project's catalogue with its aliases, then a record anchored whose organism is one
# of those aliases. Expected: anchoring resolves the wording to the strain's id (validate.py:1165-1167,
# Organisms.tsx:46-47). Observed: the record keeps the raw wording and no strain id, since the vocabulary anchoring
# reads (validate.vocabulary) holds no strain in the service.
# Fresh database bh_r_h14_02_alias, service on 127.0.0.1:10210, keyless; no model is called (the tool door's
# biorepo_write candidate anchors in code).
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
PORT=10210; DB=bh_r_h14_02_alias; P=h14-02; SID=ethanol-red
WORDING="Saccharomyces cerevisiae Ethanol Red"
cleanup() { bh_svc_stop $PORT; bh_db_drop $DB; rm -rf "$BH_WORK/data-$DB"; }
trap cleanup EXIT
O=$(bh_svc_start $DB $PORT) || { echo "RESULT: NO-DEFECT (the service did not start)"; exit 0; }
H=(-H "X-OpenFerment-Project: $P" -H 'content-type: application/json')
c() { curl -s --noproxy '*' "$@"; }
j() { python3 -c "import json,sys; d=json.load(sys.stdin); $1"; }

bh_project "$O" "$P" >/dev/null
DOCID=$(c -X POST "$O/api/intake/paste" "${H[@]}" -d "{\"title\":\"Bench note\",\"text\":\"$WORDING reached an ethanol titre of 41.7 g/L after 48 h on glucose.\",\"by\":\"Repro H14-02\",\"url\":\"\",\"licenceClass\":\"unknown\",\"licence\":\"\",\"reason\":\"alias check\"}" \
  | j 'print(d.get("documentId") or d.get("paperId") or d.get("id") or "")')
echo "step 1: pasted document $DOCID"
c -X POST "$O/api/catalogues/strain" "${H[@]}" -d "{\"entry\":{\"kind\":\"strain\",\"id\":\"$SID\",\"name\":\"Ethanol Red\",\"species\":\"Saccharomyces cerevisiae\",\"aliases\":[\"Ethanol Red\",\"$WORDING\"]},\"by\":\"Repro H14-02\"}" \
  | j 'print("step 2: strain kept:", d.get("id"), "aliases", d.get("aliases"))'
SEC=""
for i in $(seq 1 30); do
  SEC=$(c "$O/api/biorepo/overlay" "${H[@]}" | j 'ps=list(d["papers"].values()); print(ps[0]["sections"][0]["id"] if ps and ps[0].get("sections") else "")')
  [ -n "$SEC" ] && break; sleep 1
done
echo "step 3: section $SEC"
c -X POST "$O/api/tools/biorepo_write?by=Repro%20H14-02" "${H[@]}" -d "{\"action\":\"candidate\",\"target\":\"\",\"fields\":{\"paperId\":\"$DOCID\",\"sectionId\":\"$SEC\",\"field\":\"ethanol_titre\",\"value\":\"41.7\",\"unit\":\"g/L\",\"quote\":\"$WORDING reached an ethanol titre of 41.7 g/L after 48 h on glucose.\",\"organism\":\"$WORDING\"},\"note\":\"alias check\"}" \
  | j 'print("step 4: candidate through the tool door:", d.get("error") or d.get("detail") or "", json.dumps(d.get("summary"))[:200])'

ROW=$(c "$O/api/biorepo/overlay" "${H[@]}" | j '
rows = d["candidates"] + (list(d["records"].values()) if isinstance(d["records"], dict) else d["records"])
r = rows[0] if rows else {}
print(json.dumps({k: r.get(k) for k in ("organism", "organismText", "strainId")}))')
echo "step 5: the candidate as GET /api/biorepo/overlay serves it: $ROW"
HOSTS=$(c "$O/api/catalogues/strain" "${H[@]}" | j 'print([e["id"] for e in (d if isinstance(d, list) else d.values())])')
echo "step 6: GET /api/catalogues/strain ids: $HOSTS"

PYOUT=$(cd "$BH_ROOT/core" && bh_env OPENFERMENT_DATABASE_URL=$BH_SERVER/$DB .venv/bin/python - <<PY
from openferment_core import projects, validate, catalogues
with projects.using("$P"):
    cat = catalogues.as_strain_aliases()
    print("step 7: catalogues.as_strain_aliases():", cat)
    print("step 7: validate.vocabulary()['strains'] (what anchoring reads):", validate.vocabulary()["strains"])
    print("step 7: validate.strain_id('$WORDING') ->", validate.strain_id("$WORDING"))
    print("step 7: control, validate.match_whole_word('$WORDING', catalogue aliases) ->",
          validate.match_whole_word("$WORDING", cat))
PY
)
echo "$PYOUT"

STRAIN=$(echo "$ROW" | j 'print(d.get("strainId"))' 2>/dev/null)
ORG=$(echo "$ROW" | j 'print(d.get("organism"))' 2>/dev/null)
echo "EXPECTED: the candidate's strainId is $SID (organism resolved through the kept alias \"$WORDING\"), so the strain page and Hosts counts name it"
echo "OBSERVED: strainId=$STRAIN organism=\"$ORG\"; the anchoring vocabulary's strains: $(echo "$PYOUT" | grep -o "anchoring reads): .*" | cut -d' ' -f3-)"
if [ "$STRAIN" != "$SID" ] && echo "$PYOUT" | grep -q "'$(echo "$WORDING" | tr 'A-Z' 'a-z')': '$SID'"; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
