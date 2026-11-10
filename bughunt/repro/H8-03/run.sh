#!/usr/bin/env bash
# H8-03: an upload whose file name holds %00 answers 500 after the kit has committed the document,
# which no project then holds; the next project to upload the same bytes links a document whose
# source names the first project and whose sourceRef is the server's removed temporary file.
# The head's own service on a fresh test database, a free port in 9430-9439; keyless, no model call.
# usage, from the repository root: bash bughunt/repro/H8-03/run.sh
source /home/user/openFermentUI/bughunt/lib/env.sh
DB=bh_r_h8_03_svc
T=$BH_WORK/H8-03; mkdir -p "$T"
PORT=""
for p in $(seq 9430 9439); do [ -z "$(bh_port_pid "$p")" ] && { PORT=$p; break; }; done
cleanup() { [ -n "$PORT" ] && { bh_svc_stop "$PORT"; rm -f "$BH_WORK/svc-$PORT.log"; }; bh_db_drop "$DB"; rm -rf "$BH_WORK/data-$DB" "$T"; }
trap cleanup EXIT
q() { psql "$BH_SERVER/$DB" -AtXF ' | ' -c "$1"; }
c() { curl -s --noproxy '*' "$@"; }

echo "EXPECTED: POST /api/intake/upload of report%00.md answers HTTP 200 with a CollectOutcome (status failed and the"
echo "EXPECTED: reason in words, or the name kept and the document stored), and leaves no kit document that no project"
echo "EXPECTED: holds (docs/api/intake.md:55-56: the route raises no 5xx for a document it could not collect)."
[ -n "$PORT" ] || { echo "OBSERVED: no free port in 9430-9439"; echo "RESULT: NO-DEFECT"; exit 0; }

O=$(bh_svc_start "$DB" "$PORT") || { echo "OBSERVED: the service did not start"; echo "RESULT: NO-DEFECT"; exit 0; }
bh_project "$O" h803a >/dev/null; bh_project "$O" h803b >/dev/null 2>&1
echo "service on port $PORT over database $DB"
printf '# H8-03 percent name\n\nA note whose file name carries a percent-encoded NUL, for the H8-03 repro.\n' > "$T/note.md"

# 1. Project h803a uploads the note under the name report%00.md.
codeA=$(c -o "$T/a.out" -w '%{http_code}' -H 'X-OpenFerment-Project: h803a' -X POST "$O/api/intake/upload" \
        -F "file=@$T/note.md;filename=report%00.md;type=text/markdown" -F by=a)
echo "step 1: h803a uploads report%00.md -> HTTP $codeA: $(head -c 160 "$T/a.out")"
nA=$(c -H 'X-OpenFerment-Project: h803a' "$O/api/literature/documents" | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))')
links=$(q "select count(*) from openferment.documents_link")
orphans=$(q "select count(*) from sci_rag.documents d where not exists (select 1 from openferment.documents_link l where l.document_id = d.id)")
echo "step 1: documents h803a holds: $nA | kit documents: $(q 'select count(*) from sci_rag.documents') | project links: $links | kit documents no project links: $orphans"
q "select 'step 1: unlinked kit document ' || id, 'source ' || source, 'source_ref ' || source_ref from sci_rag.documents d where not exists (select 1 from openferment.documents_link l where l.document_id = d.id)"
grep -m1 -o 'invalid byte sequence for encoding "UTF8": 0x00' "$BH_WORK/svc-$PORT.log" | sed 's/^/step 1: service log: /'
grep -m1 -F '[SQL: UPDATE documents SET source_ref' "$BH_WORK/svc-$PORT.log" | sed 's/^/step 1: service log: /'
grep -m1 -F "[parameters: ('upload:report" "$BH_WORK/svc-$PORT.log" | sed 's/^/step 1: service log: /'
grep -E 'File ".*openferment_core/(intake|literature/kit)\.py", line' "$BH_WORK/svc-$PORT.log" | sort -u | sed 's#.*openferment_core/#step 1: traceback frame: #'

# 2. Project h803b uploads the same bytes as report.md.
c -o "$T/b.out" -H 'X-OpenFerment-Project: h803b' -X POST "$O/api/intake/upload" \
  -F "file=@$T/note.md;filename=report.md;type=text/markdown" -F by=b
statusB=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("status"))' "$T/b.out")
c -H 'X-OpenFerment-Project: h803b' "$O/api/literature/documents" > "$T/b.docs"
read -r srcB refB < <(python3 -c 'import json,sys; d=json.load(open(sys.argv[1]))[0]; print(d["source"], d["sourceRef"])' "$T/b.docs")
there=no; [ -e "$refB" ] && there=yes
echo "step 2: h803b uploads report.md -> status $statusB | its document: source $srcB | sourceRef $refB (file exists: $there)"

echo "OBSERVED: h803a's upload answered HTTP $codeA and h803a holds $nA documents, while the kit keeps $orphans document(s) no project links;"
echo "OBSERVED: h803b's upload of the same bytes answered $statusB, its document's source is $srcB and its sourceRef is $refB."
if [ "$codeA" = 500 ] && [ "${orphans:-0}" -ge 1 ] && [ "$statusB" = linked ] && [ "$srcB" = project:h803a:upload ]; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
