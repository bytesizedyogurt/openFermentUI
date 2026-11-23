#!/usr/bin/env bash
# Row 1 (dc02f20): a write's answer names its audit rows; GET /api/audit by action/target/who; null fields left out;
# catalogue_write keeps the call's note in detail; the audit is project-scoped.
O=${1:-http://127.0.0.1:8950}
C() { curl -s --noproxy "*" "$@"; }
echo "== catalogue_write through the tool door, as a person, in project pa"
C -X POST "$O/api/tools/catalogue_write?by=Ada%20Moreno" -H 'X-OpenFerment-Project: pa' -H 'content-type: application/json' \
  -d '{"kind":"skill","id":"sk-p1","name":"A placeholder skill","note":"a placeholder note"}' ; echo
echo "== the same as an assistant"
C -X POST "$O/api/tools/catalogue_write" -H 'X-OpenFerment-Assistant: probe/1' -H 'X-OpenFerment-Project: pa' -H 'content-type: application/json' \
  -d '{"kind":"skill","id":"sk-p2","name":"Another placeholder skill","note":"a second note"}' ; echo
echo "== GET /api/audit?action=catalogue_write&target=skill/sk-p1 in pa"
C "$O/api/audit?action=catalogue_write&target=skill/sk-p1" -H 'X-OpenFerment-Project: pa'; echo
echo "== GET /api/audit?who=probe/1 in pa"
C "$O/api/audit?who=probe/1" -H 'X-OpenFerment-Project: pa'; echo
echo "== GET /api/audit in pb (should be empty)"
C "$O/api/audit" -H 'X-OpenFerment-Project: pb'; echo
echo "== GET /api/audit?limit=0 and limit=-1"
C -o /dev/null -w '%{http_code}\n' "$O/api/audit?limit=0" -H 'X-OpenFerment-Project: pa'
C "$O/api/audit?limit=-1" -H 'X-OpenFerment-Project: pa'; echo
