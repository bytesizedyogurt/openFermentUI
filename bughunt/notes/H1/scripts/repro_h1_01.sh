#!/usr/bin/env bash
# H1-01: identical runs asked at once keep one row whose body `by` and created_by column name different askers.
# The head's own service (kinetics, a core engine) on a fresh database bh_h1_r1, port 8811; keyless.
source /home/user/openFermentUI/bughunt/lib/env.sh
S=/home/user/openFermentUI/bughunt/notes/H1/scripts; T=$BH_WORK/H1; mkdir -p "$T"
O=$(bh_svc_start bh_h1_r1 8811) || exit 1
bh_project "$O" h1r1 >/dev/null
bh_py -c "from openferment_core.fermos_engine import write_placeholder_inputs as w; w('$T/r1-inputs.json', by='H1 hunter')"
for v in 0.41 0.42 0.43; do (cd "$BH_ROOT/core" && bh_env .venv/bin/python "$S/concurrent_kinetics.py" "$O" h1r1 bh_h1_r1 "$T/r1-inputs.json" "$v" 4); done
bh_svc_stop 8811; bh_db_drop bh_h1_r1
