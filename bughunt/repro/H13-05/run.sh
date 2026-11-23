#!/usr/bin/env bash
# H13-05: examples/engines/openferment-engine-mirror/README.md followed line by line in a clean checkout
# of 2047f5a. Line 8 puts the reader in `core/`, line 9 in the package's own directory, and line 10
# begins `cd core &&`, which works from the repository root alone, a directory no line names. The
# verdict rests on that line. Printed beside it: the page itself names no database setting for line 10
# (its line 3 names docs/api/engines.md, which does), and the record-reader page names project `proof`
# and a running service and no command that makes either.
# Keyless, no network, no model call, no service. `uv` is a stand-in on PATH that prints what it was
# asked, so no line here installs into or syncs core's environment; line 8's install is stood in by an
# entry-point record on PYTHONPATH (what an editable install writes), so core/.venv is never changed.
# usage, from the repository root: bash bughunt/repro/H13-05/run.sh
source /home/user/openFermentUI/bughunt/lib/env.sh
COMMIT=2047f5a
DB=bh_r_h13_05_cfg
SCRATCH_PREFIX=bh_r_h13_05_conform
T=$BH_WORK/H13-05/run-$$
WT=$T/wt
PKG_REL=examples/engines/openferment-engine-mirror
RR_REL=examples/agents/record-reader

cleanup() {
  bh_db_drop "$DB"
  for d in $(psql "$BH_SERVER/postgres" -qAtXc \
      "SELECT datname FROM pg_database WHERE datname LIKE '${SCRATCH_PREFIX}%'" 2>/dev/null); do
    bh_db_drop "$d"
  done
  git -C "$BH_ROOT" worktree remove --force "$WT" >/dev/null 2>&1
  git -C "$BH_ROOT" worktree prune >/dev/null 2>&1
  rm -rf "$T"
}
trap cleanup EXIT

mkdir -p "$T/stub" "$T/site/openferment_engine_mirror-0.1.0.dist-info"
git -C "$BH_ROOT" worktree add --detach "$WT" "$COMMIT" >/dev/null 2>&1 \
  || { echo "OBSERVED: the worktree at $COMMIT could not be made"; echo "RESULT: NO-DEFECT"; exit 0; }
# The checkout's core/.venv: core's own environment, read only (nothing below runs uv or pip in it).
ln -s "$BH_ROOT/core/.venv" "$WT/core/.venv"
# uv, stood in: it says where it was reached from and with what, and does nothing else.
cat > "$T/stub/uv" <<'EOF'
#!/usr/bin/env bash
echo "(uv reached, from $(pwd): uv $*)"
EOF
chmod +x "$T/stub/uv"
# Line 8's install, stood in: the entry point an install of the package registers, with the checkout's
# package directory on PYTHONPATH.
printf 'Metadata-Version: 2.1\nName: openferment-engine-mirror\nVersion: 0.1.0\n' \
  > "$T/site/openferment_engine_mirror-0.1.0.dist-info/METADATA"
printf '[openferment.engines]\nmirror = openferment_engine_mirror.engine:ENGINE\n' \
  > "$T/site/openferment_engine_mirror-0.1.0.dist-info/entry_points.txt"
INSTALLED="$T/site:$WT/$PKG_REL"
run() { bh_env env -u OPENFERMENT_DATABASE_URL PATH="$T/stub:$PATH" PYTHONDONTWRITEBYTECODE=1 \
          PYTEST_ADDOPTS="-p no:cacheprovider" PYTHONPATH="$INSTALLED" "$@"; }

PAGE="$WT/$PKG_REL/README.md"
span() { sed -n "${1}p" "$PAGE" | grep -o '`[^`]*`' | tail -1 | tr -d '`'; }
L9=$(span 9); L10=$(span 10)
echo "EXPECTED: each command line of the mirror's README runs from the directory the page leaves the reader"
echo "EXPECTED: in (line 8: \"from the repository's \`core/\`\"; line 9: \"Test from this directory\"): line 10,"
echo "EXPECTED: \"Check it against the contract on a PostgreSQL server: \`cd core && uv run ...\`\", reaches uv from"
echo "EXPECTED: the package's directory where line 9 leaves the reader."
echo
echo "== the page, lines 8 to 10 ($PKG_REL/README.md)"
sed -n 8,10p "$PAGE" | cut -c1-140
echo "line 9's command:  $L9"
echo "line 10's command: $L10"
[ -n "$L9" ] && [ -n "$L10" ] || { echo "OBSERVED: lines 9 and 10 carry no command"; echo "RESULT: NO-DEFECT"; exit 0; }

echo
echo "== line 9, from the directory it names ($PKG_REL)"
(cd "$WT/$PKG_REL" && run bash -c "$L9" 2>&1 | tail -1)

echo
echo "== line 10 as written, from line 9's directory ($PKG_REL)"
out_pkg=$(cd "$WT/$PKG_REL" && run bash -c "$L10" 2>&1); rc_pkg=$?
echo "$out_pkg"; echo "exit $rc_pkg"
echo "== line 10 as written, from line 8's directory (core/)"
out_core=$(cd "$WT/core" && run bash -c "$L10" 2>&1); rc_core=$?
echo "$out_core"; echo "exit $rc_core"
echo "== line 10 as written, from the repository root (a directory no line of the page names)"
out_root=$(cd "$WT" && run bash -c "$L10" 2>&1); rc_root=$?
echo "$out_root"; echo "exit $rc_root"

echo
# `uv run python` stood in by core's environment's python (a real `uv run` would sync it), from core/.
CONFORM=${L10#cd core && uv run python }
echo "== line 10's check from the root, \`uv run python\` stood in by core/.venv/bin/python: python $CONFORM"
echo "-- the clean checkout holds no core/.env and the page names no setting"
noaddr=$(cd "$WT/core" && run .venv/bin/python $CONFORM 2>&1); rc_noaddr=$?
echo "$noaddr" | grep -v UV_NATIVE | tail -1 | cut -c1-400; echo "exit $rc_noaddr"
echo "-- with OPENFERMENT_DATABASE_URL naming a fresh migrated database ($DB), the checks' own database"
echo "   named $SCRATCH_PREFIX... in memory (the hunt's naming rule)"
if bh_db_fresh "$DB"; then
  mod=${CONFORM#-m }; eng=${mod#openferment_core.engine.conform }
  withaddr=$(cd "$WT/core" && run OPENFERMENT_DATABASE_URL="$BH_SERVER/$DB" .venv/bin/python -c \
    "import sys; from openferment_core.engine import conform; conform.SCRATCH='$SCRATCH_PREFIX'; sys.exit(conform.main(sys.argv[1:]))" \
    $eng 2>&1); rc_addr=$?
  echo "$withaddr" | grep -E '^(mirror|✗|✓ [0-9])' | cut -c1-140; echo "exit $rc_addr"
else
  echo "the database $DB could not be made"; rc_addr=-1
fi

echo
echo "== what the mirror page names for line 10 and for line 8's \"then restart the service\""
setting=$(grep -c -E 'OPENFERMENT_DATABASE_URL|core/\.env|db:up|db:migrate|db:reset|BASE\.md|repository root|repository.s root' "$PAGE")
starts=$(grep -c -E 'pnpm|uvicorn|scripts/host|launchctl' "$PAGE")
echo "lines naming the database setting, its setup or the repository root: $setting"
echo "lines naming a command that starts the service: $starts (line 8 says \"then restart the service\")"
echo "the page names its contract page on line $(grep -n 'docs/api/engines.md' "$PAGE" | cut -d: -f1 | paste -sd, -);"
echo "that page holds the setting and the root-relative form of line 10:"
(cd "$WT" && grep -n -E 'Run it as .cd core && uv run python -m openferment_core.engine.conform|^  --port 8000.. It reads .OPENFERMENT_DATABASE_URL|^.OPENFERMENT_DATABASE_URL. names \(the environment first' docs/api/engines.md | cut -c1-120)

echo
echo "== the record-reader page ($RR_REL/README.md)"
RRP="$WT/$RR_REL/README.md"
sed -n 2p "$RRP" | cut -c1-140
rr_named=$(grep -c -E -- '--project proof' "$RRP")
rr_source=$(grep -c -E 'pnpm|prove --keep|--keep|BASE\.md|TOOLS\.md|db:up|db:migrate|uvicorn' "$RRP")
echo "lines naming --project proof: $rr_named; lines naming how the project or the service comes to be: $rr_source"
echo "where \`pnpm prove --keep\` (the kept service and its project) is named:"
(cd "$WT" && grep -rn -- 'prove --keep' README.md docs/BASE.md docs/TOOLS.md docs/api/*.md examples | cut -c1-120)

echo
cd_pkg_fails=no; cd_core_fails=no; cd_root_ok=no
echo "$out_pkg" | grep -q 'cd: core: No such file or directory' && [ "$rc_pkg" -ne 0 ] && cd_pkg_fails=yes
echo "$out_core" | grep -q 'cd: core: No such file or directory' && [ "$rc_core" -ne 0 ] && cd_core_fails=yes
echo "$out_root" | grep -q 'uv reached' && cd_root_ok=yes
echo "OBSERVED: line 10 from line 9's directory: $(echo "$out_pkg" | head -1) (exit $rc_pkg)"
echo "OBSERVED: line 10 from line 8's directory core/: $(echo "$out_core" | head -1) (exit $rc_core)"
echo "OBSERVED: line 10 from the repository root reaches uv: $cd_root_ok"
echo "OBSERVED: line 10's check with no database named: $(echo "$noaddr" | grep -v UV_NATIVE | tail -1 | cut -c1-160)... (exit $rc_noaddr)"
echo "OBSERVED: line 10's check with $DB named: $(echo "$withaddr" | grep -E '^mirror' | cut -c1-120) (exit $rc_addr)"
echo "OBSERVED: the mirror page names the database setting on $setting lines and a start command on $starts; it names docs/api/engines.md, which holds both"
echo "OBSERVED: the record-reader page names --project proof on $rr_named line and its source on $rr_source"
if [ "$cd_pkg_fails" = yes ] && [ "$cd_core_fails" = yes ] && [ "$cd_root_ok" = yes ]; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
