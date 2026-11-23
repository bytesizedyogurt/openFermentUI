#!/usr/bin/env bash
# H1-07: a worker's things answer listing two things of one id is accepted; GET /api/engines lists both,
# and a run naming that id keeps the precision of the last one listed in its basis, with no word said.
# Run from the repository root: bash bughunt/repro/H1-07/run.sh
#
# The stand-in engine h107 (standin/, written by hand for this reproduction, its worker on the core's own
# workers.serve) registers under `openferment.engines` through a dist-info made in a scratch directory and
# put on PYTHONPATH, so nothing is installed into any venv and nothing in core/ is edited. The service is
# the repository's own, keyless (an empty key stands over core/.env, every proxy variable points at a
# closed port), on 127.0.0.1:9461 over a fresh database bh_r_h1_07_svc, dropped at the end.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh

HERE=$BH_ROOT/bughunt/repro/H1-07
DB=bh_r_h1_07_svc
PORT=9461
O=http://127.0.0.1:$PORT
PROJ=h107
W=$BH_WORK/H1-07/run-$$
DEAD=http://127.0.0.1:9

cleanup() {
  bh_svc_stop "$PORT" 2>/dev/null
  bh_db_drop "$DB" 2>/dev/null
  rm -rf "$W"
  rmdir "$BH_WORK/H1-07" 2>/dev/null
}
trap cleanup EXIT
mkdir -p "$W/site" "$W/out"

# The stand-in package and its dist-info: importlib.metadata finds a distribution on any sys.path entry.
cp -R "$HERE/standin/h107standin" "$W/site/"
DI=$W/site/openferment_engine_h107-0.1.0.dist-info
mkdir -p "$DI"
printf 'Metadata-Version: 2.1\nName: openferment-engine-h107\nVersion: 0.1.0\n' > "$DI/METADATA"
printf '[openferment.engines]\nh107 = h107standin.engine:ENGINE\n' > "$DI/entry_points.txt"
cp -R "$BH_DATA_SRC" "$W/data"

if ! bh_db_fresh "$DB"; then
  echo "EXPECTED: a fresh database for the service"
  echo "OBSERVED: bh_db_fresh $DB failed; nothing was checked"
  echo "RESULT: NO-DEFECT"; exit 0
fi

echo "== the service on $O over $DB, the stand-in engine on PYTHONPATH"
(
  cd "$BH_ROOT/core" || exit 1
  bh_env PYTHONPATH="$W/site" PYTHONDONTWRITEBYTECODE=1 \
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

echo "== GET /api/engines: h107 as listed"
curl -s --noproxy '*' "$O/api/engines" "${H[@]}" -o "$W/out/engines.json" -w '[%{http_code}]\n'
python3 - "$W/out/engines.json" > "$W/out/listed.txt" <<'PY'
import json, sys
for e in json.load(open(sys.argv[1])):
    if e["name"] == "h107":
        for t in e.get("things") or []:
            p = t["precision"]
            print(f"thing id={t['id']} title={t['title']!r} precision=({p['rtol']}, {p['atol']})")
        print(f"error={(e.get('error') or '')[:220]!r}")
PY
cat "$W/out/listed.txt"
DUPS=$(grep -c '^thing id=dup ' "$W/out/listed.txt")
LIST_ERR=$(grep '^error=' "$W/out/listed.txt")

# run THING: POST /api/engines/h107/run; prints "CODE precision.rtol=.. precision.atol=.. run=<id>".
run() {
  local code
  code=$(curl -s --noproxy '*' -m 60 -X POST "$O/api/engines/h107/run" "${H[@]}" \
    -d "{\"thing\":\"$1\",\"by\":\"H1-07\"}" -o "$W/out/run-$1.json" -w '%{http_code}')
  python3 - "$code" "$W/out/run-$1.json" <<'PY'
import json, sys
code, path = sys.argv[1], sys.argv[2]
try:
    d = json.load(open(path))
    basis = {i["name"]: i["value"] for i in d["artifact"]["inputs"]}
    print(f"{code} thing={basis.get('thing')} precision.rtol={basis.get('precision.rtol')} "
          f"precision.atol={basis.get('precision.atol')} run={d['run']['id']} status={d['run']['status']}")
except Exception as e:
    print(f"{code} unread: {open(path).read()[:300]!r} ({type(e).__name__})")
PY
}
echo "== the case: POST /api/engines/h107/run {thing: dup}"
R_DUP=$(run dup); echo "$R_DUP"
echo "== control: POST /api/engines/h107/run {thing: single}"
R_ONE=$(run single); echo "$R_ONE"
ROWS=$(psql "$BH_SERVER/$DB" -XAtc "SELECT count(*) FROM openferment.runs WHERE project_id = '$PROJ' AND engine = 'h107' AND body->>'plant' = 'dup'")
echo "runs rows kept for dup: $ROWS"

echo "== the two readers of one listing, in the tree: the service keys the things by id, the run card finds by id"
SVC_LINE=$(grep -n 'things = {x.id: x for x in engine.things()}' "$BH_ROOT/core/openferment_core/engine/runs.py" | head -1)
CARD_LINE=$(grep -n 'const thing = things.find((t) => t.id === thingId)' "$BH_ROOT/src/screens/ProformaStudies.tsx" | head -1)
echo "core/openferment_core/engine/runs.py:$SVC_LINE"
echo "src/screens/ProformaStudies.tsx:$CARD_LINE"

echo
echo "EXPECTED: a things answer listing two things of the id dup (docs/api/engines.md:229-230: \"\`id\`: ... A run names it as its \`plant\`\") is refused as outside the protocol (EngineBroken, listed with words in error, a run answered 503 with no runs row; docs/api/workers.md:62-68), or one thing of that id is listed and run"
echo "OBSERVED: listing: $DUPS things of id dup, $(grep '^thing id=dup ' "$W/out/listed.txt" | sed -E 's/^thing id=dup title=//' | tr '\n' ';' ) $LIST_ERR"
echo "OBSERVED: run of dup: $R_DUP; $ROWS runs row(s) kept"
echo "CONTROL:  run of single (precision listed 0, 0): $R_ONE"

two_listed=0
[ "$DUPS" = 2 ] && grep -q "^thing id=dup title='the first of two things of one id' precision=(0.0, 0.0)$" "$W/out/listed.txt" \
  && grep -q "^thing id=dup title='the second of two things of one id' precision=(1.0, 1.0)$" "$W/out/listed.txt" \
  && [ "$LIST_ERR" = "error=''" ] && two_listed=1
last_taken=0
grep -q '^200 thing=dup precision.rtol=1.0 precision.atol=1.0 run=' <<<"$R_DUP" && [ "$ROWS" = 1 ] && last_taken=1
if [ "$two_listed" = 1 ] && [ "$last_taken" = 1 ]; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
