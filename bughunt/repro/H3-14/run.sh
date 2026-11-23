#!/usr/bin/env bash
# H3-14: the deposition screen's "Released to BioRepo" band draws a released value nobody read back with the
# measured badge and a measured tick, while the runbooks module read marks the same row unverified.
#   bash bughunt/repro/H3-14/run.sh        (from the repository root; exits 0 either way)
# A fresh test database, the service on a free port in 10000-10009 over the built dist/ (keyless, no worker,
# no model call), a project with one runbook and one closed deposition (one reading read back, one never),
# the reconciliation recorded by the screen's own button in Chromium, then the band read beside runbooks_read.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PYTHONDONTWRITEBYTECODE=1 PGOPTIONS='-c client_min_messages=warning'
DB=bh_r_h3_14_released
HERE=/home/user/openFermentUI/bughunt/repro/H3-14
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
for p in $(seq 10000 10009); do
  [ -n "$(bh_port_pid "$p")" ] && continue
  if o=$(BH_KEEP_DB=1 bh_svc_start "$DB" "$p") && mine_on "$p"; then PORT=$p; O=$o; break; fi
done
[ -n "$O" ] || { echo "no service could start on 10000-10009"; echo "RESULT: NO-DEFECT (no service)"; exit 0; }
echo "service: $O over $DB, serving $BH_ROOT/dist"
echo "project: $(bh_project "$O" h3-14 "H3-14" | head -c 160)"

OUT=$(cd "$BH_ROOT" && NO_PROXY='*' no_proxy='*' timeout 240 node "$HERE/screen.cjs" "$O" "$HERE/screen.png" 2>&1)
echo "$OUT" | grep -v -E '^(EXPECTED|OBSERVED|RESULT):'
echo "the rows openferment.measured_evidence keeps for the project (id | created_by | confirmed | provenance in the body):"
psql "$BH_SERVER/$DB" -qXAt -F ' | ' -c \
  "SELECT id, created_by, body->>'confirmed', body->>'provenance' FROM openferment.measured_evidence
     WHERE project_id='h3-14' ORDER BY body->>'label'" 2>&1
echo "the screen's source for the band:"
grep -n 'ProvenanceBadge p="measured"\|Tick p="measured"\|unconfirmed'"'" "$BH_ROOT/src/screens/DepositionDetail.tsx"
echo
echo "$OUT" | grep -E '^(EXPECTED|OBSERVED):'
echo "$OUT" | grep -E '^RESULT: ' || echo "RESULT: NO-DEFECT (the script did not complete; see the lines above)"
exit 0
