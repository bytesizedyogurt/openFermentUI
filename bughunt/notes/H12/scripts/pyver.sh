#!/usr/bin/env bash
# pyver.sh 3.12|3.13 <files...>: run a selection in H12's second worktree under one Python, one line a test
# (-rA), so the two runs diff test by test. Databases are named bh_h12_v<ver>_*.
source /home/user/openFermentUI/bughunt/lib/env.sh
WT2=${WT2:-$BH_WORK/H12/wt2}
v=$1; shift
cd "$WT2/core" || exit 2
if [ "$v" = 3.12 ]; then PY=/tmp/claude-0/-home-user-openFermentUI/cfbc5c9f-640a-5002-a705-5ceaf850fdc6/scratchpad/py312/bin/python
else PY=/home/user/openFermentUI/core/.venv/bin/python; fi
bh_env OPENFERMENT_DATABASE_URL= PYTHONPATH="$WT2/core" OPENFERMENT_TEST_DATABASE_URL="$BH_SERVER/bh_h12_v${v/./}" \
  "$PY" -m pytest "$@" -q -p no:randomly -p no:cacheprovider -rA -m "not live and not sim and not slow and not lit" \
  -k "not sigterm_ends_the_command"
