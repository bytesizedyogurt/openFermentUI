#!/usr/bin/env bash
# H1-08: a thing whose configurations are ["one", " two "] passes the service's shape check and is listed so,
# and every door (the run route, the parameters route, the engine_run tool) strips the configuration a request
# names, then refuses "two" as none of the thing's configurations; " two " can never be run or read.
# Run from the repository root: bash bughunt/repro/H1-08/run.sh
#
# The stand-in engine h108 (standin/, written by hand for this reproduction) registers under
# `openferment.engines` through a dist-info made in a scratch directory and put on PYTHONPATH, so nothing is
# installed into any venv and nothing in core/ is edited (PYTHONDONTWRITEBYTECODE keeps even bytecode out).
# The service is the repository's own, keyless (an empty key stands over core/.env, every proxy variable
# points at a closed port), on 127.0.0.1:9760 over a fresh database bh_r_h1_08_svc, dropped at the end.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh

HERE=$BH_ROOT/bughunt/repro/H1-08
DB=bh_r_h1_08_svc
PORT=9760
O=http://127.0.0.1:$PORT
PROJ=h108
W=$BH_WORK/H1-08/run-$$
DEAD=http://127.0.0.1:9

cleanup() {
  bh_svc_stop "$PORT" 2>/dev/null
  bh_db_drop "$DB" 2>/dev/null
  rm -rf "$W"
  rmdir "$BH_WORK/H1-08" 2>/dev/null
}
trap cleanup EXIT
mkdir -p "$W/site" "$W/out"

# The stand-in package and its dist-info: importlib.metadata finds a distribution on any sys.path entry.
cp -R "$HERE/standin/h108standin" "$W/site/"
DI=$W/site/openferment_engine_h108-0.1.0.dist-info
mkdir -p "$DI"
printf 'Metadata-Version: 2.1\nName: openferment-engine-h108\nVersion: 0.1.0\n' > "$DI/METADATA"
printf '[openferment.engines]\nh108 = h108standin.engine:ENGINE\n' > "$DI/entry_points.txt"
cp -R "$BH_DATA_SRC" "$W/data"
WLOG=$W/out/worker-ops.jsonl; : > "$WLOG"

if ! bh_db_fresh "$DB"; then
  echo "EXPECTED: a fresh database for the service"
  echo "OBSERVED: bh_db_fresh $DB failed; nothing was checked"
  echo "RESULT: NO-DEFECT"; exit 0
fi

echo "== the service on $O over $DB, the stand-in engine h108 on PYTHONPATH"
(
  cd "$BH_ROOT/core" || exit 1
  bh_env PYTHONPATH="$W/site" PYTHONDONTWRITEBYTECODE=1 H108_WORKER_LOG="$WLOG" \
    HTTPS_PROXY=$DEAD HTTP_PROXY=$DEAD https_proxy=$DEAD http_proxy=$DEAD \
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

echo "== GET /api/engines: h108's thing cfg as listed"
curl -s --noproxy '*' "$O/api/engines" "${H[@]}" -o "$W/out/engines.json" -w '[%{http_code}]\n'
LISTED=$(python3 - "$W/out/engines.json" <<'PY'
import json, sys
for e in json.load(open(sys.argv[1])):
    if e["name"] == "h108":
        things = [(t["id"], t["configurations"], t["defaultConfiguration"]) for t in e.get("things") or []]
        print(f"h108: things={things!r} error={(e.get('error') or '')[:200]!r}")
PY
)
echo "$LISTED"

# body FILE: the answer's code and its body, the body's first 260 bytes.
show() { echo "$1 $(head -c 260 "$2")"; }
run() {  # run TAG CONFIGURATION-JSON
  local code
  code=$(curl -s --noproxy '*' -m 60 -X POST "$O/api/engines/h108/run" "${H[@]}" \
    -d "{\"thing\":\"cfg\",\"configuration\":$2,\"by\":\"H1-08\"}" -o "$W/out/run-$1.out" -w '%{http_code}')
  show "$code" "$W/out/run-$1.out"
}

echo "== control: POST /api/engines/h108/run {thing: cfg, configuration: \"one\"}"
R_ONE=$(run one '"one"'); echo "$R_ONE" | cut -c1-200
echo "== the case: POST /api/engines/h108/run {thing: cfg, configuration: \" two \"} (the name as listed)"
R_TWO=$(run sp '" two "'); echo "$R_TWO"
echo "== and with the name stripped: POST /api/engines/h108/run {thing: cfg, configuration: \"two\"}"
R_BARE=$(run bare '"two"'); echo "$R_BARE"

echo "== the case: GET /api/engines/h108/parameters?thing=cfg&configuration=%20two%20"
P_CODE=$(curl -s --noproxy '*' -m 60 -G "$O/api/engines/h108/parameters" "${H[@]}" \
  --data-urlencode 'thing=cfg' --data-urlencode 'configuration= two ' -o "$W/out/params.out" -w '%{http_code}')
P_TWO=$(show "$P_CODE" "$W/out/params.out"); echo "$P_TWO"

echo "== the case: POST /api/tools/engine_run {engine: h108, plant: cfg, configuration: \" two \"}"
curl -s --noproxy '*' -m 60 -X POST "$O/api/tools/engine_run?by=H1-08" "${H[@]}" \
  -d '{"engine":"h108","plant":"cfg","configuration":" two "}' -o "$W/out/tool.out" -w '[%{http_code}]\n'
T_TWO=$(python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print('error:', d.get('error'))" "$W/out/tool.out")
echo "$T_TWO"

OPS=$(python3 -c "
import json, sys
rows = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
print(sorted({(r['op'], r['configuration']) for r in rows}))" "$WLOG")
echo "the run and parameters ops the worker received, by configuration: $OPS"
ROWS=$(psql "$BH_SERVER/$DB" -XAtc "SELECT coalesce(string_agg(DISTINCT coalesce(body->>'configuration','null') || ':' || coalesce(body->>'status',''), ', '), 'none') FROM openferment.runs WHERE project_id = '$PROJ' AND engine = 'h108'")
echo "runs rows kept for h108 (configuration:status): $ROWS"

echo
echo "EXPECTED: docs/api/engines.md:231-232 holds each of a thing's configurations to \"each name 1 to 80 characters\", and engines.md:242-248 refuses only \"a configuration the thing does not name\", at every door; so either h108's things answer naming the configuration \" two \" is refused (the thing set aside in words), or \" two \", a name the thing lists, runs at the run route and is read at the parameters route and the engine_run tool"
echo "OBSERVED: listing: $LISTED"
echo "OBSERVED: run in \" two \": $R_TWO"
echo "OBSERVED: run in \"two\": $R_BARE"
echo "OBSERVED: parameters in \" two \": $P_TWO"
echo "OBSERVED: engine_run tool in \" two \": $T_TWO"
echo "OBSERVED: worker ops received: $OPS; runs rows: $ROWS"
echo "CONTROL:  run in \"one\": $(cut -c1-120 <<<"$R_ONE") ..."

listed=0; grep -qF "('cfg', ['one', ' two '], 'one')" <<<"$LISTED" && grep -q "error=''" <<<"$LISTED" && listed=1
ctl=0; [ "${R_ONE%% *}" = 200 ] && ctl=1
words="'two' is none of them"
run_ref=0; [ "${R_TWO%% *}" = 422 ] && grep -qF "$words" <<<"$R_TWO" && run_ref=1
bare_ref=0; [ "${R_BARE%% *}" = 422 ] && grep -qF "$words" <<<"$R_BARE" && bare_ref=1
par_ref=0; [ "${P_TWO%% *}" = 422 ] && grep -qF "$words" <<<"$P_TWO" && par_ref=1
tool_ref=0; grep -qF "$words" <<<"$T_TWO" && tool_ref=1
reached=0; grep -qF "' two '" <<<"$OPS" && reached=1
echo "checks: listed=$listed control=$ctl run_refused=$run_ref bare_refused=$bare_ref params_refused=$par_ref tool_refused=$tool_ref worker_saw_two=$reached"
if [ "$listed$ctl$run_ref$bare_ref$par_ref$tool_ref$reached" = 1111110 ]; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
