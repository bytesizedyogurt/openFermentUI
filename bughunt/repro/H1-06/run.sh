#!/usr/bin/env bash
# H1-06: a worker's things answer stating an infinite precision passes the service's shape check; the
# listing then serves its atol as null, and a run of that thing answers a plain-text 500.
# Run from the repository root: bash bughunt/repro/H1-06/run.sh
#
# The stand-in engines h106 and h106neg (standin/, written by hand for this reproduction) register under
# `openferment.engines` through a dist-info made in a scratch directory and put on PYTHONPATH, so nothing
# is installed into any venv and nothing in core/ is edited. The service is the repository's own, keyless
# (an empty key stands over core/.env, every proxy variable points at a closed port), on 127.0.0.1:9660
# over a fresh database bh_r_h1_06_svc, dropped at the end.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh

HERE=$BH_ROOT/bughunt/repro/H1-06
DB=bh_r_h1_06_svc
PORT=9660
O=http://127.0.0.1:$PORT
PROJ=h106
W=$BH_WORK/H1-06/run-$$
DEAD=http://127.0.0.1:9

cleanup() {
  bh_svc_stop "$PORT" 2>/dev/null
  bh_db_drop "$DB" 2>/dev/null
  rm -rf "$W"
  rmdir "$BH_WORK/H1-06" 2>/dev/null
}
trap cleanup EXIT
mkdir -p "$W/site" "$W/out"

# The stand-in package and its dist-info: importlib.metadata finds a distribution on any sys.path entry.
cp -R "$HERE/standin/h106standin" "$W/site/"
DI=$W/site/openferment_engine_h106-0.1.0.dist-info
mkdir -p "$DI"
printf 'Metadata-Version: 2.1\nName: openferment-engine-h106\nVersion: 0.1.0\n' > "$DI/METADATA"
printf '[openferment.engines]\nh106 = h106standin.engine:ENGINE\nh106neg = h106standin.engine:NEG\n' > "$DI/entry_points.txt"
cp -R "$BH_DATA_SRC" "$W/data"

if ! bh_db_fresh "$DB"; then
  echo "EXPECTED: a fresh database for the service"
  echo "OBSERVED: bh_db_fresh $DB failed; nothing was checked"
  echo "RESULT: NO-DEFECT"; exit 0
fi

echo "== the service on $O over $DB, the stand-in engines on PYTHONPATH"
(
  cd "$BH_ROOT/core" || exit 1
  bh_env PYTHONPATH="$W/site" HTTPS_PROXY=$DEAD HTTP_PROXY=$DEAD https_proxy=$DEAD http_proxy=$DEAD \
    ALL_PROXY=$DEAD all_proxy=$DEAD NO_PROXY=127.0.0.1,localhost no_proxy=127.0.0.1,localhost \
    OPENFERMENT_DATABASE_URL="$BH_SERVER/$DB" OPENFERMENT_DATA_DIR="$W/data" \
    OPENFERMENT_SFF_LIBRARY="$W/data/sff-library" OPENFERMENT_DIST_DIR="$BH_ROOT/dist" \
    OPENFERMENT_POLL_HOST=127.0.0.1 OPENFERMENT_PORT="$PORT" \
    setsid .venv/bin/python -m uvicorn openferment_core.api:app --host 127.0.0.1 --port "$PORT" \
    --log-level warning < /dev/null > "$W/svc.log" 2>&1 &
)
up=0
for i in $(seq 1 240); do
  curl -sf --noproxy '*' "$O/api/health" >/dev/null 2>&1 && { up=1; break; }
  sleep 0.5
done
if [ "$up" != 1 ]; then
  echo "EXPECTED: the service answers health on $PORT"
  echo "OBSERVED: no health answer; the log ends: $(tail -3 "$W/svc.log" | tr '\n' ' ')"
  echo "RESULT: NO-DEFECT"; exit 0
fi
bh_project "$O" "$PROJ" >/dev/null
H=(-H 'content-type: application/json' -H "X-OpenFerment-Project: $PROJ")

echo "== GET /api/engines: the stand-ins as listed"
curl -s --noproxy '*' "$O/api/engines" "${H[@]}" -o "$W/out/engines.json" -w '[%{http_code}]\n'
python3 - "$W/out/engines.json" > "$W/out/listed.txt" <<'PY'
import json, sys
for e in json.load(open(sys.argv[1])):
    if e["name"] in ("h106", "h106neg"):
        things = [(t["id"], t["precision"]) for t in e.get("things") or []]
        print(f"{e['name']}: things={things} error={(e.get('error') or '')[:220]!r}")
PY
cat "$W/out/listed.txt"
LIST_INF=$(grep '^h106:' "$W/out/listed.txt")
LIST_NEG=$(grep '^h106neg:' "$W/out/listed.txt")
SCHEMA=$(python3 -c "
import json; s = json.load(open('$BH_ROOT/docs/api/openapi.json'))['components']['schemas']['EnginePrecision']['properties']['atol']
print(s.get('type'), 'minimum', s.get('minimum'))")
echo "docs/api/openapi.json EnginePrecision.atol: $SCHEMA"

# run THING ENGINE: POST /api/engines/ENGINE/run; prints "CODE CONTENT-TYPE BODY(first 300 bytes)".
run() {
  local code ctype
  read -r code ctype < <(curl -s --noproxy '*' -m 60 -X POST "$O/api/engines/$2/run" "${H[@]}" \
    -d "{\"thing\":\"$1\",\"by\":\"H1-06\"}" -o "$W/out/run-$1.out" -w '%{http_code} %{content_type}\n')
  echo "$code ${ctype:-none} $(head -c 300 "$W/out/run-$1.out")"
}
echo "== control: POST /api/engines/h106/run {thing: fine}"
R_FINE=$(run fine h106); echo "$R_FINE" | cut -c1-200
echo "== the case: POST /api/engines/h106/run {thing: infprec}"
R_INF=$(run infprec h106); echo "$R_INF"
echo "== control: POST /api/engines/h106neg/run {thing: negprec}"
R_NEG=$(run negprec h106neg); echo "$R_NEG"

ROWS=$(psql "$BH_SERVER/$DB" -XAtc "SELECT count(*) FROM openferment.runs WHERE project_id = '$PROJ' AND engine = 'h106' AND body->>'plant' = 'infprec'")
ROWS_FINE=$(psql "$BH_SERVER/$DB" -XAtc "SELECT count(*) FROM openferment.runs WHERE project_id = '$PROJ' AND engine = 'h106' AND body->>'plant' = 'fine'")
echo "runs rows kept: infprec $ROWS, fine $ROWS_FINE"
LOGEND=$(grep -E '^[A-Za-z]+Error' "$W/svc.log" | tail -1)
LOGAT=$(grep -E 'File ".*openferment_core/' "$W/svc.log" | tail -2 | sed -E 's#.*openferment_core/#openferment_core/#' | tr '\n' ' ')
echo "service log, the last exception: $LOGEND"
echo "service log, its last two openferment_core frames: $LOGAT"

echo
echo "EXPECTED: h106's things answer, holding a precision whose atol is infinite (docs/api/workers.md:62-68: \"a number that is NaN or infinite ... breaks the contract: the service raises EngineBroken, keeps no runs row and answers 503 in words\"), is refused as outside the protocol: h106 is listed with that in words (as h106neg is for its negative atol), and POST /api/engines/h106/run answers 503 in words with no runs row (docs/api/engines.md:517-520)"
echo "OBSERVED: listing: $LIST_INF"
echo "OBSERVED: run of infprec: $R_INF (content-type and body above), $ROWS runs row(s) kept; the log: $LOGEND"
echo "CONTROL:  run of fine in the same engine: $(cut -c1-60 <<<"$R_FINE") ..."
echo "CONTROL:  listing: $LIST_NEG"
echo "CONTROL:  run of negprec: $(cut -c1-220 <<<"$R_NEG")"

inf_listed_null=0; grep -q "'infprec', {'rtol': 0.0, 'atol': None}" <<<"$LIST_INF" && grep -q "error=''" <<<"$LIST_INF" && inf_listed_null=1
inf_500=0; [ "${R_INF%% *}" = 500 ] && inf_500=1
if [ "$inf_listed_null" = 1 ] && [ "$inf_500" = 1 ]; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
