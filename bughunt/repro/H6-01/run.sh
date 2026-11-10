#!/usr/bin/env bash
# H6-01: a product alpha 2.1 kept with a category in its own words vanishes from every head door once the
# database is migrated. From a fresh database at alpha 2.1's schema (112eb8b, in a worktree of this run's own,
# on the repository's venv: core/uv.lock is the same file at both commits), alpha 2.1's own service keeps three
# products: ethanol ("biofuel") through the catalogue route, xylitol ("sugar alcohol") through alpha 2.1's
# catalogue_write tool, and cellulase in one of the twelve classes as the control. The head's migrations run,
# and the head's service (2047f5a, the repository) lists the products, reads each by id and runs catalogue_read;
# the database's rows are counted.
#   bash bughunt/repro/H6-01/run.sh        (from the repository root; exits 0 either way)
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PYTHONDONTWRITEBYTECODE=1 PGOPTIONS='-c client_min_messages=warning'
DB=bh_r_h6_01_upgrade
PA=9930 PB=9931                      # alpha 2.1's service, then the head's
P=h6-01; J='content-type: application/json'; H="X-OpenFerment-Project: $P"
S=$BH_WORK/H6-01; mkdir -p "$S"
WT=$S/wt-a21-$$                      # alpha 2.1's tree, this run's own
T=$(mktemp -d "$S/run.XXXXXX")       # this run's answers
cleanup() {
  bh_svc_stop "$PA"; bh_svc_stop "$PB"; bh_db_drop "$DB"
  git -C "$BH_ROOT" worktree remove --force "$WT" >/dev/null 2>&1
  git -C "$BH_ROOT" worktree list --porcelain | grep -qx "worktree $WT" && { rm -rf "$WT"; git -C "$BH_ROOT" worktree prune; }
  rm -rf "$T" "$WT" "$BH_WORK/data-$DB" "$BH_WORK/svc-$PA.log" "$BH_WORK/svc-$PB.log" "$BH_WORK/svc-$PA.pid" "$BH_WORK/svc-$PB.pid"
}
trap cleanup EXIT
fail() { echo "the steps did not complete: $*"; echo "RESULT: NO-DEFECT"; exit 0; }
for p in $PA $PB; do [ -z "$(bh_port_pid "$p")" ] || fail "port $p is taken"; done

git -C "$BH_ROOT" worktree add --detach "$WT" 112eb8b >/dev/null 2>&1 || fail "no worktree at 112eb8b"
ln -s "$BH_ROOT/core/.venv" "$WT/core/.venv"
cmp -s <(git -C "$BH_ROOT" show 112eb8b:core/uv.lock) <(git -C "$BH_ROOT" show 2047f5a:core/uv.lock) \
  && echo "core/uv.lock: the same file at 112eb8b and 2047f5a (one venv runs both trees)"

# 1. A fresh database migrated by alpha 2.1's own migrations; alpha 2.1's service over it.
BH_ROOT=$WT bh_db_fresh "$DB" || fail "bh_db_fresh at alpha 2.1"
echo "database $DB (fresh): openferment at $(psql "$BH_SERVER/$DB" -XAtc 'select version_num from openferment.alembic_version'), alpha 2.1's migrations"
A=$(BH_ROOT=$WT BH_KEEP_DB=1 BH_FIXTURES=1 bh_svc_start "$DB" "$PA") || fail "alpha 2.1's service did not start"
echo "alpha 2.1's service (112eb8b): $A"
BH_BY="Ada Moreno" bh_project "$A" "$P" "Repro H6-01" >/dev/null
for e in '{"kind":"product","id":"ethanol","name":"Ethanol","category":"biofuel"}' \
         '{"kind":"product","id":"cellulase","name":"Cellulase","category":"industrial_enzyme"}'; do
  curl -s --noproxy '*' -H "$H" -H "$J" -X POST "$A/api/catalogues/product" -d "{\"entry\":$e,\"by\":\"Ada Moreno\"}" \
    | python3 -I -c "import json,sys; d=json.load(sys.stdin); print('alpha 2.1 POST /api/catalogues/product kept', d['id'], 'category', repr(d['category']), 'by', d['by'])"
done
curl -s --noproxy '*' -H "$H" -H "$J" -X POST "$A/api/tools/catalogue_write?by=Ada%20Moreno" \
  -d '{"kind":"product","id":"xylitol","name":"Xylitol","category":"sugar alcohol"}' \
  | python3 -I -c "import json,sys; d=json.load(sys.stdin); s=d['summary'] or {}; print('alpha 2.1 catalogue_write kept', s.get('id'), 'error', d.get('error'))"
curl -s --noproxy '*' -H "$H" "$A/api/catalogues/product" > "$T/a21_list.json"
echo "alpha 2.1 GET /api/catalogues/product: $(python3 -I -c "import json,sys; print([(e['id'], e['category']) for e in json.load(open(sys.argv[1]))])" "$T/a21_list.json")"
bh_svc_stop "$PA"

# 2. The head's migrations (pnpm db:migrate's command), then the head's service over the same database.
(cd "$BH_ROOT/core" && bh_env OPENFERMENT_DATABASE_URL="$BH_SERVER/$DB" .venv/bin/python -m openferment_core.migrations migrate) \
  | sed 's/^/head migrate: /' || fail "the head's migrations"
B=$(BH_KEEP_DB=1 BH_FIXTURES=1 bh_svc_start "$DB" "$PB") || fail "the head's service did not start"
echo "the head's service (2047f5a): $B"
curl -s --noproxy '*' -H "$H" "$B/api/catalogues/product" > "$T/head_list.json"
for id in ethanol xylitol cellulase; do
  curl -s --noproxy '*' -o "$T/head_get_$id.json" -w '%{http_code}' -H "$H" "$B/api/catalogues/product/$id" > "$T/head_get_$id.code"
done
curl -s --noproxy '*' -H "$H" -H "$J" -X POST "$B/api/tools/catalogue_read" -d '{"kind":"product"}' > "$T/head_read.json"
psql "$BH_SERVER/$DB" -XAtc "select json_agg(json_build_object('key', id, 'id', body->>'id', 'category', body->>'category', 'by', body->>'by') order by id)
  from openferment.catalogue where kind='product' and project_id='$P'" > "$T/rows.json"
grep -h "does not read as an entry" "$BH_WORK/svc-$PB.log" | cut -c1-170 | sort | uniq -c | sed 's/^ */head log, times: /'
echo "the screen's subtitle: src/screens/Catalogues.tsx:$(grep -n "Every entry stays once kept" "$BH_ROOT/src/screens/Catalogues.tsx" | cut -d: -f1) \"Every entry stays once kept\""

python3 -I - "$T" <<'PY' || echo "RESULT: NO-DEFECT (the answers did not read; see the lines above)"
import json, sys
t = sys.argv[1]
a21 = [e["id"] for e in json.load(open(f"{t}/a21_list.json"))]
head = json.load(open(f"{t}/head_list.json"))
rows = json.load(open(f"{t}/rows.json")) or []
gets = {i: (open(f"{t}/head_get_{i}.code").read().strip(), json.load(open(f"{t}/head_get_{i}.json")))
        for i in ("ethanol", "xylitol", "cellulase")}
read = json.load(open(f"{t}/head_read.json"))["summary"]
print("head GET /api/catalogues/product: a", type(head).__name__, "of", len(head), "->",
      [(e["id"], e["category"]) for e in head] if isinstance(head, list) else head)
for i, (code, body) in gets.items():
    print(f"head GET /api/catalogues/product/{i}: {code}", body.get("detail") or f"category {body.get('category')!r}")
print("head catalogue_read: matched", read["matched"], [e["id"] for e in read["entries"]])
print("openferment.catalogue rows:", [(r["key"], r["category"], r["by"]) for r in rows])
lost = [r["id"] for r in rows if r["id"] in a21 and r["id"] not in [e["id"] for e in head]]
said = ", ".join(f"GET {i} answers {gets[i][0]} {gets[i][1].get('detail')!r}" for i in lost)
print(f"EXPECTED: the three products alpha 2.1 listed ({a21}) still listed and read by id at the head, or each one "
      "the head cannot read named to the person with why (as GET /api/state names a row it cannot read in `refused`)")
print(f"OBSERVED: the head lists {[e['id'] for e in head]} (a bare list naming nothing left out); "
      f"{said}; "
      f"catalogue_read matched {read['matched']}; the database still holds {len(rows)} rows, {lost} among them")
defect = (sorted(a21) == ["cellulase", "ethanol", "xylitol"] and isinstance(head, list) and len(lost) == 2
          and all(gets[i][0] == "404" and "holds no" in gets[i][1].get("detail", "") for i in lost)
          and gets["cellulase"][0] == "200" and read["matched"] == 1)
print("RESULT: DEFECT" if defect else "RESULT: NO-DEFECT")
PY
exit 0
