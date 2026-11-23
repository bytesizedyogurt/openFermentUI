#!/usr/bin/env bash
# H4-04: fermOS flags a fed-batch whose cells take up nothing as a mass balance that does not close.
# The head's own service on a fresh database, port 9110; keyless, no model call.
# usage, from the repository root: bash bughunt/repro/H4-04/run.sh
source /home/user/openFermentUI/bughunt/lib/env.sh
HERE=/home/user/openFermentUI/bughunt/repro/H4-04
DB=bh_r_h4_04_svc
PORT=9110
T=$BH_WORK/H4-04; mkdir -p "$T"
cleanup() { bh_svc_stop "$PORT"; bh_db_drop "$DB"; rm -rf "$BH_WORK/data-$DB" "$T"; }
trap cleanup EXIT

echo "EXPECTED: a fed-batch with mu_max 0 and no maintenance or product terms takes up no sugar; its series meets the"
echo "EXPECTED: closed form (V = V0 + F t, every concentration diluted) to the integrator's 1e-6, so massBalance is ok"
echo "EXPECTED: and no 'does not close' flag is raised (kinetics.py:88-94: the check catches a wrong right-hand side,"
echo "EXPECTED: never integrator error); a fed-batch with growth closes as a control."

O=$(bh_svc_start "$DB" "$PORT") || { echo "OBSERVED: the service did not start"; echo "RESULT: NO-DEFECT"; exit 0; }
bh_project "$O" h404 >/dev/null
(cd "$BH_ROOT/core" && bh_env .venv/bin/python "$HERE/cases.py" "$O" h404) | tee "$T/cases.log"

bh_py - "$T/cases.log" <<'PY'
import json, sys
line = [l for l in open(sys.argv[1]) if l.startswith("VERDICT ")]
if not line:
    print("OBSERVED: the cases script printed no verdict"); print("RESULT: NO-DEFECT"); sys.exit(0)
v = json.loads(line[-1][len("VERDICT "):])
bad = []
for name in ("noUptakeSugar", "noUptakeWater"):
    r = v.get(name, {})
    if "closure" not in r:
        print(f"OBSERVED: {name} was refused: {r}"); continue
    holds = max(r["worstRel"].values()) <= 1e-5
    flagged = (not r["ok"]) or any("does not close" in f for f in r["flags"])
    print(f"OBSERVED: {name}: series meets the closed form within {max(r['worstRel'].values()):.2e}; "
          f"massBalance closure {r['closure']:.4g}, ok {r['ok']}; flags {r['flags']}")
    print(f"OBSERVED: {name}: the 'sugar consumed' the closure divides by is {r['consumedG']:.4g} g, "
          f"{abs(r['consumedG']) / r['inventoryG']:.1e} of the {r['inventoryG']:g} g the vessel held and was fed "
          f"(the integrator's rtol is 1e-6), and the true figure is 0 g")
    if holds and flagged:
        bad.append(name)
c = v.get("control", {})
if "closure" in c:
    print(f"OBSERVED: control (growth): massBalance closure {c['closure']:.2e}, ok {c['ok']}")
print("RESULT: DEFECT" if bad else "RESULT: NO-DEFECT")
PY
exit 0
