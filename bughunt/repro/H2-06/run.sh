#!/usr/bin/env bash
# H2-06: a plant's package-test read naming no configuration answers null, while its run naming none runs in
# its default configuration and is held to that configuration's package test.
# The head's own service on a fresh database, port 9494; keyless, no model call. One BioSTEAM run of oilcane.
# usage, from the repository root: bash bughunt/repro/H2-06/run.sh
source /home/user/openFermentUI/bughunt/lib/env.sh
HERE=/home/user/openFermentUI/bughunt/repro/H2-06
DB=bh_r_h2_06_svc
PORT=9494
PLANT=oilcane
P=h206
T=$BH_WORK/H2-06; mkdir -p "$T"
cleanup() { bh_svc_stop "$PORT"; bh_db_drop "$DB"; rm -rf "$BH_WORK/data-$DB" "$T"; }
trap cleanup EXIT

# get PATH / post PATH BODY: the body on stdout, the status in $T/status.
get()  { curl -s --noproxy '*' -o "$T/body" -w '%{http_code}' -H "X-OpenFerment-Project: $P" "$O$1" > "$T/status"; cat "$T/body"; }
post() { curl -s --noproxy '*' -o "$T/body" -w '%{http_code}' -H "X-OpenFerment-Project: $P" \
              -H 'content-type: application/json' -X POST -d "$2" --max-time 1500 "$O$1" > "$T/status"; cat "$T/body"; }

echo "EXPECTED: GET /api/library/$PLANT/regression, naming no configuration, answers the package test of the"
echo "EXPECTED: configuration a run naming none runs in (the plant's default), as GET /api/library/$PLANT/parameters"
echo "EXPECTED: and POST /api/library/$PLANT/run take that default (docs/api/engines.md:629-633); it answers null"
echo "EXPECTED: only when the plant has no package test (core/openferment_core/api.py:1312-1313)."

O=$(bh_svc_start "$DB" "$PORT") || { echo "OBSERVED: the service did not start"; echo "RESULT: NO-DEFECT"; exit 0; }
bh_project "$O" "$P" >/dev/null

# 1. The shelf: the plant's configurations and the package tests it names (no worker).
get /api/library | python3 -c "
import json,sys; p=[p for p in json.load(sys.stdin)['plants'] if p['id']=='$PLANT'][0]
print('shelf: %s configurations %s, requiresConfiguration %s, tests %s' % (p['id'], p['configurations'], p.get('requiresConfiguration'), p['tests'][:3]+['...']))"
# 2. The configuration a run naming none takes, as the biosteam engine names it (no worker).
DEF=$(get /api/engines | python3 -c "
import json,sys
for e in json.load(sys.stdin):
    for t in (e.get('things') or []):
        if e.get('name')=='biosteam' and t.get('id')=='$PLANT': print(t.get('defaultConfiguration') or '')")
echo "GET /api/engines: biosteam's $PLANT runs, naming no configuration, in: ${DEF:-<none>}"
# 3. The package-test read naming no configuration, then naming the default.
NONE=$(get /api/library/$PLANT/regression); NONE_ST=$(cat "$T/status")
echo "GET /api/library/$PLANT/regression -> $NONE_ST $NONE"
NAMED=$(get "/api/library/$PLANT/regression?configuration=$DEF" | python3 -c "
import json,sys; d=json.load(sys.stdin); print('%s %d' % (d['test'], len(d['values'])) if d else 'null')")
echo "GET /api/library/$PLANT/regression?configuration=$DEF -> $(cat "$T/status") test, values: $NAMED"

# 4. The reference page, before any run of the plant, in headless Chromium over the built app.
SCR=$(cd "$HERE" && node screen.mjs "$O" "$P" "$PLANT" 2>&1 | tail -1)
echo "page /p/$P/proforma/reference/$PLANT before a run: $SCR"

# 5. A run naming no configuration (BioSTEAM builds and runs the plant in the worker; about two minutes).
post /api/library/$PLANT/run '{"by":"H2-06 repro"}' > "$T/run.json"
RUN=$(python3 -c "
import json,sys
try: d=json.load(open('$T/run.json'))
except Exception as e: print('unreadable', e); sys.exit()
r=d.get('run') or {}; o=(r.get('outputs') or {}); reg=o.get('regression') or {}
art=(d.get('artifact') or {}).get('output') or {}; areg=art.get('regression') or {}; ch=art.get('checks') or []
print('configuration=%s status=%s outputs.regression=%s artifact.regression.test=%s checks=%d/%d within' % (
  r.get('configuration'), r.get('status'), json.dumps(reg), areg.get('test'), sum(1 for c in ch if c.get('within')), len(ch)))")
echo "POST /api/library/$PLANT/run {} -> $(cat "$T/status") $RUN"

RUN_CFG=$(echo "$RUN" | sed -n 's/.*configuration=\([^ ]*\).*/\1/p')
RUN_TEST=$(echo "$RUN" | sed -n 's/.*artifact.regression.test=\([^ ]*\).*/\1/p')
echo "OBSERVED: the read naming no configuration answered $NONE; naming $DEF it answered ${NAMED%% *};"
echo "OBSERVED: the run naming none ran in $RUN_CFG and was held to $RUN_TEST."
echo "OBSERVED: the page said: $(echo "$SCR" | python3 -c "import json,sys
try: d=json.loads(sys.stdin.read()); print('[header]', d.get('heldTo'), d.get('configuration'), '[card]', d.get('card'))
except Exception: print('(the page probe gave no JSON)')")"
if [ "$NONE" = "null" ] && [ -n "$DEF" ] && [ "${NAMED%% *}" = "test_${PLANT}_$DEF" ] \
   && [ "$RUN_CFG" = "$DEF" ] && [ "$RUN_TEST" = "test_${PLANT}_$DEF" ]; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
