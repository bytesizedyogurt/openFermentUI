#!/usr/bin/env bash
# R1: two Departures rows of docs/PROGRESS.md held to the tree at 2047f5a (R1-02, R1-04). Read-only.
# Usage: bash bughunt/notes/R1/scripts/stale_rows.sh   (from the repository's root)
C=${1:-2047f5a}
echo "== R1-02: row 467 says"; git show $C:docs/PROGRESS.md | sed -n 467p | grep -o "No store holds a protocol in this build[^|]*"
echo "-- the tree at $C holds a protocol store:"
git show $C:core/openferment_core/db/alembic/versions/0010_protocols.py | grep -n "create_table('protocols'"
git show $C:docs/api/openapi.json | python3 -c "import json,sys; print([p for p in json.load(sys.stdin)['paths'] if 'protocol' in p])"
git log --format='   made at %h %s' -1 37addaf | cut -c1-110
echo "-- ADR-016 notes it, the row does not:"; git show $C:docs/decisions/ADR-016-bench-readings-alone.md | grep -n "Implementation note (alpha 2.2 E.12a)"
echo "== R1-04: row 543 says"; git show $C:docs/PROGRESS.md | sed -n 543p | grep -o "three preferences[^|]*"
echo "-- row 502 of the same table says"; git show $C:docs/PROGRESS.md | sed -n 502p | grep -o "The Durable snapshot keeps no lesson[^:]*"
echo "-- src/lib/durable.ts at $C:"; git show $C:src/lib/durable.ts | grep -n -B5 "learnProgress?:" | sed -n 1,6p
echo "-- readers of learnProgress in src/ at $C (the type alone):"; git grep -n "learnProgress" $C -- src
