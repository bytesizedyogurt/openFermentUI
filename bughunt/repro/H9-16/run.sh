#!/usr/bin/env bash
# H9-16: three callers at the tool door, each outside any ask of Postdoc's, propose the same gated
# action (runbooks lock) on the same target; the second and third are refused as "already proposed
# in this ask", though no ask holds any of the three calls.
#   bash bughunt/repro/H9-16/run.sh        (from the repository root)
# Keyless and offline: a gated write keeps a proposal and calls no model.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PYTHONDONTWRITEBYTECODE=1 PGOPTIONS='-c client_min_messages=warning'
DB=bh_r_h9_16_twin; PORT=9826; P=h916
cleanup() { bh_svc_stop "$PORT"; bh_db_drop "$DB"; rm -rf "$BH_WORK/data-$DB"; }
trap cleanup EXIT

O=$(bh_svc_start "$DB" "$PORT") || { echo "OBSERVED: the service did not start (setup)"; echo "RESULT: NO-DEFECT"; exit 0; }
bh_project "$O" "$P" >/dev/null
B='{"action":"lock","target":"rb-same","fields":{},"note":"lock it"}'
call() {  # call QUERY [HEADER...]: one runbooks_write at the tool door; prints the proposal id or the refusal
  local q="$1"; shift
  curl -s --noproxy '*' -X POST "$O/api/tools/runbooks_write$q" -H "X-OpenFerment-Project: $P" \
       -H 'content-type: application/json' "$@" -d "$B" |
    python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("error") or (d.get("summary") or {}).get("proposalId") or d)'
}
a=$(call '?by=Alice%20Person');                          echo "1. Alice Person (?by=):            $a"
b=$(call '?by=Bob%20Other');                             echo "2. Bob Other (?by=):               $b"
c=$(call '' -H 'X-OpenFerment-Assistant: other/1');      echo "3. assistant other/1 (header):     $c"

# What the project holds: the open proposals, each with its askId, and the audit rows of the writes.
open=$(curl -s --noproxy '*' "$O/api/proposals?state=proposed" -H "X-OpenFerment-Project: $P" |
  python3 -c 'import json,sys; print(json.dumps([{k: p.get(k) for k in ("id","by","target","askId")} for p in json.load(sys.stdin)]))')
echo "open proposals: $open"
aud=$(curl -s --noproxy '*' "$O/api/audit?action=lock" -H "X-OpenFerment-Project: $P" |
  python3 -c 'import json,sys; print(json.dumps([{k: r.get(k) for k in ("who","state","target","askId")} for r in json.load(sys.stdin)]))')
echo "audit rows for lock: $aud"
echo "the twin rule, as the tree holds it:"
grep -n "p.askId == made.askId\|already proposed in this ask" "$BH_ROOT/core/openferment_core/proposals.py" | sed 's/^/  /'

echo "EXPECTED: each call, outside any ask, judged on its own (Bob's and the assistant's kept as their own proposals), or a refusal whose words name the open proposal without calling it 'this ask'"
n_open=$(python3 -c 'import json,sys; print(len(json.loads(sys.argv[1])))' "$open")
no_ask=$(python3 -c 'import json,sys; print(all(p.get("askId") is None for p in json.loads(sys.argv[1])))' "$open")
echo "OBSERVED: Alice -> $a; Bob -> $b; assistant -> $c; open proposals $n_open, each askId null: $no_ask"
case "$a" in pr-*) first_ok=1;; *) first_ok=0;; esac
if [ "$first_ok" = 1 ] && [ "$n_open" = 1 ] && [ "$no_ask" = True ] \
   && grep -q "already proposed in this ask ($a)" <<< "$b" && grep -q "already proposed in this ask ($a)" <<< "$c"; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
