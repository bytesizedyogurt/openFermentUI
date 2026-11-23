#!/bin/bash
# H13-05: examples/engines/openferment-engine-mirror/README.md followed line by line from the
# directory its line 9 names ("Test from this directory"), keyless, nothing written.
# Usage: bash h13_05_stranger.sh <a clean checkout with core/.venv and the mirror installed>
set -uo pipefail
source /home/user/openFermentUI/bughunt/lib/env.sh
root="${1:?checkout}"; cd "$root/examples/engines/openferment-engine-mirror" || exit 2
echo "== line 9, from this directory"; bh_env ../../../core/.venv/bin/python -m pytest -q 2>&1 | tail -1
echo "== line 10, as written, from the same directory"; bh_env bash -c 'cd core && uv run python -m openferment_core.engine.conform mirror' 2>&1 | tail -1
echo "== line 10 from the repository root, with no database named (the README names none)"
cd "$root" && bh_env OPENFERMENT_DATABASE_URL= bash -c 'cd core && uv run python -m openferment_core.engine.conform mirror' 2>&1 | grep -v UV_NATIVE | tail -1
