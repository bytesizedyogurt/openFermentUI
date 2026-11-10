#!/usr/bin/env bash
# R2-02: conform against an address whose server answers but holds no such database.
# D.0 (6f85338) says "conform and migrations say a missing database in words (exit 2)".
# Usage: bash conform_missing_db.sh <worktree at 2047f5a with its own core/.venv>
# The worktree's conform scratch prefix is renamed to bh_r2_conform first, so the checks' own
# database is a bh_r2_* one (the hunt's naming rule); the main checkout is never touched.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
WT="${1:?worktree}"
case "$WT" in */bh/work/R2/*) ;; *) echo "refusing a worktree outside bh/work/R2" >&2; exit 2;; esac
sed -i 's/^SCRATCH = "openferment_conform"/SCRATCH = "bh_r2_conform"/' "$WT/core/openferment_core/engine/conform.py"
MISSING="$BH_SERVER/bh_r2_missing"   # the server answers; no database of this name exists
cd "$WT/core" || exit 1
echo "== migrations migrate"
bh_env OPENFERMENT_DATABASE_URL="$MISSING" PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m openferment_core.migrations migrate 2>&1 | tail -2
echo "exit ${PIPESTATUS[0]}"
echo "== conform biosteam"
bh_env OPENFERMENT_DATABASE_URL="$MISSING" PYTHONDONTWRITEBYTECODE=1 timeout 600 .venv/bin/python -m openferment_core.engine.conform biosteam 2>&1 | grep -v '^     ' | head -4
echo "exit ${PIPESTATUS[0]}"
echo "== conform train --project p"
bh_env OPENFERMENT_DATABASE_URL="$MISSING" PYTHONDONTWRITEBYTECODE=1 timeout 600 .venv/bin/python -m openferment_core.engine.conform train --project p 2>&1 | tail -2
echo "exit ${PIPESTATUS[0]}"
git -C "$WT" checkout -- core/openferment_core/engine/conform.py
