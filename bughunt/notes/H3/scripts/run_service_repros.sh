#!/usr/bin/env bash
# H3: every service-level reproduction, from a fresh test database, in order. Keyless, no worker started.
#   bash /home/user/openFermentUI/bughunt/notes/H3/scripts/run_service_repros.sh
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
S=/home/user/openFermentUI/bughunt/notes/H3/scripts
O=$(bh_svc_start bh_h3_a 8830) || exit 1
bh_project "$O" p1 "P one" >/dev/null; bh_project "$O" p2 "P two" >/dev/null
cd /home/user/openFermentUI/core
for s in bench_doors.py bench_doors2.py kinetics_provenance.py kinetics_corrected.py dup_id.py catalogue_doors.py; do
  echo "=== $s"; bh_env .venv/bin/python "$S/$s" "$O"
done
echo "=== deposition_screen.cjs"
(cd /home/user/openFermentUI && NO_PROXY='*' no_proxy='*' node "$S/deposition_screen.cjs" "$O" "${BH_WORK}")
bh_svc_stop 8830; bh_db_drop bh_h3_a
