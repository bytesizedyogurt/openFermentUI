#!/usr/bin/env bash
# Row 5: the catalogues are project stores; a protocol's step skills are held to the skill catalogue.
# Keeps a skill in pa, reads it from pa and pb, makes a protocol in pb naming pa's skill (should be refused),
# makes it in pa (should be kept), takes a file of strains in through Intake, and reads catalogue_read over the
# tool door in each project.
O=${1:-http://127.0.0.1:8950}
C() { curl -s --noproxy "*" "$@"; }
J='content-type: application/json'
echo "== keep a skill in pa"
C -X POST "$O/api/catalogues/skill" -H 'X-OpenFerment-Project: pa' -H "$J" \
  -d '{"by":"Ada Moreno","entry":{"kind":"skill","id":"SK-P5","name":"A placeholder skill","family":"aseptic"}}' | head -c 300; echo
echo "== the skill read in pa, then in pb"
C "$O/api/catalogues/skill" -H 'X-OpenFerment-Project: pa' | python3 -c 'import json,sys; print([e["id"] for e in json.load(sys.stdin)])'
C "$O/api/catalogues/skill" -H 'X-OpenFerment-Project: pb' | python3 -c 'import json,sys; print([e["id"] for e in json.load(sys.stdin)])'
C -o /dev/null -w 'pb GET skill/SK-P5: %{http_code}\n' "$O/api/catalogues/skill/SK-P5" -H 'X-OpenFerment-Project: pb'
PROTO='{"by":"Ada Moreno","protocol":{"id":"pr-p5","title":"A placeholder protocol","category":"sop","bsl":1,"currentVersion":"1.0","versions":[{"version":"1.0","baseBatch":{"value":1,"unit":"L","label":"a placeholder batch"},"estMinutes":{"active":1,"total":2},"steps":[{"id":"s1","text":"A placeholder step","skills":["SK-P5"]}]}]}}'
echo "== a protocol naming SK-P5 made in pb (pb's catalogue holds no SK-P5)"
C -X POST "$O/api/protocols" -H 'X-OpenFerment-Project: pb' -H "$J" -d "$PROTO" | head -c 300; echo
echo "== the same made in pa"
C -X POST "$O/api/protocols" -H 'X-OpenFerment-Project: pa' -H "$J" -d "$PROTO" -o /dev/null -w '%{http_code}\n'
echo "== pb's protocols"
C "$O/api/protocols" -H 'X-OpenFerment-Project: pb' | head -c 200; echo
echo "== a file of strains through Intake into pb"
printf '[{"kind":"strain","id":"st-p5","name":"Placeholdera testii P5","aliases":["P5 alias"]}]' > /tmp/claude-0/-home-user-openFermentUI/cfbc5c9f-640a-5002-a705-5ceaf850fdc6/scratchpad/bh/work/P/strains.json
C -X POST "$O/api/intake/catalogue" -H 'X-OpenFerment-Project: pb' -F kind=strain -F by="Ada Moreno" \
  -F "file=@/tmp/claude-0/-home-user-openFermentUI/cfbc5c9f-640a-5002-a705-5ceaf850fdc6/scratchpad/bh/work/P/strains.json;type=application/json" | head -c 400; echo
echo "== catalogue_read for strains in pa and pb through the tool door"
for p in pa pb; do C -X POST "$O/api/tools/catalogue_read" -H "X-OpenFerment-Project: $p" -H "$J" -d '{"kind":"strain","words":"","limit":10}' | python3 -c 'import json,sys; d=json.load(sys.stdin); print("'$p'", d.get("error"), [r.get("id") for r in (d.get("summary") or {}).get("entries", [])], str(d.get("summary"))[:200])'; done
