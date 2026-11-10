#!/usr/bin/env bash
# H11-04: the night's dump reads the database named `openferment`, whatever database core/.env's
# OPENFERMENT_DATABASE_URL names for the night's other four steps and for the service.
#
# A scratch worktree at 2047f5a runs scripts/host/nightly.sh as launchd starts it (env -i, PATH and
# HOME alone, /bin/bash). Stand-ins: `brew` names a keg whose `pg_dump` is a wrapper over the real
# /usr/bin/pg_dump on the hunt's test server, and the worktree's core/.venv/bin/python records each
# `-m openferment_core.*` call with the OPENFERMENT_DATABASE_URL nightly.sh exported to it.
# The test server may hold bh_* databases alone, so the wrapper reads the plain name `openferment`
# as the test database that stands for it on the Mini's server (bh_r_h11_04_openferment, a
# leftover with a project of its own, or a missing database in night C), and reads any name or
# address ending in a bh_r_h11_04_* database as that database itself; it refuses everything else.
#   night 0 (control): core/.env names .../openferment, as install.sh writes it.
#   night A: core/.env names .../bh_r_h11_04_live (ensure_database accepts it), a database
#            named openferment is also on the server.
#   night C: the same core/.env, no database named openferment on the server.
# Every database is made fresh here and dropped after; the worktree is removed after.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
cd "$BH_ROOT" || exit 0
SHA=2047f5a; PORT=9670
LIVE=bh_r_h11_04_live; LEFT=bh_r_h11_04_openferment; ABSENT=bh_r_h11_04_absent
OUT="$BH_WORK/H11-04"; W="$OUT/wt"
cleanup() {
  bh_svc_stop "$PORT"
  for d in "$LIVE" "$LEFT" "$ABSENT"; do bh_db_drop "$d" 2>/dev/null; done
  git -C "$BH_ROOT" worktree remove --force "$W" >/dev/null 2>&1; git -C "$BH_ROOT" worktree prune
  rm -rf "$OUT" "$BH_WORK/data-$LIVE" "$BH_WORK/data-$LEFT"
}
trap cleanup EXIT
cleanup; mkdir -p "$OUT/bin" "$OUT/keg/bin" "$OUT/ens-bin"
git -C "$BH_ROOT" worktree add --detach "$W" "$SHA" >/dev/null 2>&1 ||
  { echo "OBSERVED: no worktree"; echo "RESULT: NO-DEFECT"; exit 0; }
echo "worktree: $W at $(git -C "$W" rev-parse --short HEAD)"

echo; echo "== 1. the contract and the code, as $SHA holds them"
show() { sed -n "$2p" "$W/$1" | sed "s|^ *|   $1:$2: |"; }
show scripts/host/nightly.sh 21; show scripts/host/nightly.sh 22; show scripts/host/nightly.sh 24
show scripts/host/nightly.sh 25; show scripts/host/nightly.sh 26
show scripts/host/nightly.sh 30; show scripts/host/nightly.sh 31
show scripts/host/lib.sh 151; show scripts/host/lib.sh 152
show scripts/host/lib.sh 187; show scripts/host/lib.sh 188
sed -n 240p "$W/docs/runbooks/live-host-install.md" | grep -o "The night's dump holds the whole database\." |
  sed 's|^|   docs/runbooks/live-host-install.md:240: |'
sed -n 260p "$W/docs/runbooks/live-host-install.md" | grep -o "dumps the database \`openferment\`" |
  sed 's|^|   docs/runbooks/live-host-install.md:260: |'
echo "   lines of backup_database (lib.sh:177-205) reading OPENFERMENT_DATABASE_URL or env_setting: $(sed -n 177,205p "$W/scripts/host/lib.sh" | grep -c 'OPENFERMENT_DATABASE_URL\|env_setting')"

echo; echo "== 2. two test databases on one server, each with a project of its own made through the API"
o="$(bh_svc_start "$LIVE" "$PORT")" || { echo "OBSERVED: no service"; echo "RESULT: NO-DEFECT"; exit 0; }
bh_project "$o" night-live "The night's live project" > "$OUT/p1.json"; bh_svc_stop "$PORT"
o="$(bh_svc_start "$LEFT" "$PORT")" || { echo "OBSERVED: no service"; echo "RESULT: NO-DEFECT"; exit 0; }
bh_project "$o" leftover-only "A leftover database's project" > "$OUT/p2.json"; bh_svc_stop "$PORT"
bh_db_drop "$ABSENT"
for d in "$LIVE" "$LEFT"; do
  echo "   $d holds projects: $(psql "$BH_SERVER/$d" -XtAc 'select string_agg(id, $$ $$ order by id) from openferment.projects')"
done

# The stand-ins. brew names the keg; the keg's pg_dump records its arguments and runs the real one.
cat > "$OUT/bin/brew" <<EOF
#!/bin/bash
[ "\$*" = "--prefix --installed postgresql@17" ] && echo "$OUT/keg" && exit 0
exit 1
EOF
cat > "$OUT/keg/bin/pg_dump" <<EOF
#!/bin/bash
printf 'pg_dump %s\n' "\$*" >> "$OUT/calls"
a=(); db=""
while [ \$# -gt 0 ]; do
  case "\$1" in
    -h|--host|-p|--port|-U|--username) shift 2 ;;   # the Mini's server stands as the test server
    -d|--dbname) db="\$2"; shift 2 ;;
    --dbname=*) db="\${1#--dbname=}"; shift ;;
    -*) a+=("\$1"); shift ;;
    *) db="\$1"; shift ;;
  esac
done
name="\${db##*/}"; name="\${name%%\\?*}"
case "\$name" in
  openferment) target="\$(cat "$OUT/openferment-is")" ;;
  bh_r_h11_04_*) target="\$name" ;;
  *) echo "stand-in pg_dump: refusing the database \$db" >&2; exit 2 ;;
esac
printf 'pg_dump reads the test database %s\n' "\$target" >> "$OUT/calls"
exec /usr/bin/pg_dump "\${a[@]}" -d "$BH_SERVER/\$target"
EOF
mkdir -p "$W/core/.venv/bin"
cat > "$W/core/.venv/bin/python" <<EOF
#!/bin/bash
printf '%s\n' "python \$* DB=\${OPENFERMENT_DATABASE_URL:-<unset>} PROJECT=\${OPENFERMENT_PROJECT:-<unset>}" >> "$OUT/calls"
exit 0
EOF
chmod 755 "$OUT/bin/brew" "$OUT/keg/bin/pg_dump" "$W/core/.venv/bin/python"

night() { # night LABEL URL-DATABASE OPENFERMENT-STANDS-AS
  local label="$1" home="$OUT/home-$1"
  printf 'OPENFERMENT_DATABASE_URL=postgresql://openferment@127.0.0.1:5432/%s\nOPENFERMENT_PROJECT=night-live\n' "$2" > "$W/core/.env"
  printf '%s' "$3" > "$OUT/openferment-is"; : > "$OUT/calls"; mkdir -p "$home"
  env -i PATH="$OUT/bin:/usr/bin:/bin" HOME="$home" /bin/bash "$W/scripts/host/nightly.sh" > "$OUT/night-$label.log" 2>&1
  local rc=$?
  echo "   core/.env: $(head -1 "$W/core/.env")"
  echo "   nightly.sh exit $rc"
  sed "s|$OUT|\$OUT|g; s/^/   call: /" "$OUT/calls"
  grep -E 'dumped into|failed|does not exist' "$OUT/night-$label.log" | sed "s|$OUT|\$OUT|g; s/^/   log: /"
  eval "RC_$label=$rc"
  local dump; dump="$(ls "$home/openferment-backups/"openferment-*.dump 2>/dev/null | head -1)"
  if [ -n "$dump" ]; then
    pg_restore -f - "$dump" > "$OUT/dump-$label.sql" 2>/dev/null
    eval "LIVE_IN_$label=$(grep -c 'night-live' "$OUT/dump-$label.sql")"
    eval "LEFT_IN_$label=$(grep -c 'leftover-only' "$OUT/dump-$label.sql")"
    echo "   the kept dump ${dump##*/}: lines naming night-live $(eval echo \$LIVE_IN_$label), naming leftover-only $(eval echo \$LEFT_IN_$label)"
  else
    eval "LIVE_IN_$label=none"; eval "LEFT_IN_$label=none"
    echo "   no dump kept in $home/openferment-backups/" | sed "s|$OUT|\$OUT|"
  fi
  eval "WORK_DB_$label=\"$(grep -m1 -o 'openferment_core.extract --all DB=[^ ]*' "$OUT/calls" | sed 's|.*/||')\""
  eval "DUMP_DB_$label=\"$(grep -m1 '^pg_dump -' "$OUT/calls" | awk '{print $NF}')\""
}

echo; echo "== 3. ensure_database (install.sh's step) over night A's core/.env"
printf 'OPENFERMENT_DATABASE_URL=postgresql://openferment@127.0.0.1:5432/%s\n' "$LIVE" > "$W/core/.env"
env -i PATH="$OUT/ens-bin:/usr/bin:/bin" HOME="$OUT/home-ens" /bin/bash -c 'source "$1"; ensure_database; echo "exit $?"' _ \
  "$W/scripts/host/lib.sh" 2>&1 | sed 's/^/   /'

echo; echo "== 4. night 0 (control): core/.env names the database openferment, as install.sh writes it"
night 0 openferment "$LEFT"
echo; echo "== 5. night A: core/.env names $LIVE, and a database named openferment is on the server"
night A "$LIVE" "$LEFT"
echo; echo "== 6. night C: core/.env names $LIVE, and no database named openferment is on the server"
night C "$LIVE" "$ABSENT"
rm -f "$W/core/.env"

echo; echo "== 7. the stand-in pg_dump, given the address core/.env names in nights A and C"
: > "$OUT/calls"
"$OUT/keg/bin/pg_dump" -h 127.0.0.1 --format=custom --file="$OUT/by-url.dump" \
  --dbname="postgresql://openferment@127.0.0.1:5432/$LIVE" 2>&1 | sed 's/^/   /'
sed "s|$OUT|\$OUT|g; s/^/   call: /" "$OUT/calls"
BY_URL=$(pg_restore -f - "$OUT/by-url.dump" 2>/dev/null | grep -c 'night-live')
echo "   that dump's lines naming night-live: $BY_URL"

echo
echo "EXPECTED: each night pg_dump reads the database the night's four python steps are given, the one core/.env's OPENFERMENT_DATABASE_URL names: night A's and night C's dump hold $LIVE's project night-live (nightly.sh:30 \"The database as the night finds it, before the night's work writes to it\")."
echo "OBSERVED: night 0: the work given '$WORK_DB_0', pg_dump asked for '$DUMP_DB_0', exit $RC_0. Night A: the work given '$WORK_DB_A', pg_dump asked for '$DUMP_DB_A', exit $RC_A, the dump's lines naming night-live $LIVE_IN_A and naming leftover-only $LEFT_IN_A. Night C: the work given '$WORK_DB_C', pg_dump asked for '$DUMP_DB_C', exit $RC_C, dump kept: $([ "$LIVE_IN_C" = none ] && echo none || echo yes). The same stand-in given core/.env's address dumps night-live ($BY_URL lines)."
if [ "$WORK_DB_A" = "$LIVE" ] && [ "$DUMP_DB_A" = openferment ] && [ "$RC_A" = 0 ] &&
   [ "$LIVE_IN_A" = 0 ] && [ "$LEFT_IN_A" != 0 ] && [ "$LEFT_IN_A" != none ]; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
