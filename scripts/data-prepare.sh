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

# §1.5 — the full text of every paper that carries an identifier. Intake keeps
# what it fetched and the misses it was told, so a second run asks only for
# what is new (intake.fetch_paper).
if reaches europepmc; then
  echo "full text: fetching from Europe PMC"
  pnpm --silent intake:fetch --all || status=1
else
  echo "full text: Europe PMC does not answer here, so nothing is fetched (pnpm ready says why)"
fi

# §4.1 — the passage index over whatever full text is here. Local work, no
# network: it cuts only the papers whose text changed since the last build.
echo "passage index: building"
pnpm --silent index:build || status=1

exit "$status"
