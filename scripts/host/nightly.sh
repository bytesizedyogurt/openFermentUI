#!/bin/bash
# Nightly Intake (OF-BLD-012 §B.8), and the night's check proposals
# (OF-BLD-013 §5.2). The com.umutuzo.openferment.nightly LaunchDaemon runs
# this at 03:00; running it by hand does the same thing.
#
# Fetches every paper Europe PMC can give, then extracts from whatever arrived.
# Both batches skip what is already done, so a night with nothing new costs
# nothing, and extraction prints its cost per paper. The running service reads
# the new files on its next request; no restart. Exits non-zero when either
# batch failed, so the log says so.
set -uo pipefail
# shellcheck source=lib.sh
source "$(dirname "$0")/lib.sh"
cd "$REPO/core" || exit 1
PY=.venv/bin/python

# The database and the project the night's extraction writes into (ADR-001,
# ADR-005), from core/.env when the environment lacks them; nothing else is
# read from that file here, and each command reads the key itself.
for name in OPENFERMENT_DATABASE_URL OPENFERMENT_PROJECT; do
  value="$(env_setting "$name")"
  [ -n "$value" ] && export "$name=$value"
done

echo "── $(date '+%Y-%m-%d %H:%M:%S') nightly intake"

# Intake caches a miss (no open-access text yet, a 404) so a batch never asks
# twice (intake.fetch_paper). Papers become open access later, and that is the
# reason this job exists (§B.8), so a miss older than a week is forgotten here
# and asked again. Complete fetches are kept: their text is what review
# decisions are anchored to, and refetching them would buy nothing.
"$PY" - <<'EOF'
import json, time
from openferment_core import intake
WEEK = 7 * 24 * 3600
expired = 0
for path in intake.FULLTEXT_DIR.glob("*.json"):
    try:
        status = json.loads(path.read_text(encoding="utf-8")).get("status")
    except (OSError, ValueError):
        continue
    if status == "failed:fetch" and time.time() - path.stat().st_mtime > WEEK:
        path.unlink()
        expired += 1
print(f"{expired} cached misses older than a week will be asked again")
EOF

status=0
"$PY" -m openferment_core.intake --all || status=$?
# Candidates belong to a project: the one OPENFERMENT_PROJECT names.
if [ -n "${OPENFERMENT_PROJECT:-}" ]; then
  "$PY" -m openferment_core.extract --all || status=$?
else
  echo "no OPENFERMENT_PROJECT in core/.env, so tonight's extraction waits: name the project it extracts into"
fi
# Every fetched model file against its pinned hash, and the ten newest
# artifacts recomputed and compared with what was kept. A difference is
# reported and fails the night; nothing is rewritten.
"$PY" -m openferment_core.nightly_checks || status=$?
# OF-BLD-013 §5.2 — rank the team against the ledger and put the highest
# person and skill pairs in the assessors' queue. A pair an open check
# already covers is never proposed again, so a quiet night proposes nothing.
"$PY" -m openferment_core.checks propose || status=$?
# Each new check gets the model's brief while the key is there; without one
# the checks wait in the queue and an assessor can ask for a brief later.
"$PY" -m openferment_core.checks brief --missing || status=$?
echo "── $(date '+%Y-%m-%d %H:%M:%S') done, exit $status"
exit "$status"
