#!/usr/bin/env bash
# H9-15: ask_postdoc and get_artifact, the openferment MCP server's two tools of its own, answer a
# missing or mistyped argument with isError true and pydantic's validation text (its URL included),
# where every registry tool answers the same inputs with a ToolResult whose error holds words.
#   bash bughunt/repro/H9-15/run.sh        (from the repository root; exits 0 either way)
# A fresh test database, one project made in process, then the MCP server in its own process over
# raw JSON-RPC lines on stdio. No service, no port, no model call, no network beyond loopback.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PYTHONDONTWRITEBYTECODE=1 PGOPTIONS='-c client_min_messages=warning'
DB=bh_r_h9_15_mcp
PROJ=h9-15
HERE=/home/user/openFermentUI/bughunt/repro/H9-15
cleanup() { bh_db_drop "$DB"; }
trap cleanup EXIT

bh_db_fresh "$DB" || { echo "the database could not be made"; echo "RESULT: NO-DEFECT (no database)"; exit 0; }
echo "database: $DB (fresh, migrated to head)"
MADE=$(OPENFERMENT_DATABASE_URL="$BH_SERVER/$DB" bh_py -c "
from openferment_core import projects
from openferment_core.models import ProjectCreate
p = projects.create(ProjectCreate(id='$PROJ', name='H9-15 probe', by='bughunt'))
print('project:', p.id)
" 2>&1 | tail -1)
echo "$MADE"
echo

echo "## the MCP server in its own process (--project $PROJ), raw JSON-RPC tools/call"
MCP=$(bh_py "$HERE/mcp_call.py" "$BH_SERVER/$DB" "$PROJ" 2>&1)
echo "$MCP"
echo

n() { echo "$MCP" | grep -c -E "$1"; }
ctrl_words=$(n '^CASE CONTROL literature_document .*\| isError=False \| JSON keys=.*error')
ctrl_art=$(n "^CASE CONTROL get_artifact .*\| isError=False \| JSON keys=error \| text=\{\"error\": \"no readable artifact 'zz'")
ask_bad=$(n '^CASE PROBE ask_postdoc .*\| isError=True \| no JSON \| text=Error executing tool ask_postdoc: 1 validation error for ask_postdocArguments.*errors\.pydantic\.dev')
art_bad=$(n '^CASE PROBE get_artifact .*\| isError=True \| no JSON \| text=Error executing tool get_artifact: 1 validation error for get_artifactArguments.*errors\.pydantic\.dev')
ask_plan=$(n '^CASE PROBE ask_postdoc .*\| isError=False \| JSON keys=.*declined')
art_words=$(n '^CASE PROBE get_artifact .*\| isError=False \| JSON keys=error ')

echo "EXPECTED: ask_postdoc with no question, or a question that is no string, answers an AnswerPlan whose declined holds words, and get_artifact with no id, or an id that is no string, answers {\"error\": <words>}, each with isError false, as the registry tool literature_document answers the same inputs (docs/TOOLS.md:896: \"ask_postdoc's an AnswerPlan whose declined holds the words ... {\\\"error\\\": <words>} alone for a tool and for get_artifact ... is_error stays false\")."
echo "OBSERVED: controls: literature_document refused in words with isError false in $ctrl_words of 3 cases, get_artifact id \"zz\" refused in words in $ctrl_art of 1; probes: ask_postdoc answered isError true with pydantic's validation text and its errors.pydantic.dev URL in $ask_bad of 3 cases (an AnswerPlan with declined in $ask_plan), get_artifact the same in $art_bad of 3 cases ({\"error\": <words>} in $art_words)."
if [ "$ctrl_words" = 3 ] && [ "$ctrl_art" = 1 ] && [ "$ask_bad" = 3 ] && [ "$art_bad" = 3 ]; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
