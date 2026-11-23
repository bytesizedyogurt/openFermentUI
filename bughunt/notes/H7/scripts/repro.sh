#!/usr/bin/env bash
# H7 reproductions, from a copy of the development database (read with pg_dump alone) seeded with placeholder rows
# through the API. Usage: bash repro.sh <scenario>, one of:
#   twotabs        H7-01  two tabs, service away: tab A's reading erased from the browser's queue
#   reload         H7-02  a reload while the service is away: the bench says not found; the queue waits for a second reload
#   sameonline     H7-03  two tabs on one deposition, service up: the second tab's reading refused and dropped
#   overrides      H7-04  two tabs on one scenario's panel: one override erases the other
#   unknown        H7-05  an address naming a project the service does not hold reloads without end
#   stopped-words  H7-06  detail pages with every /api request refused
#   a11y           H7-07  the Deposition takeover at 810x1080
#   logo           H7-08  the rail's logo drops the project from the address
#   runreload      H7-09  a protocol's run and its deviation note after a reload
#   stop           (held) the service stopped and started under a live page: writes sent once, in order
#   walk           every rail and secondary screen in the empty, full and stopped states
# Every database is bh_h7_*; the service listens on 127.0.0.1:8873; both are removed at the end.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=$BH_WORK/H7/repro; mkdir -p "$OUT"
DB=bh_h7_repro; PORT=8873; ORIGIN=http://127.0.0.1:$PORT
NODE() { (cd "$HERE" && env -u HTTPS_PROXY -u HTTP_PROXY -u https_proxy -u http_proxy timeout 900 node "$@"); }
bh_db_drop $DB
psql "$BH_SERVER/postgres" -qXc "CREATE DATABASE $DB"
pg_dump -Fc -d "$BH_SERVER/openferment_dev" | pg_restore --no-owner -d "$BH_SERVER/$DB" 2>/dev/null
BH_KEEP_DB=1 bh_svc_start $DB $PORT >/dev/null || exit 1
RUN=$(curl -s --noproxy '*' -H 'X-OpenFerment-Project: ethanol' "$ORIGIN/api/runs" | python3 -c "import json,sys; print(json.load(sys.stdin)[0]['id'])")
python3 "$HERE/seed_full.py" "$ORIGIN" ethanol "$RUN" > "$OUT/seed.log"
curl -s --noproxy '*' -X POST -H 'Content-Type: application/json' -H 'X-OpenFerment-Project: ethanol' "$ORIGIN/api/guild/people" \
  -d '{"id":"p-hseven","name":"H7 Hunter","role":"lead","joinedAt":"2026-11-01","addedAt":"2026-11-10T00:00:00Z","addedBy":null}' >/dev/null
RB=$(grep '^RUNBOOK ' "$OUT/seed.log" | cut -d' ' -f2)
case "${1:-}" in
  twotabs|reload|sameonline|stop) NODE outbox.mjs "$ORIGIN" ethanol "$RB" $DB $PORT "$1" "$OUT/$1.json" ;;
  overrides) NODE overrides_twotabs.mjs "$ORIGIN" ethanol ethanol_glucose_v0 "$OUT/overrides.json" ;;
  unknown) NODE unknown_project.mjs "$ORIGIN" nosuchproject ;;
  stopped-words)
    sed "s/rb-study-291ece4fcd99/$RB/" "$HERE/ids_full.json" > "$OUT/ids.json"
    NODE stopped_words.mjs "$ORIGIN" ethanol "$OUT/ids.json" "$OUT/stopped-words.json" ;;
  a11y) NODE deposition_a11y.mjs "$ORIGIN" ethanol "$RB" 'H7 placeholder protocol' "$OUT/a11y.json" ;;
  logo) NODE logo.mjs "$ORIGIN" ethanol ;;
  runreload) NODE run_reload.mjs "$ORIGIN" ethanol h7-protocol ;;
  walk)
    sed "s/rb-study-291ece4fcd99/$RB/" "$HERE/ids_full.json" > "$OUT/ids.json"
    NODE walk_all.mjs "$ORIGIN" ethanol full "$OUT/walk-full.json" "$OUT/ids.json"
    NODE walk_all.mjs "$ORIGIN" ethanol stopped "$OUT/walk-stopped.json" "$OUT/ids.json" ;;
  *) echo "unknown scenario: ${1:-}" ;;
esac
bh_svc_stop $PORT
bh_db_drop $DB
