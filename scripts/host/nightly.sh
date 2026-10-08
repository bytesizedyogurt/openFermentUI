#!/bin/bash
# Nightly Intake (OF-BLD-012 §B.8). The com.umutuzo.openferment.nightly
# LaunchDaemon runs this at 03:00; running it by hand does the same thing.
#
# Fetches every paper Europe PMC can give, then extracts from whatever arrived.
# Both batches skip what is already done, so a night with nothing new costs
# nothing, and extraction prints its cost per paper. The running service reads
# the new files on its next request; no restart. Exits non-zero when either
# batch failed, so the log says so.
set -uo pipefail
cd "$(dirname "$0")/../../core" || exit 1
PY=.venv/bin/python

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
"$PY" -m openferment_core.extract --all || status=$?
echo "── $(date '+%Y-%m-%d %H:%M:%S') done, exit $status"
exit "$status"
