#!/usr/bin/env bash
# H9-06: with OPENFERMENT_ROUTES set to a table that cannot route, POST /api/ask and
# POST /api/intake/{id}/extract answer 500 Internal Server Error, the RoutesInvalid words lost.
# Two services of the head on fresh databases: 10040 with the table {"plan": {"models": []}},
# 10041 with no table (the control). Keyless; the model API names 127.0.0.1:10049, where nothing
# listens, so no request can leave the machine and none is spent.
# usage, from the repository root: bash bughunt/repro/H9-06/run.sh
source /home/user/openFermentUI/bughunt/lib/env.sh
DB=bh_r_h9_06_routes; DBC=bh_r_h9_06_control
PORT=10040; PORTC=10041; DEAD=10049
TABLE='{"plan": {"models": []}}'
T=$BH_WORK/H9-06; mkdir -p "$T"
cleanup() { bh_svc_stop "$PORT"; bh_svc_stop "$PORTC"; bh_db_drop "$DB"; bh_db_drop "$DBC";
            rm -rf "$BH_WORK/data-$DB" "$BH_WORK/data-$DBC" "$T"; }
trap cleanup EXIT

# start NAME PORT ROUTES: the head's service, keyless, the model API on the dead loopback port.
start() {
  local n="$1" port="$2" routes="$3" data; data=$(bh_data "$n")
  bh_db_fresh "$n" 2>/dev/null || return 1
  (
    cd "$BH_ROOT/core" || exit 1
    bh_env OPENFERMENT_DATABASE_URL="$BH_SERVER/$n" OPENFERMENT_DATA_DIR="$data" \
      OPENFERMENT_SFF_LIBRARY="$data/sff-library" OPENFERMENT_DIST_DIR="$BH_ROOT/dist" \
      OPENFERMENT_POLL_HOST=127.0.0.1 OPENFERMENT_PORT="$port" \
      OPENFERMENT_ROUTES="$routes" OPENFERMENT_LOCAL_BASE_URL= OPENFERMENT_WORKSPACE_ID= \
      ANTHROPIC_BASE_URL="http://127.0.0.1:$DEAD" \
      setsid .venv/bin/python -m uvicorn openferment_core.api:app --host 127.0.0.1 --port "$port" \
      --log-level warning < /dev/null > "$T/svc-$port.log" 2>&1 &
  )
  local i; for i in $(seq 1 240); do
    curl -sf --noproxy '*' "http://127.0.0.1:$port/api/health" >/dev/null 2>&1 && { echo "http://127.0.0.1:$port"; return 0; }
    sleep 0.5
  done
  return 1
}

echo "EXPECTED: core/openferment_core/api.py:554-556 says of POST /api/ask: \"Every failure below returns a plan"
echo "EXPECTED: with \`declined\` set rather than an HTTP error\"; ADR-008 6.3 says OPENFERMENT_ROUTES is \"refused in"
echo "EXPECTED: words when it cannot route (\`RoutesInvalid\`...)\". So under the table $TABLE"
echo "EXPECTED: POST /api/ask answers 200 with a plan whose declined holds the RoutesInvalid words, and the"
echo "EXPECTED: extraction route a refusal in words (a 503 with its detail, as for no key), as the control's"
echo "EXPECTED: keyless ask on the plain table answers 200 with declined set."

O=$(start "$DB" "$PORT" "$TABLE") || { echo "OBSERVED: the service on $PORT did not start"; echo "RESULT: NO-DEFECT"; exit 0; }
OC=$(start "$DBC" "$PORTC" "") || { echo "OBSERVED: the control service on $PORTC did not start"; echo "RESULT: NO-DEFECT"; exit 0; }
H=(-H 'X-OpenFerment-Project: h906' -H 'content-type: application/json')
bh_project "$O" h906 >/dev/null; bh_project "$OC" h906 >/dev/null

echo "## GET /api/health on $PORT (the table laid over): $(curl -s --noproxy '*' -w ' [%{http_code}]' "$O/api/health")"

ask=$(curl -s --noproxy '*' -o "$T/ask.body" -w '%{http_code}' -X POST "$O/api/ask" "${H[@]}" -d '{"question":"What does the yeast ferment?"}')
echo "## POST /api/ask on $PORT: [$ask] $(head -c 300 "$T/ask.body")"

doc=$(curl -s --noproxy '*' -X POST "$O/api/intake/paste" "${H[@]}" \
      -d '{"title":"Notes","text":"Yeast ferments glucose to ethanol. Xylose is not consumed.","by":"H9-06 repro"}' \
      | python3 -c 'import json,sys; print(json.load(sys.stdin).get("documentId",""))' 2>/dev/null)
ext=$(curl -s --noproxy '*' -o "$T/ext.body" -w '%{http_code}' -X POST "$O/api/intake/$doc/extract" "${H[@]}")
echo "## POST /api/intake/$doc/extract on $PORT: [$ext] $(head -c 300 "$T/ext.body")"

ctl=$(curl -s --noproxy '*' -o "$T/ctl.body" -w '%{http_code}' -X POST "$OC/api/ask" "${H[@]}" -d '{"question":"What does the yeast ferment?"}')
ctl_declined=$(python3 -c 'import json,sys; print((json.load(open(sys.argv[1])).get("declined") or "")[:200])' "$T/ctl.body" 2>/dev/null)
echo "## control POST /api/ask on $PORTC (no table): [$ctl] declined: $ctl_declined"

named=$(grep -c "RoutesInvalid: OPENFERMENT_ROUTES.plan.models is a list of model specs" "$T/svc-$PORT.log")
echo "## the service log on $PORT: $(grep -c 'Exception in ASGI application' "$T/svc-$PORT.log") unhandled exception(s), $named naming RoutesInvalid; the last frames:"
grep -E 'File ".*(postdoc_agent|extract|llm|api)\.py"|^[ |]*openferment_core\.llm\.RoutesInvalid' "$T/svc-$PORT.log" \
  | sed -E 's/^[ |]+//; s#/home/user/openFermentUI/##' | awk '!seen[$0]++' | sed 's/^/   /' 

echo "OBSERVED: POST /api/ask answered [$ask] '$(head -c 60 "$T/ask.body")'; POST /api/intake/<doc>/extract answered [$ext] '$(head -c 60 "$T/ext.body")';"
echo "OBSERVED: the RoutesInvalid words reach the service log alone ($named line(s)); the control ask answered [$ctl] with declined set."
if [ "$ask" = 500 ] && [ "$ext" = 500 ] && [ "${named:-0}" -gt 0 ]; then echo "RESULT: DEFECT"; else echo "RESULT: NO-DEFECT"; fi
exit 0
