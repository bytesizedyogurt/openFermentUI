#!/usr/bin/env bash
# H1-03: the documented `conform biosteam --thing ethanol_glucose_v0 --inputs <file>` fails with ProjectRequired.
# The head's own venv, a fresh database bh_h1_r3 for the verdict, keyless; then the same command with
# OPENFERMENT_PROJECT set to any id, which makes the checks run.
source /home/user/openFermentUI/bughunt/lib/env.sh
T=$BH_WORK/H1; mkdir -p "$T"; bh_db_fresh bh_h1_r3 || exit 1
D=$(bh_data bh_h1_r3)
cat > "$T/r3-inputs.json" <<'JSON'
[{"name":"feed_glucose_conc","quantity":{"value":100,"unit":"g L-1","origin":{"kind":"person-assumption","by":"H1 hunter","at":"2026-11-10"}}},
 {"name":"titre","quantity":{"value":50,"unit":"g L-1","origin":{"kind":"person-assumption","by":"H1 hunter","at":"2026-11-10"}}},
 {"name":"yield","quantity":{"value":0.4,"unit":"g g-1","origin":{"kind":"person-assumption","by":"H1 hunter","at":"2026-11-10"}}},
 {"name":"productivity","quantity":{"value":1,"unit":"g L-1 h-1","origin":{"kind":"person-assumption","by":"H1 hunter","at":"2026-11-10"}}},
 {"name":"plant_scale","quantity":{"value":1000,"unit":"t yr-1","origin":{"kind":"person-assumption","by":"H1 hunter","at":"2026-11-10"}}},
 {"name":"glucose_price","quantity":{"value":0.5,"unit":"USD kg-1","origin":{"kind":"person-assumption","by":"H1 hunter","at":"2026-11-10"}}}]
JSON
cd "$BH_ROOT/core"
echo "== as documented"
bh_env OPENFERMENT_DATABASE_URL="$BH_SERVER/bh_h1_r3" OPENFERMENT_DATA_DIR="$D" OPENFERMENT_SFF_LIBRARY="$D/sff-library" \
  .venv/bin/python -m openferment_core.engine.conform biosteam --thing ethanol_glucose_v0 --inputs "$T/r3-inputs.json" 2>&1 | grep -v '^INFO'
echo "exit ${PIPESTATUS[0]}"
echo "== with OPENFERMENT_PROJECT set to an id no database holds"
bh_env OPENFERMENT_PROJECT=any-id OPENFERMENT_DATABASE_URL="$BH_SERVER/bh_h1_r3" OPENFERMENT_DATA_DIR="$D" OPENFERMENT_SFF_LIBRARY="$D/sff-library" \
  .venv/bin/python -m openferment_core.engine.conform biosteam --thing ethanol_glucose_v0 --inputs "$T/r3-inputs.json" 2>&1 | grep -v '^INFO' | head -3
echo "exit ${PIPESTATUS[0]}"
bh_db_drop bh_h1_r3
