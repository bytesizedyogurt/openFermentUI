#!/usr/bin/env bash
# H9-01: POST /api/literature/answer with X-OpenFerment-Key makes its model call on the key the
# service's environment holds (core/.env's), while the request's audit row says an override was used.
# The model API is a loopback stand-in that records each request's x-api-key and answers every one
# with an error, so no request leaves the machine and nothing is spent. Both keys are sentinels
# made fresh each run: ENVKEY stands where core/.env's key would, SENTINEL is the request's own.
#   bash bughunt/repro/H9-01/run.sh        (from the repository root)
source /home/user/openFermentUI/bughunt/lib/env.sh
export PYTHONDONTWRITEBYTECODE=1 PGOPTIONS="-c client_min_messages=warning"
HERE=/home/user/openFermentUI/bughunt/repro/H9-01
PORT=9350; STANDIN=9351; DB=bh_r_h9_01_key; P=pk; RAGKEY=bh-r-h9-01-ragkey
W="$BH_WORK/H9-01/run"; rm -rf "$W"; mkdir -p "$W"; REC="$W/standin.jsonl"; : > "$REC"
O="http://127.0.0.1:$PORT"
ENVKEY="BUGHUNT-ENVKEY-$(openssl rand -hex 8)"; SENT="BUGHUNT-SENTINEL-$(openssl rand -hex 12)"
DEAD=http://127.0.0.1:9   # every proxy setting points nowhere: only loopback is reachable

cleanup() {
  bh_svc_stop "$PORT" >/dev/null 2>&1
  pkill -f "standin_model_api.py $STANDIN" >/dev/null 2>&1
  bh_db_drop "$DB" >/dev/null 2>&1
  rm -rf "$BH_WORK/data-$DB" "$W"; rmdir "$BH_WORK/H9-01" 2>/dev/null
}
trap cleanup EXIT

# 1. The stand-in model API, then the service over a fresh database: ANTHROPIC_BASE_URL names the
#    stand-in, ANTHROPIC_API_KEY is ENVKEY, the kit's REST door has a key of its own for the control.
setsid python3 "$HERE/standin_model_api.py" "$STANDIN" "$REC" 400 </dev/null >/dev/null 2>&1 &
sleep 0.5
bh_db_fresh "$DB" || { echo "RESULT: NO-DEFECT (setup failed: database)"; exit 0; }
data=$(bh_data "$DB")
(
  cd "$BH_ROOT/core" || exit 1
  bh_env OPENFERMENT_DATABASE_URL="$BH_SERVER/$DB" OPENFERMENT_DATA_DIR="$data" \
    OPENFERMENT_SFF_LIBRARY="$data/sff-library" OPENFERMENT_DIST_DIR="$BH_ROOT/dist" \
    OPENFERMENT_POLL_HOST=127.0.0.1 OPENFERMENT_PORT="$PORT" \
    OPENFERMENT_ROUTES= OPENFERMENT_LOCAL_BASE_URL= OPENFERMENT_WORKSPACE_ID= \
    OPENFERMENT_RAG_KEY="$RAGKEY" ANTHROPIC_API_KEY="$ENVKEY" \
    ANTHROPIC_BASE_URL="http://127.0.0.1:$STANDIN" \
    HTTPS_PROXY="$DEAD" HTTP_PROXY="$DEAD" ALL_PROXY="$DEAD" https_proxy="$DEAD" http_proxy="$DEAD" \
    all_proxy="$DEAD" NO_PROXY=127.0.0.1,localhost no_proxy=127.0.0.1,localhost HF_HUB_OFFLINE=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    setsid .venv/bin/python -m uvicorn openferment_core.api:app --host 127.0.0.1 --port "$PORT" \
    --log-level warning < /dev/null > "$W/svc.log" 2>&1 &
)
up=0; for i in $(seq 1 240); do
  curl -sf --noproxy '*' "$O/api/health" >/dev/null 2>&1 && { up=1; break; }; sleep 0.5; done
[ "$up" = 1 ] || { echo "service did not start:"; tail -20 "$W/svc.log"; echo "RESULT: NO-DEFECT (setup failed: service)"; exit 0; }

# 2. A project and one pasted document, so retrieval finds a passage and the answer asks the model.
bh_project "$O" "$P" >/dev/null
DOC=$(curl -s --noproxy '*' -X POST "$O/api/intake/paste" -H "X-OpenFerment-Project: $P" \
  -H 'content-type: application/json' \
  -d '{"title":"Ethanol fermentation notes","text":"Saccharomyces cerevisiae ferments glucose to ethanol under anaerobic conditions. Xylose is not consumed by the wild type strain.","by":"Tester Person"}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin).get("documentId",""))' 2>/dev/null)
[ -n "$DOC" ] || { echo "paste failed:"; tail -20 "$W/svc.log"; echo "RESULT: NO-DEFECT (setup failed: paste)"; exit 0; }
echo "document: $DOC; model requests before the two asks: $(wc -l < "$REC" | tr -d ' ')"

# 3. The subject and the control, each naming SENTINEL in X-OpenFerment-Key; the audit rows.
bh_py "$HERE/drive.py" "$O" "$P" "$SENT" "$ENVKEY" "$REC" "$RAGKEY" "$W/out.json" \
  || { echo "RESULT: NO-DEFECT (setup failed: driver)"; exit 0; }
echo "## the request's key in the service log: $(grep -c "$SENT" "$W/svc.log") lines"

# 4. The cause, without the service: a context variable set around a plain threading.Thread is
#    gone inside it (kit.answer's pump thread), and present in asyncio.to_thread (the REST door's path).
echo "## the cause, in the repository's Python:"
bh_py - <<'PY'
import asyncio, threading
from openferment_core import llm
seen = {}
with llm.request_key("a-key-the-request-names"):
    t = threading.Thread(target=lambda: seen.__setitem__("threading.Thread", llm.key_named()))
    t.start(); t.join()
    async def main():
        seen["asyncio.to_thread"] = await asyncio.to_thread(llm.key_named)
    asyncio.run(main())
print(f"  inside llm.request_key: key_named() in a threading.Thread = {seen['threading.Thread']}; "
      f"in asyncio.to_thread = {seen['asyncio.to_thread']}")
PY

echo "EXPECTED: every model request POST /api/literature/answer makes carries the request's key (x-api-key = SENTINEL), as POST /rag/v1/answer's do; the audit row's override:true then holds"
python3 - "$W/out.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
s, c = d["subject"], d["control"]
print(f"OBSERVED: /api/literature/answer sent {s['modelRequests']} model request(s) carrying {s['keysUsed']}; "
      f"/rag/v1/answer sent {c['modelRequests']} carrying {c['keysUsed']}; "
      f"key_override audit row for POST /api/literature/answer with override true: {d['audited']}")
wrong = s["modelRequests"] > 0 and any(k != "SENTINEL" for k in s["keysUsed"])
control_ok = c["modelRequests"] > 0 and all(k == "SENTINEL" for k in c["keysUsed"])
if s["modelRequests"] == 0:
    print("RESULT: NO-DEFECT (the subject sent no model request, so nothing was shown)")
elif not control_ok:
    print("RESULT: NO-DEFECT (the control did not carry the request's key, so the setup shows nothing)")
else:
    print("RESULT: " + ("DEFECT" if wrong else "NO-DEFECT"))
PY
exit 0
