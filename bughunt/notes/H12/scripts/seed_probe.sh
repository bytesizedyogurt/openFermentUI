#!/usr/bin/env bash
# seed_probe.sh WT: plant typed science in a worktree (a service module holding a titre, a yield, a price and a
# strain fact, and a browser data file exporting a yield table), run test_no_seed.py and test_boundaries.py,
# then remove both files. CLAUDE.md: "no composition, yield, price, titre, strain fact or paper's finding is typed
# in code or seed ... (core/tests/test_no_seed.py, acceptance A4)". The tests should fail; they pass.
set -u
WT=${1:?worktree}
S=/home/user/openFermentUI/bughunt/notes/H12/scripts
PY=$WT/core/openferment_core/typical_values.py
TS=$WT/src/data/yields.ts
cat > "$PY" <<'PYEOF'
"""Typical values a run falls back to when a project holds no record (PLANTED by bug hunt H12)."""
ETHANOL_TITRE_G_PER_L = 92.0          # S. cerevisiae CEN.PK113-7D, fed-batch, from a paper's table 2
ETHANOL_YIELD_G_PER_G = 0.48
CORN_STOVER_GLUCAN_FRACTION = 0.35    # a composition
ENZYME_PRICE_USD_PER_KG = 4.24        # a price
PYEOF
mkdir -p "$(dirname "$TS")"
cat > "$TS" <<'TSEOF'
// Typical yields by strain (PLANTED by bug hunt H12): a paper's findings typed into the browser.
export const TYPICAL_YIELDS = [
  { strain: 's-cerevisiae-cenpk113-7d', product: 'ethanol', gPerG: 0.48, titreGPerL: 92, paper: 'PMC0000000' },
];
TSEOF
WT=$WT $S/wtpytest.sh tests/test_no_seed.py tests/test_boundaries.py tests/test_guidance.py 2>&1 | tail -2
rm -f "$PY" "$TS"
git -C "$WT" status --short
