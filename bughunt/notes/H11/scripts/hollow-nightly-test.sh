#!/bin/bash
# hollow-nightly-test.sh CHECKOUT OUT: in the hunt's own worktree CHECKOUT, comment out nightly.sh's
# `backup_database || status=$?` line, run the three tests of the night's dump in that worktree's
# core/tests/test_host.py, run the mutated nightly.sh on the stand-ins (no pg_dump call is made), then
# put nightly.sh back with git checkout in the worktree. Nothing outside CHECKOUT and OUT is touched.
set -uo pipefail
CO="$1"; OUT="$2"; HERE="$(cd "$(dirname "$0")" && pwd)"
source /home/user/openFermentUI/bughunt/lib/env.sh
sed -i 's/^backup_database || status=\$?$/# backup_database || status=$?  (mutation: the night skips its dump)/' \
  "$CO/scripts/host/nightly.sh"
echo "--- the mutated line:"; grep -n 'backup_database ||' "$CO/scripts/host/nightly.sh"
echo "--- the tests of the night's dump, on the mutated tree:"
(cd "$CO/core" && bh_env /home/user/openFermentUI/core/.venv/bin/python -m pytest tests/test_host.py -q -p no:randomly \
  -k "nightly_dumps_before or night_dumps or failed_dump" 2>&1 | tail -2)
echo "--- the mutated night on the stand-ins (no pg_dump line below means no dump was made):"
bash "$HERE/nightly-cases.sh" "$CO" "$OUT" 2>&1 | sed -n '1,6p'
git -C "$CO" checkout -- scripts/host/nightly.sh
git -C "$CO" diff --stat -- scripts/host/nightly.sh
