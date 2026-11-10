#!/bin/bash
# dump-restore.sh LIB OUT: the night's dump with the real pg_dump and the runbook's step 7 restore
# with the real createdb and pg_restore, on test databases. backup_database dumps the database
# `openferment`; a wrapper in the stand-in keg hands pg_dump the test database bh_h11_live in that
# name's place, so nothing touches a database outside bh_h11_*. Then the restore command the
# runbook names (createdb -h 127.0.0.1 openferment_restored && pg_restore -h 127.0.0.1 -d ...) is
# run with bh_h11_restored in the name's place, and the two databases' tables and rows compared.
set -uo pipefail
source /home/user/openFermentUI/bughunt/lib/env.sh
LIB="$1"; OUT="$2"
rm -rf "$OUT"; mkdir -p "$OUT/keg/bin" "$OUT/bin" "$OUT/home dir"
cat > "$OUT/bin/brew" <<EOF
#!/bin/bash
[ "\$*" = "--prefix --installed postgresql@17" ] && echo "$OUT/keg" && exit 0
exit 1
EOF
cat > "$OUT/keg/bin/pg_dump" <<EOF
#!/bin/bash
# The night's call, the database openferment named bh_h11_live on the test server.
a=(); for x in "\$@"; do case "\$x" in openferment) a+=("$BH_SERVER/bh_h11_live") ;; -h|127.0.0.1) ;; *) a+=("\$x") ;; esac; done
printf 'pg_dump %s\n' "\$*" >> "$OUT/calls"
exec /usr/bin/pg_dump "\${a[@]}"
EOF
chmod 755 "$OUT/bin/brew" "$OUT/keg/bin/pg_dump"
bh_db_fresh bh_h11_live || exit 1
# A project and a few rows, made through the API of a service over bh_h11_live.
o="$(BH_KEEP_DB=1 bh_svc_start bh_h11_live 8911)" || exit 1
bh_project "$o" dump-check "Dump check" > "$OUT/project.json"
bh_svc_stop 8911
HOME="$OUT/home dir" PATH="$OUT/bin:/usr/bin:/bin" bash -c 'set -euo pipefail; source "$1"; backup_database' _ "$LIB" > "$OUT/backup.out" 2>&1
echo "backup_database exit $?"; cat "$OUT/backup.out"
dump="$(ls "$OUT/home dir/openferment-backups/"openferment-*.dump)"
pg_restore -l "$dump" | grep -c ' TABLE ' | sed 's/^/tables in the dump: /'
# The runbook's restore, the name openferment_restored standing as bh_h11_restored.
bh_db_drop bh_h11_restored
createdb -d "$BH_SERVER/postgres" bh_h11_restored 2>/dev/null || psql "$BH_SERVER/postgres" -qXc 'CREATE DATABASE bh_h11_restored'
pg_restore -d "$BH_SERVER/bh_h11_restored" "$dump" > "$OUT/restore.out" 2>&1
echo "pg_restore exit $?"; head -20 "$OUT/restore.out"
q="SELECT n.nspname||'.'||c.relname, (xpath('/row/c/text()', query_to_xml('select count(*) as c from '||quote_ident(n.nspname)||'.'||quote_ident(c.relname), false, true, '')))[1]::text FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE c.relkind='r' AND n.nspname IN ('openferment','sci_rag','public') ORDER BY 1"
psql "$BH_SERVER/bh_h11_live" -XtAc "$q" > "$OUT/live.rows"
psql "$BH_SERVER/bh_h11_restored" -XtAc "$q" > "$OUT/restored.rows"
echo "tables live: $(wc -l < "$OUT/live.rows"), restored: $(wc -l < "$OUT/restored.rows")"
diff "$OUT/live.rows" "$OUT/restored.rows" && echo "every table and its row count the same"
psql "$BH_SERVER/bh_h11_restored" -XtAc "select extname||' '||extversion from pg_extension order by 1"
bh_db_drop bh_h11_restored; bh_db_drop bh_h11_live
