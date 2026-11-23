#!/bin/bash
# H13-04: `pnpm eval` with no project and with a project the database lacks, beside lit:graph's answer.
# Usage: bash h13_04_eval_project.sh <checkout> <a migrated bh_ database>
set -uo pipefail
source /home/user/openFermentUI/bughunt/lib/env.sh
root="${1:?checkout}"; dbn="${2:?bh_ database}"; cd "$root" || exit 2
E=(bh_env OPENFERMENT_DATA_DIR="$(mktemp -d)" OPENFERMENT_DATABASE_URL="$BH_SERVER/$dbn")
echo "== eval seed, no project";  "${E[@]}" OPENFERMENT_PROJECT= pnpm --silent eval seed 2>&1 | grep -v UV_NATIVE | tail -2; echo "   exit ${PIPESTATUS[0]}"
echo "== eval seed, project nope"; "${E[@]}" OPENFERMENT_PROJECT=nope pnpm --silent eval seed 2>&1 | grep -v UV_NATIVE | grep -E 'Error|Traceback' | head -2; echo "   exit ${PIPESTATUS[0]}"
echo "== eval summary, project nope"; "${E[@]}" OPENFERMENT_PROJECT=nope pnpm --silent eval summary 2>&1 | grep -v UV_NATIVE | tail -1; echo "   exit ${PIPESTATUS[0]}"
echo "== lit:graph --project nope --dry-run"; "${E[@]}" pnpm --silent lit:graph --project nope --dry-run 2>&1 | grep -v UV_NATIVE | tail -1; echo "   exit ${PIPESTATUS[0]}"
