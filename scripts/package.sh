#!/bin/bash
# The download: one zip that holds this commit's files and the built app, and
# starts with `bash start.sh` (START-HERE.md).
#
#   bash scripts/package.sh [output directory]      pnpm package
#
# It holds what git tracks at HEAD, plus dist/ built from it. It holds no
# core/.env, no database, no node_modules and no .venv: a key and a person's
# work never enter a package.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
OUT="${1:-$REPO/.package}"
[ -z "$(git status --porcelain --untracked-files=no)" ] || { echo "✗ commit your changes first: the package is what git tracks at HEAD" >&2; exit 1; }
NAME="openFerment-$(node -p "require('./package.json').version")-$(git rev-parse --short HEAD)"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

pnpm build
git archive --format=tar --prefix="$NAME/" HEAD | tar -x -C "$STAGE"
cp -R dist "$STAGE/$NAME/dist"
for f in core/.env node_modules core/.venv .openferment; do
  [ ! -e "$STAGE/$NAME/$f" ] || { echo "✗ $f reached the package" >&2; exit 1; }
done
mkdir -p "$OUT"
rm -f "$OUT/$NAME.zip"
(cd "$STAGE" && zip -qry "$OUT/$NAME.zip" "$NAME")
echo "✓ $OUT/$NAME.zip ($(du -h "$OUT/$NAME.zip" | awk '{print $1}'))"
