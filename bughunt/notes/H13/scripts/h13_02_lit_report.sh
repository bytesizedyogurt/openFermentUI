#!/bin/bash
# H13-02: `pnpm lit:report` (the demo, offline, keyless) run in a disposable checkout rewrites
# docs/reports/literature-retrieval.md and drops the sections written by hand after its generated part.
# Usage: bash h13_02_lit_report.sh <a disposable worktree with core/.venv>   (it restores the two files after)
set -uo pipefail
source /home/user/openFermentUI/bughunt/lib/env.sh
wt="${1:?worktree}"; here="$(cd "$(dirname "$0")" && pwd)"
case "$wt" in /home/user/openFermentUI|/home/user/openFermentUI/) echo "refusing the main checkout"; exit 2;; esac
echo "-- the committed report's header and hand-added note:"
sed -n '1p;91p' "$wt/docs/reports/literature-retrieval.md"
grep -c '' "$wt/docs/reports/literature-retrieval.md" | sed 's/^/   lines before: /'
(cd "$wt/core" && bh_env OPENFERMENT_DATA_DIR="$(mktemp -d)" OPENFERMENT_TEST_DATABASE_URL="$BH_SERVER/bh_h13_test" \
  .venv/bin/python "$here/lit_report_bh.py" >/dev/null 2>&1); echo "   lit:report exit $?"
grep -c '' "$wt/docs/reports/literature-retrieval.md" | sed 's/^/   lines after: /'
git -C "$wt" diff --stat -- docs/reports/
echo "-- sections gone:"; git -C "$wt" diff -- docs/reports/literature-retrieval.md | grep '^-###' 
git -C "$wt" checkout -- docs/reports/
