#!/usr/bin/env bash
# H9-14: a NUL in an id answers with the database driver's error, its SQL statement and bound
# parameters, where an id of no run, record or document is refused in words.
#   bash bughunt/repro/H9-14/run.sh   (from the repository's root)
# A fresh database, the head's service on 127.0.0.1:9221 over it (keyless), one project; then
# engine_report and flowsheet_read at the REST tool door and get_document on the sci-rag MCP
# server, each asked once with an id of nothing and once with "a\u0000b". Cleans up after itself.
source /home/user/openFermentUI/bughunt/lib/env.sh
HERE="$BH_ROOT/bughunt/repro/H9-14"
W="$BH_WORK/H9-14"; mkdir -p "$W"
DB=bh_r_h9_14_svc; PORT=9221; P=h914; O="http://127.0.0.1:$PORT"
DATA="$W/data"

cleanup() {
  bh_svc_stop "$PORT"
  bh_db_drop "$DB"
  rm -rf "$W"
}
trap cleanup EXIT

bh_svc_stop "$PORT"
bh_db_fresh "$DB" || { echo "OBSERVED: no fresh database"; echo "RESULT: NO-DEFECT"; exit 0; }
rm -rf "$DATA"; cp -R "$BH_DATA_SRC" "$DATA"
(
  cd "$BH_ROOT/core" || exit 1
  bh_env OPENFERMENT_DATABASE_URL="$BH_SERVER/$DB" OPENFERMENT_DATA_DIR="$DATA" \
    OPENFERMENT_SFF_LIBRARY="$DATA/sff-library" OPENFERMENT_DIST_DIR="$BH_ROOT/dist" \
    OPENFERMENT_POLL_HOST=127.0.0.1 OPENFERMENT_PORT="$PORT" \
    OPENFERMENT_ROUTES= OPENFERMENT_LOCAL_BASE_URL= ANTHROPIC_BASE_URL=http://127.0.0.1:9 \
    setsid .venv/bin/python -m uvicorn openferment_core.api:app --host 127.0.0.1 --port "$PORT" \
    --log-level warning < /dev/null > "$W/svc.log" 2>&1 &
)
up=0; for i in $(seq 1 240); do
  curl -sf --noproxy '*' "$O/api/health" >/dev/null 2>&1 && { up=1; break; }; sleep 0.5
done
[ "$up" = 1 ] || { echo "OBSERVED: the service gave no health answer"; cat "$W/svc.log"; echo "RESULT: NO-DEFECT"; exit 0; }
echo "service: $O over $DB"
echo "project: $(bh_project "$O" "$P" | cut -c1-120)"

tool() {  # tool NAME JSON-BODY: the answer's status and its error field
  curl -s --noproxy '*' -o "$W/answer.json" -w '%{http_code}' -X POST "$O/api/tools/$1" \
       -H "X-OpenFerment-Project: $P" -H 'content-type: application/json' -d "$2" > "$W/status"
  echo "[$(cat "$W/status")] $(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("error"))' "$W/answer.json" | tr '\n' ' ')"
}

echo "## engine_report, an id of no run"
ER_UNKNOWN=$(tool engine_report '{"run":"no-such-run"}'); echo "$ER_UNKNOWN"
echo "## engine_report, a NUL in the run id"
ER_NUL=$(tool engine_report '{"run":"a\u0000b"}'); echo "$ER_NUL"
echo "## flowsheet_read, an id of no record"
FR_UNKNOWN=$(tool flowsheet_read '{"record":"no-such-record"}'); echo "$FR_UNKNOWN"
echo "## flowsheet_read, a NUL in the record id"
FR_NUL=$(tool flowsheet_read '{"record":"a\u0000b"}'); echo "$FR_NUL"
echo "## sci-rag get_document, an id of no document and a NUL in the id"
SR=$(bh_py "$HERE/scirag_get_document.py" "$BH_SERVER/$DB" "$P" 2>&1); echo "$SR"
SR_UNKNOWN=$(printf '%s\n' "$SR" | grep '^CASE unknown'); SR_NUL=$(printf '%s\n' "$SR" | grep '^CASE nul')

leaks() { case "$1" in *DBAPIError*"[SQL: SELECT"*"[parameters: "*) return 0;; *) return 1;; esac; }
clean() { [ -n "$1" ] && ! case "$1" in *DBAPIError*|*"[SQL:"*|*"[parameters:"*) true;; *) false;; esac; }

n=0; where=()
leaks "$ER_NUL" && clean "$ER_UNKNOWN" && { n=$((n+1)); where+=("engine_report"); }
leaks "$FR_NUL" && clean "$FR_UNKNOWN" && { n=$((n+1)); where+=("flowsheet_read"); }
leaks "$SR_NUL" && clean "$SR_UNKNOWN" && { n=$((n+1)); where+=("sci-rag get_document"); }

echo
echo "EXPECTED: an id holding a NUL is refused in words as an id of nothing is (engine_report refused: ..., flowsheet_read refused: ..., the kit's words for a document the project does not hold), with no driver error, SQL text or bound parameters"
if leaks "$ER_NUL" && clean "$ER_UNKNOWN"; then
  echo "OBSERVED: at ${n} of 3 doors (${where[*]}) the id of nothing is refused in words and the NUL id answers the driver's DBAPIError with its [SQL: SELECT ...] statement and [parameters: (project, id)]; engine_report's: $(printf '%s' "$ER_NUL" | cut -c1-330)"
  echo "RESULT: DEFECT"
else
  echo "OBSERVED: engine_report with a NUL answers: $(printf '%s' "$ER_NUL" | cut -c1-330)"
  echo "RESULT: NO-DEFECT"
fi
exit 0
