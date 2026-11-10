#!/usr/bin/env bash
# repro_import.sh: `pnpm db:import-alpha1` (package.json's command) from a worktree of the head (wt-head) on
# alpha 1.0 data directories written by alpha 1.0's own models (gen_alpha1.py), into a fresh test database
# bh_h6_r2; the head's service on 8866 reads the result. Shows:
#   H6-02  a decision whose gold value is a model's estimate is carried into the record store and read back
#          verified, gold; the record store's own door refuses the same decision (rule estimate)
#   H6-03  the command answers a traceback, with no `refused:` line, for two extraction files of one paper, a
#          database the server does not hold and a server that does not answer
#   H6-04  the counts it prints and audits say 3 people for a guild.json naming one person twice; 2 are kept
source /home/user/openFermentUI/bughunt/lib/env.sh
S=/home/user/openFermentUI/bughunt/notes/H6/scripts
W=$BH_WORK/H6
WT=$W/wt-head
DATA=$W/a1data-repro
DB=bh_h6_r2
URL=$BH_SERVER/$DB
git -C /home/user/openFermentUI show alpha-1.0:core/openferment_core/models.py > "$W/models-a1.py"
(cd "$W" && bh_env "$WT/core/.venv/bin/python" -I "$S/gen_alpha1.py" "$W/models-a1.py" "$DATA" >/dev/null) || exit 1
bh_db_fresh $DB || exit 1
imp() {  # imp CASE [URL]
  ( cd "$WT" && bh_env OPENFERMENT_DATABASE_URL="${2:-$URL}" \
      pnpm --silent db:import-alpha1 --name "Alpha 1.0 $1" --by "Ada Moreno" --data "$DATA/$1" ) > "$W/r2-$1.out" 2>&1
  echo "  exit $?; $(grep -c '^refused:' "$W/r2-$1.out") refused: lines; $(grep -c '^Traceback' "$W/r2-$1.out") tracebacks; last line: $(tail -1 "$W/r2-$1.out" | cut -c1-160)"
}
echo "== H6-02: estimate"; imp estimate
B=$(BH_KEEP_DB=1 bh_svc_start $DB 8866) || exit 1
H='X-OpenFerment-Project: alpha-1-0-estimate'; J='content-type: application/json'
curl -s --noproxy '*' -H "$H" "$B/api/biorepo/overlay" | python3 -c "
import json,sys; r=json.load(sys.stdin)['records']['cl1-P1-0001']
print('  BioRepo reads cl1-P1-0001:', r['status'], r['provenance'], 'gold', json.dumps(r.get('gold')))"
curl -s --noproxy '*' -H "$H" -H "$J" -X POST "$B/api/biorepo/check" -d '{"status":"verified","provenance":"curated","reviewer":"Ada Moreno","recordId":"cl1-P1-0001","at":"2026-10-20T00:00:00Z","gold":{"value":3,"unit":"mg L-1","origin":{"kind":"model-estimate","by":"claude-x","at":"2026-10-20T00:00:00Z"}}}' \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('  the record store asked the same decision: ok', d['ok'], 'rule', d['rule'])"
bh_svc_stop 8866
echo "== H6-03: two extraction files of one paper"; imp dup-paper
echo "== H6-03: a database the server does not hold"; imp full "$BH_SERVER/bh_h6_nothere"
echo "== H6-03: a server that does not answer"; imp full "postgresql://openferment:openferment@127.0.0.1:8869/bh_h6_x"
echo "   (pnpm db:migrate on the same two: $(cd "$WT/core" && bh_env OPENFERMENT_DATABASE_URL="$BH_SERVER/bh_h6_nothere" .venv/bin/python -m openferment_core.migrations migrate 2>&1 | cut -c1-90) | $(cd "$WT/core" && bh_env OPENFERMENT_DATABASE_URL=postgresql://openferment:openferment@127.0.0.1:8869/bh_h6_x .venv/bin/python -m openferment_core.migrations migrate 2>&1 | cut -c1-90))"
echo "== H6-04: one person named twice"; imp dup-person
grep "people" "$W/r2-dup-person.out" | sed 's/^/  printed:/'
psql "$URL" -XAtc "select '  kept: ' || count(*) || ' people (' || string_agg(id || ' ' || (body->>'name'), ', ') || ')' from openferment.guild_people where project_id='alpha-1-0-dup-person'"
psql "$URL" -XAtc "select '  audited: ' || (body->'detail'->'counts'->>'people') || ' people' from openferment.audit where project_id='alpha-1-0-dup-person' and action='import_alpha1'"
bh_db_drop $DB
