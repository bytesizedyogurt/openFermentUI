#!/usr/bin/env bash
# R1-03 (and R2-01): `lit:graph --dry-run` sums every batch's prompt into one count and prices that sum as one
# request, so Haiku 5.5's long-prompt tier (past 100,000 prompt tokens a request) prices every batch; the build
# sends one request a batch, each far under the threshold. The records' 0.2199 and 2.3239 USD come from this sum.
# Keyless, no model call, no service: a fresh database holding 120 passages of placeholder words in 12 documents,
# the real CLI's dry run over it (whole and --limit 40), the build on a client that records each request, and
# graph_command's own dry-run branch over F.5's recorded measure.
# usage, from the repository root: bash bughunt/repro/R1-03/run.sh
source /home/user/openFermentUI/bughunt/lib/env.sh
HERE=/home/user/openFermentUI/bughunt/repro/R1-03
DB=bh_r_r1_03_run
T=$BH_WORK/R1-03; mkdir -p "$T"
export PYTHONDONTWRITEBYTECODE=1
cleanup() { bh_db_drop "$DB"; rm -rf "$T"; }
trap cleanup EXIT

bh_db_fresh "$DB" || { echo "OBSERVED: the fresh database could not be made"; echo "RESULT: NO-DEFECT"; exit 0; }
# One project, 12 documents of 10 passages each, every passage 4,000 characters (the kit's cut per passage),
# so each batch is the largest a batch can be. Placeholder words alone; nothing scientific.
psql "$BH_SERVER/$DB" -qX -v ON_ERROR_STOP=1 <<'SQL' || { echo "OBSERVED: the seed failed"; echo "RESULT: NO-DEFECT"; exit 0; }
INSERT INTO openferment.projects (id, name, created_by) VALUES ('r103', 'r103', 'bughunt');
INSERT INTO sci_rag.documents (id, title, source, authors, license_class, content_hash, chunk_count, extra)
SELECT 'r103doc' || lpad(d::text, 3, '0'), 'Placeholder document ' || d, 'bughunt-r103', ARRAY['bughunt'], 'open',
       md5('r103doc' || d) || md5('r103doc' || d), 10, '{}'::jsonb
FROM generate_series(1, 12) AS d;
INSERT INTO sci_rag.chunks (id, document_id, chunk_index, content, token_count, is_table)
SELECT 'r103c' || lpad(d::text, 3, '0') || lpad(c::text, 3, '0'), 'r103doc' || lpad(d::text, 3, '0'), c,
       left(repeat('placeholder passage ' || c || ' of document ' || d || ' words words words. ', 200), 4000), 1000, false
FROM generate_series(1, 12) AS d, generate_series(0, 9) AS c;
INSERT INTO openferment.documents_link (project_id, document_id, selection, created_by)
SELECT 'r103', id, '{}'::json, 'bughunt' FROM sci_rag.documents WHERE source = 'bughunt-r103';
SQL

on_db() { (cd "$BH_ROOT/core" && bh_env OPENFERMENT_INDEX_MODEL=claude-haiku-5-5 OPENFERMENT_DATABASE_URL="$BH_SERVER/$DB" \
  .venv/bin/python "$@"); }
echo "the real dry run, the first 40 passages: python -m openferment_core.literature_live graph --project r103 --dry-run --limit 40"
on_db -m openferment_core.literature_live graph --project r103 --dry-run --limit 40 | tee "$T/dry40.json"
echo "the real dry run, every passage: python -m openferment_core.literature_live graph --project r103 --dry-run"
on_db -m openferment_core.literature_live graph --project r103 --dry-run | tee "$T/dry.json"
on_db "$HERE/check.py" "$T/dry40.json" "$T/dry.json" | tee "$T/check.log"

echo "the records that carry the dry run's figures (git grep at 2047f5a):"
git -C "$BH_ROOT" grep -n -e '2\.3239' -e '0\.2199' 2047f5a -- docs | cut -c1-220
recorded=$(git -C "$BH_ROOT" grep -c -e '2\.3239' 2047f5a -- docs | awk -F: '{s+=$NF} END {print s+0}')
echo "OBSERVED: $recorded line(s) of docs/ at 2047f5a carry 2.3239 USD, the dry run's sum-priced ceiling"

if grep -q '^VERDICT: DEFECT$' "$T/check.log" && [ "${recorded:-0}" -gt 0 ]; then echo "RESULT: DEFECT"; else echo "RESULT: NO-DEFECT"; fi
exit 0
