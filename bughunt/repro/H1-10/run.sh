#!/usr/bin/env bash
# H1-10: once the Proforma worker has answered, GET /api/engines lists biosteam's and train's workerStatus
# as `ready` whatever becomes of the process: after the worker is killed no Proforma worker lives and both
# still read `ready` (and GET /api/proforma/status says `ready` too), where a WorkerEngine whose worker died
# reads `cold`.
# Run from the repository root: bash bughunt/repro/H1-10/run.sh
#
# The repository's own service (core/ at 2047f5a, read and run, never edited), keyless: an empty key stands
# over core/.env and every proxy variable points at a closed port, so no request leaves the machine.
# PYTHONDONTWRITEBYTECODE keeps even bytecode out of core/. 127.0.0.1:10360 over a fresh database
# bh_r_h1_10_svc; OPENFERMENT_WARM_PROFORMA=1 makes the service start the Proforma worker itself (a ping,
# no plant is built). The control is a WorkerEngine over the tree's echo worker, in a process of its own.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh

DB=bh_r_h1_10_svc
PORT=10360
O=http://127.0.0.1:$PORT
PROJ=h110
W=$BH_WORK/H1-10/run-$$
DEAD=http://127.0.0.1:9

cleanup() {
  bh_svc_stop "$PORT" 2>/dev/null
  bh_db_drop "$DB" 2>/dev/null
  rm -rf "$W"
  rmdir "$BH_WORK/H1-10" 2>/dev/null
}
trap cleanup EXIT
mkdir -p "$W/out"
cp -R "$BH_DATA_SRC" "$W/data"

if [ "$(git -C "$BH_ROOT" diff --name-only 2047f5a -- core src scripts examples | wc -l)" != 0 ]; then
  echo "note: the tree's core/, src/, scripts/ or examples/ differ from 2047f5a"
fi

# The Proforma workers alive under the service: children of the service's pid, zombies left out.
workers_alive() {
  local svc; svc=$(bh_port_pid "$PORT")
  ps -o pid=,stat=,args= --ppid "$svc" 2>/dev/null | awk '$2 !~ /^Z/ && /proforma_worker/ {n++} END {print n+0}'
}
worker_pid() {
  local svc; svc=$(bh_port_pid "$PORT")
  ps -o pid=,stat=,args= --ppid "$svc" 2>/dev/null | awk '$2 !~ /^Z/ && /proforma_worker/ {print $1; exit}'
}
# The listing's workerStatus for biosteam and train, one "name=status" pair a word.
listed() {
  curl -s --noproxy '*' -m 120 "$O/api/engines" -H "X-OpenFerment-Project: $PROJ" -o "$W/out/engines-$1.json" \
    -w '' || true
  python3 - "$W/out/engines-$1.json" <<'PY'
import json, sys
try:
    rows = json.load(open(sys.argv[1]))
except Exception as e:
    print(f"unreadable listing: {e}"); sys.exit(0)
print(" ".join(f"{e['name']}={e['workerStatus']}" for e in rows if e.get("name") in ("biosteam", "train")))
PY
}
sim_status() {
  curl -s --noproxy '*' -m 30 "$O/api/proforma/status" -H "X-OpenFerment-Project: $PROJ" \
    | python3 -c "import json,sys; print(json.load(sys.stdin).get('status'))" 2>/dev/null
}

if ! bh_db_fresh "$DB"; then
  echo "EXPECTED: a fresh database for the service"
  echo "OBSERVED: bh_db_fresh $DB failed; nothing was checked"
  echo "RESULT: NO-DEFECT"; exit 0
fi

echo "== the service on $O over $DB, OPENFERMENT_WARM_PROFORMA=1"
(
  cd "$BH_ROOT/core" || exit 1
  bh_env PYTHONDONTWRITEBYTECODE=1 OPENFERMENT_WARM_PROFORMA=1 \
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

echo "== wait for the warm start: GET /api/proforma/status until ready (up to 300 s)"
t0=$(date +%s); st=""
for i in $(seq 1 300); do
  st=$(sim_status); [ "$st" = ready ] || [ "$st" = failed ] && break
  sleep 1
done
echo "GET /api/proforma/status: $st after $(( $(date +%s) - t0 )) s"
if [ "$st" != ready ]; then
  echo "EXPECTED: the Proforma worker warms and reads ready"
  echo "OBSERVED: it reads $st; the log ends: $(tail -3 "$W/svc.log" | tr '\n' ' ')"
  echo "RESULT: NO-DEFECT"; exit 0
fi

echo "== before the kill"
B_ALIVE=$(workers_alive)
B_LIST=$(listed before)
echo "Proforma workers alive under the service: $B_ALIVE"
echo "GET /api/engines workerStatus: $B_LIST"

WPID=$(worker_pid)
echo "== SIGKILL the Proforma worker (pid $WPID)"
[ -n "$WPID" ] && kill -KILL "$WPID"
for i in $(seq 1 20); do [ "$(workers_alive)" = 0 ] && break; sleep 0.25; done

echo "== after the kill"
A_ALIVE=$(workers_alive)
A_LIST=$(listed after)
A_SIM=$(sim_status)
A_ALIVE2=$(workers_alive)
echo "Proforma workers alive under the service: $A_ALIVE"
echo "GET /api/engines workerStatus: $A_LIST"
echo "GET /api/proforma/status: $A_SIM"
echo "Proforma workers alive after both reads (the reads start none): $A_ALIVE2"

echo "== control: a WorkerEngine over the tree's echo worker, read through registry.status_of as the listing reads it"
CTRL=$(cd "$BH_ROOT/core" && bh_env PYTHONDONTWRITEBYTECODE=1 timeout 120 .venv/bin/python - <<'PY'
import os, signal, time
from openferment_core.engine.contract import WorkerEngine
from openferment_core.engine.registry import status_of
e = WorkerEngine(name="h110", worker="openferment_core.workers.echo_worker")
first = status_of(e)
e.call("echo", {"x": 1})
warm = status_of(e)
os.kill(e._sim._proc.pid, signal.SIGKILL)
for _ in range(40):
    if e._sim._proc.poll() is not None:
        break
    time.sleep(0.05)
print(f"before first use={first} after an answer={warm} after its worker was killed={status_of(e)}")
PY
)
echo "WorkerEngine: ${CTRL:-the control did not run}"

echo
echo "EXPECTED: workerStatus says where the worker is: contract.py:104-106 gives a WorkerEngine \"ready\" while the worker's process answers and \"cold\" before its first use, and simulator.py:7-8 says status() \"says where it is: cold, starting, ready or failed\"; so with no Proforma worker alive biosteam and train read cold (or failed), as the WorkerEngine control reads cold after its worker is killed"
echo "OBSERVED: before the kill $B_ALIVE worker alive, listing [$B_LIST]; after the kill $A_ALIVE alive, listing [$A_LIST], /api/proforma/status $A_SIM, and $A_ALIVE2 alive after the reads; control [${CTRL:-none}]"

if [ "$B_ALIVE" -ge 1 ] && [ "$A_ALIVE" = 0 ] && [ "$A_ALIVE2" = 0 ] \
   && echo "$A_LIST" | grep -q 'biosteam=ready' && echo "$A_LIST" | grep -q 'train=ready'; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
