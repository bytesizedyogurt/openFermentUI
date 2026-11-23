#!/usr/bin/env bash
# H12-07: CI never holds core/uv.lock. .github/workflows/verify.yml installs the JavaScript side with
# `pnpm install --frozen-lockfile` and runs no `uv sync --frozen|--locked` and no `uv lock --check`; every Python
# stage of `pnpm verify` it runs calls `uv run --all-extras` (neither --frozen nor --locked), which re-locks a
# core/uv.lock that no longer matches core/pyproject.toml, installs what the new lock says, and goes on.
# scripts/host/deploy.sh:80-82 runs the same gate with UV_FROZEN=1 so that it "read[s] core/uv.lock as committed".
#
# In a worktree of 2047f5a of this run's own, with a venv of its own made by CLAUDE.md:20's install
# (`uv sync --frozen --all-extras`, offline, from uv's cache), it makes the commit a person makes when they change
# core/pyproject.toml and leave core/uv.lock: alembic narrowed to <1.20, the lock still pinning alembic 1.20.1. Then:
#   a. the holding steps CI lacks: `uv lock --check` and `uv sync --locked --all-extras` (each should refuse);
#   b. CI's form: test:core's own command (package.json:24) on tests/test_db.py (the migrations, alembic's);
#   c. prove's form (`uv run --frozen`, package.json:42), after b, on the lock b left;
#   d. CLAUDE.md:20's install on the commit as pushed (the committed lock restored).
# Offline throughout (uv's cache alone); the repository's own core/.venv is read, never synced.
# A fresh database of its own (bh_r_h12_07_db) stands in OPENFERMENT_DATABASE_URL, the tests' own session
# databases are made under bh_r_h12_07_t; all are dropped, and the worktree removed, at the end.
#   bash bughunt/repro/H12-07/run.sh        (from the repository root; exits 0 either way)
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PYTHONDONTWRITEBYTECODE=1 PGOPTIONS='-c client_min_messages=warning'
unset VIRTUAL_ENV UV_PROJECT_ENVIRONMENT UV_FROZEN UV_LOCKED 2>/dev/null
REV=2047f5a
DB=bh_r_h12_07_db
TPREFIX=bh_r_h12_07_t
S=$BH_WORK/H12-07; mkdir -p "$S"
WT=$S/wt-$$
T=$(mktemp -d "$S/run.XXXXXX")
cleanup() {
  bh_db_drop "$DB"
  for d in $(psql "$BH_SERVER/postgres" -XAtc "select datname from pg_database where datname like '${TPREFIX}%'" 2>/dev/null); do
    bh_db_drop "$d"; done
  git -C "$BH_ROOT" worktree remove --force "$WT" >/dev/null 2>&1; git -C "$BH_ROOT" worktree prune
  rm -rf "$T" "$WT"; rmdir "$S" 2>/dev/null
}
trap cleanup EXIT
fail() { echo "the steps did not complete: $*"; echo "RESULT: NO-DEFECT"; exit 0; }
uvw() { (cd "$WT/core" && bh_env OPENFERMENT_DATABASE_URL="$BH_SERVER/$DB" OPENFERMENT_TEST_DATABASE_URL="$BH_SERVER/$TPREFIX" \
          uv "$@" 2>&1 | grep -v 'UV_NATIVE_TLS'; exit "${PIPESTATUS[0]}"); }
venv_alembic() { "$WT/core/.venv/bin/python" -c "import importlib.metadata as m; print(m.version('alembic'))" 2>/dev/null || echo none; }
lock_alembic() { awk '/^name = "alembic"$/{getline; gsub(/version = |"/,""); print; exit}' "$WT/core/uv.lock"; }
repo_alembic() { "$BH_ROOT/core/.venv/bin/python" -c "import importlib.metadata as m; print(m.version('alembic'))" 2>/dev/null; }
REPO_BEFORE=$(repo_alembic)

# 0. What CI runs, read at $REV (git show; nothing checked out).
echo "0. what CI runs, at $REV:"
YML=$(git -C "$BH_ROOT" show "$REV:.github/workflows/verify.yml") || fail "no verify.yml at $REV"
echo "$YML" | grep -nE '^\s*- (run|uses|name):|^\s+run:' | sed 's/^/   verify.yml:/'
HOLD=$(echo "$YML" | grep -cE 'uv sync|uv lock|--locked|--frozen([^-]|$)|UV_FROZEN|UV_LOCKED')
echo "   lines in verify.yml that hold the Python lock (uv sync, uv lock, --locked, --frozen, UV_FROZEN, UV_LOCKED): $HOLD"
echo "$YML" | grep -n 'frozen-lockfile' | sed 's/^/   verify.yml:/'
PKG=$(git -C "$BH_ROOT" show "$REV:package.json")
CHAIN=$(echo "$PKG" | grep -oP '"verify": "\K[^"]*' | grep -oP 'pnpm \K[a-z:]+')
UNHELD=0
for s in $CHAIN; do
  cmd=$(echo "$PKG" | grep -oP "^\s*\"$s\": \"\K.*(?=\",?$)")
  case "$cmd" in *"uv run"*)
    case "$cmd" in *--frozen*|*--locked*) held=held ;; *) held="neither --frozen nor --locked"; UNHELD=$((UNHELD+1)) ;; esac
    echo "   verify stage $s: $(echo "$cmd" | grep -oP 'uv run [^ ]+( [^ ]+)?') ($held)";;
  esac
done
echo "   prove (CI's last step): $(echo "$PKG" | grep -oP '"prove": "\K[^"]*')"
git -C "$BH_ROOT" show "$REV:scripts/host/deploy.sh" | sed -n '80,82p' | sed 's/^/   deploy.sh:/'

# 1. A worktree of its own, its venv made by CLAUDE.md:20's install.
git -C "$BH_ROOT" worktree add --detach "$WT" "$REV" >/dev/null 2>&1 || fail "no worktree at $REV"
bh_db_fresh "$DB" || fail "bh_db_fresh $DB"
echo "1. worktree $WT at $(git -C "$WT" rev-parse --short HEAD); database $DB (fresh)"
uvw sync --frozen --offline --all-extras > "$T/sync0.log"; SYNC0=$?
echo "   uv sync --frozen --offline --all-extras (CLAUDE.md:20): exit $SYNC0, $(grep -m1 -E '^Installed|^Resolved' "$T/sync0.log")"
[ "$SYNC0" = 0 ] || fail "the frozen install did not run: $(tail -2 "$T/sync0.log")"
V0=$(venv_alembic)
echo "   alembic: core/uv.lock pins $(lock_alembic), the worktree's venv holds $V0"

# 2. The commit: core/pyproject.toml changed, core/uv.lock left as it was.
sed -i 's/^    "alembic>=1.13",$/    "alembic>=1.13,<1.20",/' "$WT/core/pyproject.toml"
echo "2. the stale lock: $(git -C "$WT" diff --stat | tail -1 | sed 's/^ *//'); $(grep -n '"alembic' "$WT/core/pyproject.toml" | sed 's/^/pyproject.toml:/;s/ \{2,\}/ /')"
git -C "$WT" diff --quiet -- core/uv.lock && echo "   core/uv.lock unchanged, still pinning alembic $(lock_alembic)"

# a. The holding steps CI lacks.
uvw lock --check --offline > "$T/check.log"; CHECK=$?
echo "a. uv lock --check: exit $CHECK, $(grep -m1 '^error' "$T/check.log")"
uvw sync --locked --offline --all-extras > "$T/locked.log"; LOCKED=$?
echo "   uv sync --locked --all-extras: exit $LOCKED, $(grep -m1 '^error' "$T/locked.log"); the venv's alembic $(venv_alembic)"

# b. CI's form: test:core's command (package.json:24) on one file, the migrations' tests.
uvw run --offline --all-extras pytest tests/test_db.py -q -p no:cacheprovider -m "not live and not sim and not slow and not lit" > "$T/ci.log"; CI=$?
echo "b. uv run --all-extras pytest tests/test_db.py -m \"not live and not sim and not slow and not lit\": exit $CI, $(tail -1 "$T/ci.log")"
grep -E '^(Uninstalled|Installed)' "$T/ci.log" | sed 's/^/   /'
LOCKDIFF=$(git -C "$WT" diff --stat -- core/uv.lock | tail -1 | sed 's/^ *//')
L1=$(lock_alembic); V1=$(venv_alembic)
echo "   core/uv.lock after: ${LOCKDIFF:-unchanged}; it pins alembic $L1, the venv holds $V1"
git -C "$WT" diff -U0 -- core/uv.lock | grep -E '^[-+](version|    \{ name = "alembic")' | sed 's/^/   uv.lock diff: /'

# c. prove's form after verify's stages, on the lock b left.
uvw run --frozen --offline --all-extras python -c "import alembic; print('alembic', alembic.__version__)" > "$T/prove.log"; PROVE=$?
PV=$(grep -oP '^alembic \K\S+' "$T/prove.log")
echo "c. uv run --frozen --all-extras (prove's form) after b: exit $PROVE, alembic ${PV:-none}"

# d. CLAUDE.md:20's install on the commit as pushed: the committed lock restored.
git -C "$WT" checkout -q -- core/uv.lock
uvw sync --frozen --offline --all-extras > "$T/sync1.log"; SYNC1=$?
V2=$(venv_alembic)
echo "d. the committed lock restored; uv sync --frozen --all-extras: exit $SYNC1, $(grep -E '^ [-+] alembic' "$T/sync1.log" | tr '\n' ' ')"
echo "   alembic: core/pyproject.toml asks $(grep -oP '"alembic\K[^"]*' "$WT/core/pyproject.toml"), core/uv.lock pins $(lock_alembic), the install holds $V2"
REPO_AFTER=$(repo_alembic)
echo "   the repository's own core/.venv (read only): alembic $REPO_BEFORE before, $REPO_AFTER after"

echo "EXPECTED: CI fails a commit whose core/uv.lock no longer matches core/pyproject.toml, the way it fails a stale pnpm-lock.yaml (verify.yml:68 --frozen-lockfile), through a step such as uv lock --check or uv sync --locked --all-extras (here each exits 1); and verify's stages run on the versions the committed lock pins (CLAUDE.md:40), the ones CLAUDE.md:20's frozen install installs, as deploy.sh:80-82 runs the same gate with UV_FROZEN=1 to read core/uv.lock as committed"
echo "OBSERVED: verify.yml holds the Python lock on $HOLD lines; $UNHELD of verify's uv run stages carry neither --frozen nor --locked; with pyproject asking alembic >=1.13,<1.20 and core/uv.lock pinning 1.20.1, uv lock --check exits $CHECK and uv sync --locked exits $LOCKED, while test:core's form exits $CI ($(tail -1 "$T/ci.log")) after rewriting core/uv.lock (${LOCKDIFF:-unchanged}) to alembic $L1 and installing $V1; prove's frozen form then runs on alembic ${PV:-none}; the committed lock's frozen install (CLAUDE.md:20) holds alembic $V2, a version pyproject excludes and CI never ran"
if [ "$HOLD" = 0 ] && [ "$UNHELD" -gt 0 ] && [ "$V0" = 1.20.1 ] && [ "$CHECK" != 0 ] && [ "$LOCKED" != 0 ] \
   && [ "$CI" = 0 ] && [ -n "$LOCKDIFF" ] && [ "$L1" != 1.20.1 ] && [ "$V1" = "$L1" ] && [ "${PV:-}" = "$L1" ] \
   && [ "$SYNC1" = 0 ] && [ "$V2" = 1.20.1 ] && [ "$REPO_BEFORE" = "$REPO_AFTER" ]; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
