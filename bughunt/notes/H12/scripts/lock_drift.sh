#!/usr/bin/env bash
# lock_drift.sh WT: in a worktree of one's own, loosen one constraint in core/pyproject.toml so core/uv.lock no
# longer matches it; `uv lock --check` refuses the stale lock (exit 1), and `uv run --all-extras` (the way every
# verify stage in package.json calls it, and the only way CI reaches the Python side) rewrites the lock and runs
# (exit 0). Offline: uv reads its cache alone. Restores both files after.
source /home/user/openFermentUI/bughunt/lib/env.sh
WT=${1:?worktree}; cd "$WT/core" || exit 2
sed -i 's/"jsonschema>=4.23", "pyyaml>=6"\]/"jsonschema>=4.23", "pyyaml>=6.0.1"]/' pyproject.toml
bh_env uv lock --check --offline >/dev/null 2>&1; echo "uv lock --check: exit $?"
bh_env uv run --offline --all-extras python -c "print('uv run ran')" 2>/dev/null | tail -1; echo "uv run --all-extras: exit ${PIPESTATUS[0]}"
git -C "$WT" diff --stat -- core/uv.lock
git -C "$WT" checkout -- core/pyproject.toml core/uv.lock
