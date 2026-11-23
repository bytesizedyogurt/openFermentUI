#!/usr/bin/env bash
# spend_nan.sh: spend.py's daily cap under OPENFERMENT_DAILY_BUDGET_USD = 25, nan, NaN and inf, on the head's
# code over a fresh test database bh_h12_spend (dropped after). Keyless; no model is called.
source /home/user/openFermentUI/bughunt/lib/env.sh
bh_db_fresh bh_h12_spend 2>/dev/null || exit 1
(cd "$BH_ROOT/core" && bh_env PYTHONDONTWRITEBYTECODE=1 OPENFERMENT_DATABASE_URL="$BH_SERVER/bh_h12_spend" \
   .venv/bin/python /home/user/openFermentUI/bughunt/notes/H12/scripts/spend_nan.py 2>&1 | tail -4)
bh_db_drop bh_h12_spend
