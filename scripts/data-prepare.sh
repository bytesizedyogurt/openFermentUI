#!/bin/bash
# What a machine derives for itself (OF-BLD-014 §1.3, E.10).
#
#   bash scripts/data-prepare.sh        pnpm data:prepare
#
# Rebuilds what each machine makes on its own, and skips what is already
# there, so a LIVE step on a fresh VM finds its inputs in place. The steps
# arrive with the phases that need them: §1.5 the full-text fetch, §4.1 the
# passage index, §6.2 the model files. Each runs only where `pnpm ready`
# says the host it needs answers. Exits non-zero when a step that ran failed.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

report="$(pnpm --silent ready 2>&1)" || true
lane="$(printf '%s\n' "$report" | sed -n 's/^lane: //p' | tail -1)"
echo "pnpm ready: lane ${lane:-unknown}"
# Whether `pnpm ready` marked a check ✓, by its row name.
reaches() { printf '%s\n' "$report" | grep -q "^✓ $1 "; }

status=0

echo "nothing to prepare yet"
exit "$status"
