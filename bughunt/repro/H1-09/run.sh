#!/usr/bin/env bash
# H1-09: a contract engine's run op that answers the output {name, value, unit, stray: 42} is accepted as in
# shape; the run is kept done, and its artifact keeps the stray number in its output, in its hash and in what
# its replay compares. The control, an output with no unit, is refused 503 as no name, value and unit.
# Run from the repository root: bash bughunt/repro/H1-09/run.sh
#
# The stand-in engine h109 (standin/, written by hand for this reproduction) registers under
# `openferment.engines` through a dist-info made in a scratch directory and put on PYTHONPATH, so nothing is
# installed into any venv and nothing in core/ is edited (PYTHONDONTWRITEBYTECODE keeps even bytecode out).
# The service is the repository's own, keyless (an empty key stands over core/.env, every proxy variable
# points at a closed port), on 127.0.0.1:10060 over a fresh database bh_r_h1_09_svc, dropped at the end.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh

HERE=$BH_ROOT/bughunt/repro/H1-09
DB=bh_r_h1_09_svc
PORT=10060
O=http://127.0.0.1:$PORT
PROJ=h109
W=$BH_WORK/H1-09/run-$$
DEAD=http://127.0.0.1:9

cleanup() {
  bh_svc_stop "$PORT" 2>/dev/null
  bh_db_drop "$DB" 2>/dev/null
  rm -rf "$W"
  rmdir "$BH_WORK/H1-09" 2>/dev/null
}
trap cleanup EXIT
mkdir -p "$W/site" "$W/out"

# The stand-in package and its dist-info: importlib.metadata finds a distribution on any sys.path entry.
cp -R "$HERE/standin/h109standin" "$W/site/"
DI=$W/site/openferment_engine_h109-0.1.0.dist-info
mkdir -p "$DI"
printf 'Metadata-Version: 2.1\nName: openferment-engine-h109\nVersion: 0.1.0\n' > "$DI/METADATA"
printf '[openferment.engines]\nh109 = h109standin.engine:ENGINE\n' > "$DI/entry_points.txt"
cp -R "$BH_DATA_SRC" "$W/data"

if ! bh_db_fresh "$DB"; then
  echo "EXPECTED: a fresh database for the service"
  echo "OBSERVED: bh_db_fresh $DB failed; nothing was checked"
  echo "RESULT: NO-DEFECT"; exit 0
fi

echo "== the service on $O over $DB, the stand-in engine h109 on PYTHONPATH"
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

echo "== GET /api/engines: h109 as listed"
curl -s --noproxy '*' "$O/api/engines" "${H[@]}" -o "$W/out/engines.json" -w '[%{http_code}]\n'
python3 - "$W/out/engines.json" <<'PY'
import json, sys
for e in json.load(open(sys.argv[1])):
    if e["name"] == "h109":
        print(f"h109: things={[t['id'] for t in e.get('things') or []]} error={(e.get('error') or '')[:200]!r}")
PY

echo "== control: POST /api/engines/h109/run {thing: nounit} (the output {name: x, value: 1.0}, no unit)"
C_CODE=$(curl -s --noproxy '*' -m 60 -X POST "$O/api/engines/h109/run" "${H[@]}" \
  -d '{"thing":"nounit","by":"H1-09"}' -o "$W/out/nounit.json" -w '%{http_code}')
C_BODY=$(head -c 300 "$W/out/nounit.json")
echo "$C_CODE $C_BODY"

echo "== the case: POST /api/engines/h109/run {thing: extra} (the output {name: x, value: 1.0, unit: u, stray: 42})"
X_CODE=$(curl -s --noproxy '*' -m 60 -X POST "$O/api/engines/h109/run" "${H[@]}" \
  -d '{"thing":"extra","by":"H1-09"}' -o "$W/out/extra.json" -w '%{http_code}')
echo "[$X_CODE]"
python3 - "$W/out/extra.json" > "$W/out/extra.txt" <<'PY'
import json, sys
try:
    d = json.load(open(sys.argv[1]))
    r, a = d.get("run") or {}, d.get("artifact") or {}
    print("status=" + str(r.get("status")))
    print("artifact=" + str(a.get("id")))
    print("hash=" + str(a.get("outputHash")))
    print("artifact_values=" + json.dumps((a.get("output") or {}).get("values")))
    print("run_values=" + json.dumps([(v["name"], sorted(v["quantity"])) for v in (r.get("outputs") or {}).get("values") or []]))
except Exception as e:
    print("status=unreadable " + repr(e)[:200])
PY
cat "$W/out/extra.txt"
field() { sed -n "s/^$1=//p" "$W/out/extra.txt"; }
X_STATUS=$(field status); AID=$(field artifact); X_HASH=$(field hash); X_ART=$(field artifact_values); X_RUN=$(field run_values)

A_VALUES=""; HASHES=""; R_SUMMARY=""
if [ -n "$AID" ] && [ "$AID" != None ]; then
  echo "== GET /api/biorepo/artifacts/$AID: the artifact as the store keeps it"
  curl -s --noproxy '*' "$O/api/biorepo/artifacts/$AID" "${H[@]}" -o "$W/out/artifact.json" -w '[%{http_code}]\n'
  A_VALUES=$(python3 -c "import json,sys; print(json.dumps(json.load(open(sys.argv[1]))['output'].get('values')))" "$W/out/artifact.json")
  echo "kept output.values: $A_VALUES"

  echo "== the kept hash against the service's own output_hash, over the output as kept and with the stray key taken out"
  HASHES=$(cd "$BH_ROOT/core" && bh_env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -c '
import copy, json, sys
from openferment_core.artifacts import output_hash
a = json.load(open(sys.argv[1]))
out = a["output"]
bare = copy.deepcopy(out)
for v in bare.get("values") or []:
    v.pop("stray", None)
kept = a["outputHash"]
print(f"kept={kept[:16]} as_kept={output_hash(out)[:16]} three_fields={output_hash(bare)[:16]}")
' "$W/out/artifact.json" 2>&1 | tail -1)
  echo "$HASHES"

  echo "== POST /api/biorepo/artifacts/$AID/replay (the stand-in answers stray 43 on its second run of extra)"
  curl -s --noproxy '*' -m 60 -X POST "$O/api/biorepo/artifacts/$AID/replay" "${H[@]}" -o "$W/out/replay.json" -w '[%{http_code}]\n'
  R_SUMMARY=$(python3 -c "
import json, sys
d = json.load(open(sys.argv[1]))
diffs = [(x['path'], x['stored'], x['replayed']) for x in d.get('differences') or []]
print(f\"identical={d.get('identical')} withinTolerance={d.get('withinTolerance')} differences={diffs}\")" "$W/out/replay.json")
  echo "$R_SUMMARY"
fi

ROWS=$(psql "$BH_SERVER/$DB" -XAtc "SELECT coalesce(string_agg(body->>'plant' || ':' || coalesce(body->>'status',''), ', ' ORDER BY body->>'plant'), 'none') FROM openferment.runs WHERE project_id = '$PROJ' AND engine = 'h109'")
echo "runs rows kept for h109 (thing:status): $ROWS"

echo
echo "EXPECTED: docs/api/workers.md:62-68 says \"An answer outside the shapes below (a result key missing, outputs that are no list of names, values and units, ...) breaks the contract: the service raises EngineBroken, keeps no runs row and answers 503 in words\", and the run op's shape (workers.md:93-94, engines.md:456) is {\"outputs\": [{\"name\", \"value\", \"unit\"}, ...]}; so the output {name, value, unit, stray: 42} is refused 503 with no runs row, or kept as its name, value and unit alone, with no stray number in the artifact, its hash or its replay"
echo "OBSERVED: run of extra: $X_CODE, status $X_STATUS; the run's typed outputs (name, quantity keys): $X_RUN"
echo "OBSERVED: the artifact $AID keeps output.values $A_VALUES"
echo "OBSERVED: hashes: $HASHES"
echo "OBSERVED: replay: $R_SUMMARY"
echo "OBSERVED: runs rows: $ROWS"
echo "CONTROL:  run of nounit (no unit): $C_CODE $(cut -c1-200 <<<"$C_BODY")"

ctl=0; [ "$C_CODE" = 503 ] && grep -qF "no name, value and unit" <<<"$C_BODY" && ctl=1
kept=0; [ "$X_CODE" = 200 ] && [ "$X_STATUS" = done ] && kept=1
stray=0; grep -qF '"stray": 42' <<<"$A_VALUES" && grep -qF '"stray": 42' <<<"$X_ART" && stray=1
hashed=0
k=$(sed -n 's/.*kept=\([0-9a-f]*\).*/\1/p' <<<"$HASHES"); f=$(sed -n 's/.*as_kept=\([0-9a-f]*\).*/\1/p' <<<"$HASHES")
b=$(sed -n 's/.*three_fields=\([0-9a-f]*\).*/\1/p' <<<"$HASHES")
[ -n "$k" ] && [ "$k" = "$f" ] && [ "$k" != "$b" ] && hashed=1
replayed=0; grep -qF "('values[0].stray', 42, 43)" <<<"$R_SUMMARY" && ! grep -qF "values[0].value" <<<"$R_SUMMARY" \
  && grep -qF "withinTolerance=False" <<<"$R_SUMMARY" && replayed=1
echo "checks: control_refused=$ctl stray_run_kept_done=$kept stray_in_artifact=$stray stray_in_hash=$hashed stray_in_replay=$replayed"
if [ "$ctl$kept$stray$hashed$replayed" = 11111 ]; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
