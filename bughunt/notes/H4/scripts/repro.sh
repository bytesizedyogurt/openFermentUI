#!/usr/bin/env bash
# H4 reproductions from a fresh database. Usage:
#   bash /home/user/openFermentUI/bughunt/notes/H4/scripts/repro.sh <H4-01|H4-02|H4-03|H4-04|H4-05|H4-06|H4-07|all> [port]
# Starts the head's service on a fresh database bh_h4_repro (port 8841 by default), makes project h4p, runs the
# scripts the candidate needs, prints what they print, and stops the service and drops the database after.
# Artifact ids are the hashes of their bases (every value here is fixed, its origin dated 2026-11-10), so the ids
# the scripts pass between steps are the same on any fresh database.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
S=/home/user/openFermentUI/bughunt/notes/H4/scripts
PORT=${2:-8841}
O=$(bh_svc_start bh_h4_repro "$PORT") || exit 1
trap 'bh_svc_stop "$PORT"; bh_db_drop bh_h4_repro' EXIT
bh_project "$O" h4p "H4 project" >/dev/null; echo
py() { (cd /home/user/openFermentUI/core && bh_env .venv/bin/python "$@"); }
lib_run() {  # lib_run PLANT OUTFILE
  curl -s --noproxy '*' -X POST "$O/api/library/$1/run" -H 'content-type: application/json' \
       -H 'X-OpenFerment-Project: h4p' -d '{"by":"h4"}' > "$2"
}
W=$BH_WORK/H4/repro; mkdir -p "$W"
case "$1" in
  H4-01|all)
    echo "== H4-01: a library run's cost card reads its lines at the package's set price"
    lib_run cornstover "$W/cornstover.json"; lib_run cellulosic_ethanol_v0 "$W/cev0.json"
    py -c "
import json
for f in ('cornstover', 'cev0'):
    d = json.load(open('$W/' + f + '.json')); t = d['artifact']['output']['tea']; p = d['artifact']['output']['price']
    print(f, 'solvedPrice', p['solvedPrice'], 'tea.productPrice', t['productPrice'],
          'capitalRecovery perUnit', [l['perUnit'] for l in t['lines'] if l['key'] == 'capitalRecovery'])"
    py "$S/cornstover_feedprice.py" "$O" h4p
    ;;&
  H4-03|all)
    echo "== H4-03: a value set equal to the library default moves the price in the fifth digit"
    [ -f "$W/cornstover.json" ] || lib_run cornstover "$W/cornstover.json"
    py -c "import json; print('default run solvedPrice', json.load(open('$W/cornstover.json'))['artifact']['output']['price']['solvedPrice'])"
    py "$S/cornstover_feeddefault.py" "$O" h4p
    ;;&
  H4-06|all)
    echo "== H4-06: cellulosic_ethanol_v0's ethanol outputs are the denatured product stream's mass"
    [ -f "$W/cev0.json" ] || lib_run cellulosic_ethanol_v0 "$W/cev0.json"
    py -c "
import json
d = json.load(open('$W/cev0.json')); o = d['artifact']['output']
eth = [s for s in o['streams'] if s['id'] == 'ethanol'][0]
print('outputs', o['outputs'])
print('ethanol stream', eth['massFlow'], eth['massFlows'])
print('ethanol itself per kg dry feed', eth['massFlows']['Ethanol'] / o['outputs']['dryFeedKgPerH'])"
    ;;&
  H4-04|H4-05|all)
    echo "== H4-04 and H4-05: fermOS cases solvable by hand"
    py "$S/kinetics_cases.py" "$O" h4p | grep -E '^==|massBalance|refused'
    py "$S/kinetics_more.py" "$O" h4p | grep -E '^C '
    py "$S/zero_growth_runout.py" "$O" h4p
    ;;&
  H4-02|H4-07|all)
    echo "== H4-02 and H4-07: a scenario run, its train, a vessel design and the composite run built from them"
    py "$S/kinetics_cases.py" "$O" h4p >/dev/null   # keeps simulation 4b01278bdfb022c0
    py "$S/vessel_one.py" "$O" h4p 4b01278bdfb022c0 1000 | sed -n 1,3p
    py "$S/scenario_run.py" "$O" h4p
    py -c "import json; o=json.load(open('$BH_WORK/H4/svc-egv0-report.json'))['artifact']['output']; print('titre input 70 g/L; beer', o['readBack']['beerEthanolGPerL'], 'g/L; batch time', o['readBack']['batchTimeH'], 'h')"
    py "$S/train_from_run.py" "$O" h4p eb4ad3a1fce70fa2 egv0 | tail -1
    V=$(py -c "import json; print(json.load(open('$BH_WORK/H4/vessel-4b01278bdfb022c0.json'))['artifactId'])")
    T=$(py -c "import json; print(json.load(open('$BH_WORK/H4/train-egv0-run.json'))['artifactId'])")
    py "$S/composite_run.py" "$O" h4p "$V" "$T" repro
    ;;
esac
