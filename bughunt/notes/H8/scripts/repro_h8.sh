#!/usr/bin/env bash
# H8's reproductions from a fresh database: bash repro_h8.sh H8-01 (or H8-05, H8-07, ...).
# Starts the head's service on 127.0.0.1:8887 over a fresh bh_h8_r database, keyless, runs the case,
# stops the service and drops the database. H8-05 and H8-07 run in-process beside the service.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
ID="$1"; HERE=/home/user/openFermentUI/bughunt/notes/H8/scripts; PORT=8887; DB=bh_h8_r$(echo "$ID" | tr -dc '0-9')
ORIGIN=$(bh_svc_start "$DB" "$PORT") || { echo "the service did not start"; exit 2; }
status=0
case "$ID" in
  H8-05)
    bh_project "$ORIGIN" sffp >/dev/null
    (cd "$BH_ROOT/core" && bh_env OPENFERMENT_DATABASE_URL="$BH_SERVER/$DB" OPENFERMENT_DATA_DIR="$BH_WORK/data-$DB" \
       OPENFERMENT_SFF_LIBRARY="$BH_WORK/data-$DB/sff-library" .venv/bin/python -I "$HERE/import_url_route.py") \
       2>&1 | grep -E '^/' | tee /dev/stderr | grep -q '^/bad-location -> 500' || status=1
    [ $status = 0 ] && echo SHOWN || echo "NOT SHOWN" ;;
  H8-07)
    (cd "$BH_ROOT/core" && bh_env .venv/bin/python -I "$HERE/report_lane_setup.py" paste "$ORIGIN" rep) | tee /tmp/h8-07.$$
    A=$(head -1 /tmp/h8-07.$$ | awk '{print $2}'); rm -f /tmp/h8-07.$$
    mkdir -p "$BH_WORK/H8/repro-data"
    (cd "$BH_ROOT/core" && bh_env OPENFERMENT_DATABASE_URL="$BH_SERVER/$DB" .venv/bin/python -I \
       "$HERE/report_lane_setup.py" candidate rep "$A") 2>&1 | grep candidate
    OUT=$(cd "$BH_ROOT/core" && bh_env OPENFERMENT_DATABASE_URL="$BH_SERVER/$DB" OPENFERMENT_DATA_DIR="$BH_WORK/H8/repro-data" \
       .venv/bin/python -I -m openferment_core.literature_live report --project rep --by h8 \
       --configs interactive,vector_only,keyword_only 2>/dev/null | tail -1)
    FILE=$(echo "$OUT" | python3 -c 'import json,sys; print(json.load(sys.stdin)["file"])')
    python3 - "$FILE" <<'EOF' || status=1
import json, sys
r = json.load(open(sys.argv[1])); q = r["truth"]["questions"][0]
lane = r["retrieval"]["interactive"]
top = lane["ranked"][q["id"]][0]
k, p = lane["kit"]["records"][0], lane["passage"]["records"][0]
print("question:", q["question"], "| its document:", q["documentId"])
print("first passage retrieved is of document:", top["documentId"])
print("kit rule first relevant rank:", k["first_relevant_rank"], "| passage rule:", p["first_relevant_rank"])
ok = top["documentId"] != q["documentId"] and k["first_relevant_rank"] == 1 and p["first_relevant_rank"] == 2
print("SHOWN" if ok else "NOT SHOWN"); sys.exit(0 if ok else 1)
EOF
    ;;
  *)
    (cd "$BH_ROOT/core" && bh_env .venv/bin/python -I "$HERE/repro_h8.py" "$ID" "$ORIGIN") || status=1 ;;
esac
bh_svc_stop "$PORT"; bh_db_drop "$DB"
exit $status
