#!/usr/bin/env bash
# H3-13: catalogue_write, in the model's lane, keeps a paper's measured values written in words (a strain
# named "Strain making 45 g/L", a summary "reaches a titre of 45 g/L ...", a note "... 0.45 g/g yield"),
# against its own description: "Names and words only, never a measured value: a number a paper reports is
# a record".
#   bash bughunt/repro/H3-13/run.sh        (from the repository root; exits 0 either way)
# A fresh test database, the service on a free port in 9700-9709 (keyless, no worker, no model call), two
# calls at POST /api/tools/catalogue_write with the assistant header, one read back, the row in the table.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PYTHONDONTWRITEBYTECODE=1 PGOPTIONS='-c client_min_messages=warning'
DB=bh_r_h3_13_catalogue
HERE=/home/user/openFermentUI/bughunt/repro/H3-13
PORT=""

# Whether the listener on a port is this run's service (its environment names this run's database).
mine_on() {
  local pid; pid=$(bh_port_pid "$1"); [ -n "$pid" ] || return 1
  tr '\0' '\n' < "/proc/$pid/environ" 2>/dev/null | grep -qx "OPENFERMENT_DATABASE_URL=$BH_SERVER/$DB"
}
cleanup() {
  if [ -n "$PORT" ] && mine_on "$PORT"; then bh_svc_stop "$PORT"; fi
  bh_db_drop "$DB"
  rm -rf "$BH_WORK/data-$DB"
}
trap cleanup EXIT

bh_db_fresh "$DB" || { echo "bh_db_fresh failed"; echo "RESULT: NO-DEFECT (the database could not be made)"; exit 0; }
echo "database: $DB (fresh, migrated to head)"
O=""
for p in $(seq 9700 9709); do
  [ -n "$(bh_port_pid "$p")" ] && continue
  if o=$(BH_KEEP_DB=1 bh_svc_start "$DB" "$p") && mine_on "$p"; then PORT=$p; O=$o; break; fi
done
[ -n "$O" ] || { echo "no service could start on 9700-9709"; echo "RESULT: NO-DEFECT (no service)"; exit 0; }
echo "service: $O over $DB"

OUT=$(bh_py "$HERE/repro.py" "$O" 2>&1)
echo "$OUT" | grep -v -E '^(EXPECTED|OBSERVED|RESULT):'
echo "the row openferment.catalogue keeps (id | created_by | agent | via | name | summary | note):"
psql "$BH_SERVER/$DB" -qXAt -F ' | ' -c \
  "SELECT id, created_by, body->>'agent', body->>'via', body->>'name', body->>'summary', body->>'note'
     FROM openferment.catalogue WHERE project_id='h3-13' ORDER BY id" 2>&1
echo "the audit row of the write (module | action | state | target | who | agent):"
psql "$BH_SERVER/$DB" -qXAt -F ' | ' -c \
  "SELECT module, action, state, target, who, agent FROM openferment.audit WHERE project_id='h3-13'
     AND action='catalogue_write' ORDER BY 1" 2>&1
echo
echo "$OUT" | grep -E '^(EXPECTED|OBSERVED):'
echo "$OUT" | grep -E '^RESULT: ' || echo "RESULT: NO-DEFECT (the script did not complete; see the lines above)"
exit 0
