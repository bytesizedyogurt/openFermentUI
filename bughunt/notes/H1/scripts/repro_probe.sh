#!/usr/bin/env bash
# H1-02, H1-05, H1-06, H1-07, H1-08: the stand-in engine package in scripts/probe-engine, installed into the venv
# of a worktree of H1's own (made at 2047f5a when missing), then probed: discovery's heavy-module count (H1-02),
# and the probe engine's things infprec, dup, cfg and extra at a service started from the worktree on bh_h1_rp,
# port 8815. usage: repro_probe.sh [WORKTREE]
source /home/user/openFermentUI/bughunt/lib/env.sh
S=/home/user/openFermentUI/bughunt/notes/H1/scripts
W=${1:-$BH_WORK/H1/wt-repro}
[ -d "$W" ] || git -C "$BH_ROOT" worktree add --detach "$W" 2047f5a >/dev/null 2>&1
[ -x "$W/core/.venv/bin/python" ] || (cd "$W/core" && bh_env uv sync --frozen --all-extras >/dev/null 2>&1)
P=$BH_WORK/H1/probe-engine-repro; rm -rf "$P"; cp -R "$S/probe-engine" "$P"
# The package as the hunt last installed it: no second claim on mirror or biosteam (those two lines are the
# duplicate-name probe, run on their own).
sed -i 's/^mirror = /#mirror = /; s/^biosteam = /#biosteam = /' "$P/pyproject.toml"
(cd "$W/core" && bh_env bash -c 'uv pip install --python .venv/bin/python -c <(uv export --frozen --all-extras --no-hashes --no-emit-project --quiet) -e '"$P" >/dev/null 2>&1)
echo "== H1-02: discovery with h1z alone, then with an earlier misnamed entry that imports cobra"
for set in "h1z-heavy-unseen" "h1a-misnamed-heavy h1z-heavy-unseen" "h1b-fails-heavy h1z-heavy-unseen"; do
  echo "-- $set"; (cd "$W/core" && bh_env OPENFERMENT_DATABASE_URL="$BH_SERVER/postgres" .venv/bin/python "$S/heavy_left.py" $set 2>&1 | grep -v INFO); done
bh_db_fresh bh_h1_rp || exit 1
D=$(bh_data bh_h1_rp)
(cd "$W/core" && bh_env OPENFERMENT_DATABASE_URL="$BH_SERVER/bh_h1_rp" OPENFERMENT_DATA_DIR="$D" OPENFERMENT_SFF_LIBRARY="$D/sff-library" \
  OPENFERMENT_DIST_DIR="$BH_ROOT/dist" setsid .venv/bin/python -m uvicorn openferment_core.api:app --host 127.0.0.1 --port 8815 \
  --log-level warning < /dev/null > "$BH_WORK/svc-8815.log" 2>&1 &)
for i in $(seq 1 120); do curl -sf --noproxy '*' http://127.0.0.1:8815/api/health >/dev/null 2>&1 && break; sleep 0.5; done
O=http://127.0.0.1:8815; bh_project "$O" h1rp >/dev/null
H=(-H 'content-type: application/json' -H 'X-OpenFerment-Project: h1rp')
echo "== H1-05, H1-06, H1-07: GET /api/engines, the probe's things infprec, dup, cfg"
curl -s --noproxy '*' "$O/api/engines" "${H[@]}" | python3 -c "
import sys, json
for e in json.load(sys.stdin):
    if e['name'] == 'probe':
        print([(t['id'], t['title'], t['configurations'], t['precision']) for t in e['things'] if t['id'] in ('infprec', 'dup', 'cfg')])"
echo "== H1-05: a run of infprec"; curl -s --noproxy '*' -X POST "$O/api/engines/probe/run" "${H[@]}" -d '{"thing":"infprec","by":"H1"}' -w ' [%{http_code}]\n'
echo "== H1-06: a run of dup, the precision its basis keeps"
curl -s --noproxy '*' -X POST "$O/api/engines/probe/run" "${H[@]}" -d '{"thing":"dup","by":"H1"}' | python3 -c "
import sys, json; d = json.load(sys.stdin); print([(i['name'], i['value']) for i in d['artifact']['inputs'] if i['name'].startswith('precision')])"
echo "== H1-07: cfg run in its listed configuration ' two ', at the run route, the parameters route and the tool"
curl -s --noproxy '*' -X POST "$O/api/engines/probe/run" "${H[@]}" -d '{"thing":"cfg","configuration":" two ","by":"H1"}' -w ' [%{http_code}]\n'
curl -s --noproxy '*' -G "$O/api/engines/probe/parameters" "${H[@]}" --data-urlencode 'thing=cfg' --data-urlencode 'configuration= two ' -w ' [%{http_code}]\n'
curl -s --noproxy '*' -X POST "$O/api/tools/engine_run?by=H1" "${H[@]}" -d '{"engine":"probe","plant":"cfg","configuration":" two "}' | python3 -c "import sys, json; print(json.load(sys.stdin).get('error'))"
echo "== H1-08: a run of extra, the artifact's output"
curl -s --noproxy '*' -X POST "$O/api/engines/probe/run" "${H[@]}" -d '{"thing":"extra","by":"H1"}' | python3 -c "
import sys, json; d = json.load(sys.stdin); print(d['run']['status'], d['artifact']['output']['values'])"
pid=$(bh_port_pid 8815); [ -n "$pid" ] && kill -TERM -- -"$(ps -o pgid= -p "$pid" | tr -d ' ')" 2>/dev/null; sleep 2
bh_db_drop bh_h1_rp
(cd "$W/core" && bh_env uv pip uninstall --python .venv/bin/python openferment-engine-h1probe >/dev/null 2>&1)
[ "${1:-}" = "" ] && git -C "$BH_ROOT" worktree remove --force "$W"
