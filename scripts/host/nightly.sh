#!/bin/bash
# Nightly extraction (OF-BLD-012 §B.8), and the night's check proposals
# (OF-BLD-013 §5.2). The com.umutuzo.openferment.nightly LaunchDaemon runs
# this at 03:00; running it by hand does the same thing.
#
# Extracts from every document the project holds in its literature (ADR-002;
# documents arrive through Intake, collected by a person). The batch skips
# what is already extracted, so a night with nothing new costs nothing, and
# extraction prints its cost per document. The running service reads the new
# rows on its next request; no restart. Exits non-zero when a batch failed,
# so the log says so.
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

echo "── $(date '+%Y-%m-%d %H:%M:%S') nightly extraction"

status=0
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
