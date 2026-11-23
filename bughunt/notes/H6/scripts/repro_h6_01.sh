#!/usr/bin/env bash
# repro_h6_01.sh: a product alpha 2.1 kept with a category in its own words vanishes from every head door once
# the database is migrated. From a fresh database: alpha 2.1 (wt-main, 112eb8b) keeps three products, one
# through the catalogue route with category "biofuel", one through its own catalogue_write tool with category
# "sugar alcohol" and one in a class the head's proposer reads; the head's migrations run; the head's service
# lists the products, reads each by id and the database's rows are counted. Ports 8864 (alpha 2.1) and 8865
# (head); database bh_h6_r1, dropped at the end. Needs wt-main made as notes.md says.
source /home/user/openFermentUI/bughunt/lib/env.sh
S=/home/user/openFermentUI/bughunt/notes/H6/scripts
W=$BH_WORK/H6
DB=bh_h6_r1
psql "$BH_SERVER/postgres" -qXc "DROP DATABASE IF EXISTS $DB WITH (FORCE)"; psql "$BH_SERVER/postgres" -qXc "CREATE DATABASE $DB"
(cd "$W/wt-main/core" && bh_env OPENFERMENT_DATABASE_URL="$BH_SERVER/$DB" .venv/bin/python -m openferment_core.migrations migrate)
bash "$S/main_svc.sh" start $DB 8864 >/dev/null || exit 1
A=http://127.0.0.1:8864; J='content-type: application/json'
curl -s --noproxy '*' -H "$J" -X POST $A/api/projects -d '{"id":"p1","name":"P1","by":"Ada Moreno"}' >/dev/null
H='X-OpenFerment-Project: p1'
for e in '{"kind":"product","id":"ethanol","name":"Ethanol","category":"biofuel"}' \
         '{"kind":"product","id":"cellulase","name":"Cellulase","category":"industrial_enzyme"}'; do
  curl -s --noproxy '*' -H "$H" -H "$J" -X POST $A/api/catalogues/product -d "{\"entry\":$e,\"by\":\"Ada Moreno\"}" \
    | python3 -c "import json,sys; d=json.load(sys.stdin); print('alpha 2.1 kept', d['id'], 'category', d['category'])"
done
curl -s --noproxy '*' -H "$H" -H "$J" -X POST "$A/api/tools/catalogue_write?by=claude-opus-5-5" \
  -d '{"kind":"product","id":"xylitol","name":"Xylitol","category":"sugar alcohol"}' \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('alpha 2.1 catalogue_write:', d['summary'] or d['error'])"
echo "alpha 2.1 lists: $(curl -s --noproxy '*' -H "$H" $A/api/catalogues/product | python3 -c "import json,sys; print([e['id'] for e in json.load(sys.stdin)])")"
bash "$S/main_svc.sh" stop $DB 8864
(cd "$BH_ROOT/core" && bh_env OPENFERMENT_DATABASE_URL="$BH_SERVER/$DB" .venv/bin/python -m openferment_core.migrations migrate)
B=$(BH_KEEP_DB=1 bh_svc_start $DB 8865) || exit 1
echo "head lists: $(curl -s --noproxy '*' -H "$H" $B/api/catalogues/product | python3 -c "import json,sys; print([e['id'] for e in json.load(sys.stdin)])")"
for id in ethanol xylitol cellulase; do
  echo "head GET /api/catalogues/product/$id -> $(curl -s --noproxy '*' -o /dev/null -w '%{http_code}' -H "$H" $B/api/catalogues/product/$id) $(curl -s --noproxy '*' -H "$H" $B/api/catalogues/product/$id | head -c 120)"
done
echo "head catalogue_read: $(curl -s --noproxy '*' -H "$H" -H "$J" -X POST $B/api/tools/catalogue_read -d '{"kind":"product"}' | python3 -c "import json,sys; d=json.load(sys.stdin)['summary']; print(d['matched'], [e['id'] for e in d['entries']])")"
echo "rows in the database: $(psql "$BH_SERVER/$DB" -XAtc "select string_agg(id || ' (' || coalesce(body->>'category','none') || ')', ', ' order by id) from openferment.catalogue where kind='product'")"
echo "the head's log:"; grep "does not read as an entry" "$BH_WORK/svc-8865.log" | head -2 | cut -c1-200
bh_svc_stop 8865
bh_db_drop $DB
