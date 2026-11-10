#!/usr/bin/env bash
# wtpytest.sh [-3.12] <pytest args...>: run pytest in H12's worktree (keyless, test databases named bh_h12_t_*).
# With -3.12 it runs the same selection under the Python 3.12 environment with the worktree's core on PYTHONPATH.
source /home/user/openFermentUI/bughunt/lib/env.sh
WT=${WT:-$BH_WORK/H12/wt}
PY312=/tmp/claude-0/-home-user-openFermentUI/cfbc5c9f-640a-5002-a705-5ceaf850fdc6/scratchpad/py312/bin/python
cd "$WT/core" || exit 2
if [ "$1" = "-3.12" ]; then shift
  bh_env OPENFERMENT_DATABASE_URL= PYTHONPATH="$WT/core" OPENFERMENT_TEST_DATABASE_URL="$BH_SERVER/bh_h12_p" \
    "$PY312" -m pytest "$@" -q -p no:randomly -p no:cacheprovider
else
  bh_env OPENFERMENT_TEST_DATABASE_URL="$BH_SERVER/bh_h12_t" .venv/bin/python -m pytest "$@" -q -p no:randomly -p no:cacheprovider
fi
