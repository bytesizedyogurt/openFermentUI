#!/usr/bin/env bash
# H13-03: `pnpm ready`'s model and roles rows ask the Models API about the plan and index routes
# alone, so explain, extract and judge moved to models the key may not use read ✓ on both rows.
# Keyless, no network, no service: a fresh migrated test database (the roles row reads today's
# spend), the rows called as ready.run calls them with a key, their Anthropic client a stand-in.
# usage, from the repository root: bash bughunt/repro/H13-03/run.sh
source /home/user/openFermentUI/bughunt/lib/env.sh
HERE=/home/user/openFermentUI/bughunt/repro/H13-03
DB=bh_r_h13_03_ready
T=$BH_WORK/H13-03; mkdir -p "$T"
cleanup() { bh_db_drop "$DB"; rm -rf "$T"; }
trap cleanup EXIT

echo "EXPECTED: with OPENFERMENT_ROUTES moving explain and extract to claude-haiku-4-5-20251001 and judge to"
echo "EXPECTED: claude-opus-4-8, neither listed for the key, the model and roles rows name the routes' models"
echo "EXPECTED: and mark ! or ✗ for the two the key cannot use (docs/runbooks/live-host-install.md:170-171"
echo "EXPECTED: \"\`model\` and \`roles\`, the routes' models through the Models API\"; CLAUDE.md:29 \"says in rows"
echo "EXPECTED: whether the service can run: ... the model routes\"), as they do when the plan route moves."

bh_db_fresh "$DB" || { echo "OBSERVED: the test database could not be made"; echo "RESULT: NO-DEFECT"; exit 0; }
(cd "$BH_ROOT/core" && bh_env OPENFERMENT_DATABASE_URL="$BH_SERVER/$DB" OPENFERMENT_FIXTURES= \
   .venv/bin/python "$HERE/ready_routes.py") > "$T/out.log" 2>&1
grep -E '^(CASE|VERDICT)' "$T/out.log"
grep -E 'Traceback|Error' "$T/out.log" | grep -vE '^CASE|ModelUnavailable' | head -5

moved_model=$(grep -E '^CASE moved: [^ ]+ model:' "$T/out.log" | cut -c1-200)
moved_roles=$(grep -E '^CASE moved: [^ ]+ roles:' "$T/out.log" | cut -c1-200)
echo "OBSERVED: $moved_model"
echo "OBSERVED: $moved_roles"
echo "OBSERVED: $(grep -E '^CASE moved: moved routes. models the rows never asked' "$T/out.log")"
echo "OBSERVED: $(grep -E '^CASE live call on extract' "$T/out.log" | cut -c1-200)"
if grep -q '^VERDICT: DEFECT' "$T/out.log"; then echo "RESULT: DEFECT"; else echo "RESULT: NO-DEFECT"; fi
exit 0
