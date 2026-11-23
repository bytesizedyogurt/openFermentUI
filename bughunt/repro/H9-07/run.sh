#!/usr/bin/env bash
# H9-07: `pnpm ready --offline` skips the model and roles rows whole, so an OPENFERMENT_ROUTES table that cannot route
# (RoutesInvalid) leaves the report at "Ready." and exit 0; the table is read with no network and no key.
#
#   bash bughunt/repro/H9-07/run.sh        (from the repository root)
#
# A fresh database (bh_r_h9_07_ready, made by bh_db_fresh) and a private copy of the fetched data. For a valid table
# and five tables that cannot route, `python -m openferment_core.ready --offline --no-workers` (what `pnpm ready
# --offline` runs, without the workers' cold start), then, in one process with no network, what llm.routes() and
# ready.check_model(have_key=False) say of the same table. Keyless: no key in the environment, ANTHROPIC_BASE_URL on a
# loopback port nothing listens on, and the service row polls 127.0.0.1:10349, where nothing listens. No service is
# started. Ends with RESULT: DEFECT or RESULT: NO-DEFECT and exits 0; the database and the data copy go on the way out.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PGOPTIONS='-c client_min_messages=warning'
DB=bh_r_h9_07_ready; OUT=$BH_WORK/H9-07; rm -rf "$OUT"; mkdir -p "$OUT"
cleanup() { bh_db_drop $DB; rm -rf "$OUT"; }
trap cleanup EXIT
finish() { echo "OBSERVED: $1"; echo "RESULT: NO-DEFECT"; exit 0; }

echo "EXPECTED: for a routing table that cannot route, \`pnpm ready --offline\` shows a failing (✗) model row in the RoutesInvalid words llm.routes() gives, and exits 1 (CLAUDE.md:29: \`pnpm ready\` (or \`pnpm ready --offline\`) says in rows whether the service can run ... the model routes; ADR-008 6.3: refused in words when it cannot route (RoutesInvalid, and \`pnpm ready\` fails on it))."

bh_db_fresh $DB || finish "the database $DB could not be made"
cp -R "$BH_DATA_SRC" "$OUT/data" || finish "the data copy could not be made"

NAMES=(valid malformed unknown-family unknown-provider bad-effort empty-models)
declare -A TABLES=(
  [valid]='{"plan": {"effort": "high"}}'
  [malformed]='{"plan": {"models": ["claude-opus-5-5"]'
  [unknown-family]='{"planner": {"models": ["claude-opus-5-5"]}}'
  [unknown-provider]='{"plan": {"models": ["acme:big-model"]}}'
  [bad-effort]='{"plan": {"effort": "extreme"}}'
  [empty-models]='{"plan": {"models": []}}'
)
GUARD=(OPENFERMENT_DATABASE_URL="$BH_SERVER/$DB" OPENFERMENT_DATA_DIR="$OUT/data" OPENFERMENT_POLL_HOST=127.0.0.1
       OPENFERMENT_PORT=10349 ANTHROPIC_BASE_URL=http://127.0.0.1:10348 NO_PROXY=127.0.0.1,localhost no_proxy=127.0.0.1,localhost)

for name in "${NAMES[@]}"; do
  (cd "$BH_ROOT/core" && bh_env "${GUARD[@]}" OPENFERMENT_ROUTES="${TABLES[$name]}" \
     timeout 300 .venv/bin/python -m openferment_core.ready --offline --no-workers) > "$OUT/$name.ready" 2>&1
  echo "$?" > "$OUT/$name.exit"
done

# The same tables in one process, with no network and no key, core/.env left unread: llm.routes() and the model row.
printf '%s\n' "${NAMES[@]}" > "$OUT/names"
for name in "${NAMES[@]}"; do printf '%s\n' "${TABLES[$name]}" > "$OUT/$name.table"; done
(cd "$BH_ROOT/core" && bh_env "${GUARD[@]}" .venv/bin/python - "$OUT" <<'PY'
import json, os, sys
from pathlib import Path
out = Path(sys.argv[1])
from openferment_core import llm, ready
rows = {}
for name in (out / "names").read_text().split():
    os.environ["OPENFERMENT_ROUTES"] = (out / f"{name}.table").read_text().strip()
    try:
        llm.routes(); routes = "routes"
    except llm.RoutesInvalid as e:
        routes = f"RoutesInvalid: {e}"
    c = ready.check_model(False)
    rows[name] = {"routes": routes, "check_model": f"{ready.MARKS[c.mark]} {c.detail}", "mark": c.mark}
(out / "inprocess.json").write_text(json.dumps(rows))
PY
) > "$OUT/inprocess.log" 2>&1
[ -s "$OUT/inprocess.json" ] || finish "the in-process check wrote nothing: $(tail -c 400 "$OUT/inprocess.log")"

python3 - "$OUT" <<'PY'
import json, sys
from pathlib import Path
out = Path(sys.argv[1])
names = (out / "names").read_text().split()
inproc = json.loads((out / "inprocess.json").read_text())
def ready_of(name):
    text = (out / f"{name}.ready").read_text()
    lines = text.strip().splitlines()
    model = next((l for l in lines if l[2:].startswith("model ")), "(no model row)")
    roles = next((l for l in lines if l[2:].startswith("roles ")), "(no roles row)")
    summary = next((l for l in reversed(lines) if l == "Ready." or "problem" in l), "(no summary line)")
    fails = [l for l in lines if l.startswith("✗")]
    return {"exit": int((out / f"{name}.exit").read_text().strip() or -1), "model": " ".join(model.split()),
            "roles": " ".join(roles.split()), "summary": summary, "fails": fails}
base = ready_of("valid")
print(f"OBSERVED: valid table {(out / 'valid.table').read_text().strip()}: ready --offline says '{base['model']}', "
      f"'{base['summary']}', exit {base['exit']}; llm.routes() {inproc['valid']['routes']}.")
broken = []
for name in names[1:]:
    r, ip = ready_of(name), inproc[name]
    table = (out / f"{name}.table").read_text().strip()
    print(f"OBSERVED: {name} {table}: llm.routes() raises {ip['routes']}; check_model(have_key=False) with no "
          f"network: '{ip['check_model']}'; ready --offline says '{r['model']}', '{r['roles']}', '{r['summary']}', "
          f"exit {r['exit']}" + (f"; its failing rows: {r['fails']}" if r["fails"] else "") + ".")
    cannot_route = ip["routes"].startswith("RoutesInvalid") and ip["mark"] == "fail"
    said_ready = r["exit"] == 0 and r["summary"] == "Ready." and r["model"].startswith("·") and "--no-network" in r["model"]
    if cannot_route and said_ready:
        broken.append(name)
sane = base["exit"] == 0 and base["summary"] == "Ready." and inproc["valid"]["routes"] == "routes"
print(f"OBSERVED: {len(broken)} of {len(names) - 1} tables that cannot route leave ready --offline at 'Ready.' and exit 0 "
      f"with the model row skipped ({', '.join(broken) or 'none'}).")
print("RESULT: " + ("DEFECT" if sane and broken else "NO-DEFECT"))
PY
exit 0
