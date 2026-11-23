#!/usr/bin/env bash
# H9: three callers at the tool door propose the same gated action on the same target.
#   twin_rule.sh PORT
source /home/user/openFermentUI/bughunt/lib/env.sh
port="$1"; O=$(bh_svc_start bh_h9_twin "$port") || exit 1; bh_project "$O" pa >/dev/null
B='{"action":"lock","target":"rb-same","fields":{},"note":"lock it"}'
say() { python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('error') or d['summary'].get('proposalId'))"; }
curl -s --noproxy '*' -X POST "$O/api/tools/runbooks_write?by=Alice%20Person" -H 'X-OpenFerment-Project: pa' -H 'content-type: application/json' -d "$B" | say
curl -s --noproxy '*' -X POST "$O/api/tools/runbooks_write?by=Bob%20Other" -H 'X-OpenFerment-Project: pa' -H 'content-type: application/json' -d "$B" | say
curl -s --noproxy '*' -X POST "$O/api/tools/runbooks_write" -H 'X-OpenFerment-Assistant: other/1' -H 'X-OpenFerment-Project: pa' -H 'content-type: application/json' -d "$B" | say
bh_svc_stop "$port"; bh_db_drop bh_h9_twin
