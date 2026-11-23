#!/usr/bin/env bash
# H14: a kept strain's aliases never resolve a record's organism wording to the strain.
# Fresh database bh_h14_alias on port 8942: a project, a pasted document naming "Saccharomyces cerevisiae Ethanol Red",
# a strain kept with the alias "Ethanol Red" (and the paper's full wording too), then a candidate anchored through the
# tool door (biorepo_write candidate: anchoring with no model) whose organism is the paper's wording. Expected: the
# record's organism resolves to the strain id (validate.py:1165-1170, Organisms.tsx:46-47, intake.md:106). Observed:
# strainId null, organism the raw wording; the vocabulary anchoring reads holds no strain at all.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
PORT=8942; DB=bh_h14_alias; P=alias-check; O=$(bh_svc_start $DB $PORT) || exit 1
H=(-H "X-OpenFerment-Project: $P" -H 'content-type: application/json')
c() { curl -s --noproxy '*' "$@"; }
bh_project "$O" "$P" >/dev/null
DOC=$(c -X POST "$O/api/intake/paste" "${H[@]}" -d '{"title":"Bench note","text":"Saccharomyces cerevisiae Ethanol Red reached an ethanol titre of 41.7 g/L after 48 h on glucose.","by":"Hunt Fourteen","url":"","licenceClass":"unknown","licence":"","reason":"alias check"}')
DOCID=$(echo "$DOC" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("documentId") or d.get("paperId") or d.get("id"))')
echo "pasted: $DOC" | cut -c1-200
c -X POST "$O/api/catalogues/strain" "${H[@]}" -d '{"entry":{"kind":"strain","id":"ethanol-red","name":"Ethanol Red","species":"Saccharomyces cerevisiae","aliases":["Ethanol Red","Saccharomyces cerevisiae Ethanol Red"]},"by":"Hunt Fourteen"}' | cut -c1-160; echo
for i in $(seq 1 30); do
  SEC=$(c "$O/api/biorepo/overlay" "${H[@]}" | python3 -c 'import json,sys; d=json.load(sys.stdin); ps=list(d["papers"].values()); print(ps[0]["sections"][0]["id"] if ps and ps[0].get("sections") else "")')
  [ -n "$SEC" ] && break; sleep 1
done
echo "section: $SEC"
c -X POST "$O/api/tools/biorepo_write?by=Hunt%20Fourteen" "${H[@]}" -d "{\"action\":\"candidate\",\"target\":\"\",\"fields\":{\"paperId\":\"$DOCID\",\"sectionId\":\"$SEC\",\"field\":\"ethanol_titre\",\"value\":\"41.7\",\"unit\":\"g/L\",\"quote\":\"Saccharomyces cerevisiae Ethanol Red reached an ethanol titre of 41.7 g/L after 48 h on glucose.\",\"organism\":\"Saccharomyces cerevisiae Ethanol Red\"},\"note\":\"alias check\"}" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("tool:", d.get("error") or d.get("detail"), d.get("summary"))'
echo "== the candidate as the overlay serves it"
c "$O/api/biorepo/overlay" "${H[@]}" | python3 -c '
import json,sys
d=json.load(sys.stdin)
rows = d["candidates"] + (list(d["records"].values()) if isinstance(d["records"], dict) else d["records"])
for r in rows:
    print({k: r.get(k) for k in ("id","organism","organismText","strainId")})
'
echo "== validate.strain_id over the project, as anchoring calls it"
(cd "$BH_ROOT/core" && bh_env OPENFERMENT_DATABASE_URL=$BH_SERVER/$DB .venv/bin/python - <<EOF
from openferment_core import projects, validate, catalogues
with projects.using("$P"):
    print("catalogue aliases:", catalogues.as_strain_aliases())
    print("anchoring vocabulary strains:", validate.vocabulary()["strains"])
    print("strain_id('Saccharomyces cerevisiae Ethanol Red') ->", validate.strain_id("Saccharomyces cerevisiae Ethanol Red"))
EOF
)
bh_svc_stop $PORT; bh_db_drop $DB
