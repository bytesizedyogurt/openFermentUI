#!/usr/bin/env bash
# H14: a second comparison of the same runs rewrites the first comparison's title, and keeps it in the first
# maker's name and time. Fresh database bh_h14_cmp on port 8943: two library runs (corn, sugarcane), a comparison by
# "Ada" titled A, then one by "Ben" titled B over the same runs in the same order. Expected (studies.md: "the same runs
# in the same order are one comparison"): the comparison Ada kept keeps Ada's title, or Ben's ask is refused or kept
# beside it in Ben's name. Observed: the one row now holds Ben's title B, still `by` Ada at Ada's time; A is gone.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
PORT=8943; DB=bh_h14_cmp; P=cmp-check; O=$(bh_svc_start $DB $PORT) || exit 1
H=(-H "X-OpenFerment-Project: $P" -H 'content-type: application/json')
c() { curl -s --noproxy '*' "$@"; }
bh_project "$O" "$P" >/dev/null
R1=$(c -X POST "$O/api/library/corn/run" "${H[@]}" -d '{"by":"Ada"}' | python3 -c 'import json,sys; print(json.load(sys.stdin)["run"]["id"])')
R2=$(c -X POST "$O/api/library/sugarcane/run" "${H[@]}" -d '{"by":"Ada"}' | python3 -c 'import json,sys; print(json.load(sys.stdin)["run"]["id"])')
echo "runs: $R1 $R2"
echo "== Ada compares, titled A"
c -X POST "$O/api/studies/comparisons" "${H[@]}" -d "{\"title\":\"A: Ada's question\",\"runIds\":[\"$R1\",\"$R2\"],\"by\":\"Ada\"}" \
  | python3 -c 'import json,sys; d=json.load(sys.stdin)["comparison"]; print({k: d[k] for k in ("id","title","by","at")})'
echo "== Ben compares the same runs, titled B"
c -X POST "$O/api/studies/comparisons" "${H[@]}" -d "{\"title\":\"B: Ben's question\",\"runIds\":[\"$R1\",\"$R2\"],\"by\":\"Ben\"}" \
  | python3 -c 'import json,sys; d=json.load(sys.stdin)["comparison"]; print({k: d[k] for k in ("id","title","by","at")})'
echo "== what the project keeps"
c "$O/api/studies/comparisons" "${H[@]}" | python3 -c 'import json,sys; [print({k: x[k] for k in ("id","title","by","at")}) for x in json.load(sys.stdin)]'
psql "$BH_SERVER/$DB" -XAtc "select id, created_by, body->>'title', body->>'by' from openferment.comparisons"
echo "== the audit rows naming the comparison"
c "$O/api/audit?limit=50" "${H[@]}" | python3 -c 'import json,sys; [print(r.get("who"), r.get("action"), r.get("target")) for r in json.load(sys.stdin) if "compar" in (r.get("action") or "")]'
bh_svc_stop $PORT; bh_db_drop $DB
