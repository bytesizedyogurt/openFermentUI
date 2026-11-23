#!/usr/bin/env bash
# H10-03 (with H8-09): the kit's /rag mount answers four doors with no key, the corpus manifest among
# them with the project's counts, and that manifest names addresses, an embedder and a feature this
# mount does not have.
#   bash bughunt/repro/H10-03/run.sh            (from the repository root)
# Two fresh databases, two keyless services (no model call, nothing leaves 127.0.0.1):
#   A  bh_r_h10_03_nokey on 127.0.0.1:9170 with OPENFERMENT_RAG_KEY empty (ADR-002: "/rag refuses every request")
#   B  bh_r_h10_03_key   on 127.0.0.1:9171 with a throwaway OPENFERMENT_RAG_KEY (CLAUDE.md: "behind OPENFERMENT_RAG_KEY")
# Each project r1 holds one pasted placeholder note, so its counts read 1.
set -u
export PGOPTIONS="-c client_min_messages=warning"
source /home/user/openFermentUI/bughunt/lib/env.sh
cd "$BH_ROOT" || exit 0
DB_A=bh_r_h10_03_nokey; PORT_A=9170; A="http://127.0.0.1:$PORT_A"
DB_B=bh_r_h10_03_key;   PORT_B=9171; B="http://127.0.0.1:$PORT_B"
KEY_B="bh-h10-03-throwaway-rag-key-$RANDOM$RANDOM"
OUT="$BH_WORK/H10-03"
J='content-type: application/json'
cleanup() {
  bh_svc_stop "$PORT_A"; bh_svc_stop "$PORT_B"; bh_db_drop "$DB_A"; bh_db_drop "$DB_B"
  rm -rf "$OUT" "$BH_WORK/data-$DB_A" "$BH_WORK/data-$DB_B"
}
trap cleanup EXIT
cleanup; mkdir -p "$OUT"

echo "tree: $(git rev-parse --short HEAD); core/ src/ scripts/ examples/ docs/ as at 2047f5a: $(git diff --quiet 2047f5a -- core src scripts examples docs CLAUDE.md && echo yes || echo NO)"
code() { curl -s --noproxy '*' -o /dev/null -w '%{http_code}' "$@"; }
paste_one() {  # ORIGIN: project r1 and one pasted placeholder note
  bh_project "$1" r1 >/dev/null
  curl -s --noproxy '*' -m 180 -o /dev/null -w '%{http_code}' -X POST "$1/api/intake/paste" -H "$J" \
    -H 'X-OpenFerment-Project: r1' \
    -d '{"title":"A pasted note","text":"A placeholder note the hunt pastes so the project holds one document.","by":"bughunt","licenceClass":"unknown"}'
}

# ── A: no key set ────────────────────────────────────────────────────────────
export OPENFERMENT_RAG_KEY=''   # stands over core/.env, which the service loads without overriding
bh_svc_start "$DB_A" "$PORT_A" >/dev/null || { echo "OBSERVED: service A did not start"; echo "RESULT: NO-DEFECT"; exit 0; }
unset OPENFERMENT_RAG_KEY
echo "A: service on $A over fresh $DB_A, OPENFERMENT_RAG_KEY empty; paste into r1: $(paste_one "$A")"
echo "   pnpm ready's rag row for this setting (core/openferment_core/ready.py:248):"
sed -n 248p core/openferment_core/ready.py | sed 's/^ */     /'
echo "-- A: every door asked with no key (X-OpenFerment-Project: r1, no Authorization, no X-API-Key)"
: > "$OUT/a.codes"
for p in /rag/v1/status /rag/v1/documents /rag/health /rag/v1/corpus-manifest /rag/docs /rag/openapi.json; do
  c=$(code -H 'X-OpenFerment-Project: r1' "$A$p"); echo "$p $c" >> "$OUT/a.codes"; printf '   GET %-24s %s\n' "$p" "$c"
done
printf '   GET %-24s %s\n' /rag/ "$(curl -s --noproxy '*' -o /dev/null -w '%{http_code} -> %{redirect_url}' "$A/rag/")"
curl -s --noproxy '*' -H 'X-OpenFerment-Project: r1' "$A/rag/v1/corpus-manifest" > "$OUT/a.manifest.json"
curl -s --noproxy '*' "$A/rag/health" > "$OUT/a.health.json"
echo "   /rag/health body: $(cat "$OUT/a.health.json")"
python3 - "$OUT/a.manifest.json" <<'PY'
import json, sys
m = json.load(open(sys.argv[1]))
print("-- A: the manifest, given with no key")
for k in ("stats", "embedding", "endpoints", "features"):
    print(f"   {k:10s} {json.dumps(m[k])}")
PY
python3 - "$OUT/a.manifest.json" > "$OUT/a.endpoints" <<'PY'
import json, sys
e = json.load(open(sys.argv[1]))["endpoints"]
print(e["rest"] + "/status"); print(e["mcp"] + "/"); print(e["openapi"])
PY
echo "-- A: what the manifest's own endpoints answer"
read -r REST_URL MCP_URL OAPI_URL < <(tr '\n' ' ' < "$OUT/a.endpoints")
printf '   rest    %-44s %s\n' "$REST_URL" "$(code -H 'X-OpenFerment-Project: r1' "$REST_URL")"
printf '   mcp     %-44s %s\n' "$MCP_URL" "$(code -X POST -H "$J" -H 'X-OpenFerment-Project: r1' -d '{}' "$MCP_URL")"
printf '   mcp     %-44s %s\n' "$A/rag/mcp/" "$(code -X POST -H "$J" -H 'X-OpenFerment-Project: r1' -d '{}' "$A/rag/mcp/")"
OAPI_TITLE=$(curl -s --noproxy '*' "$OAPI_URL" | python3 -c 'import json,sys; print(json.load(sys.stdin)["info"]["title"])' 2>/dev/null)
KIT_TITLE=$(curl -s --noproxy '*' "$A/rag/openapi.json" | python3 -c 'import json,sys; print(json.load(sys.stdin)["info"]["title"])' 2>/dev/null)
printf '   openapi %-44s info.title %s (the kit'"'"'s /rag/openapi.json: %s)\n' "$OAPI_URL" "$OAPI_TITLE" "$KIT_TITLE"
EMBED_VER=$(psql "$BH_SERVER/$DB_A" -XAtc "select string_agg(distinct embedding_version, ',') from sci_rag.chunks")
echo "   sci_rag.chunks embedding_version: $EMBED_VER"
echo "   the key's scopes (core/openferment_core/literature/kit.py:88): $(sed -n 88p core/openferment_core/literature/kit.py)"
bh_svc_stop "$PORT_A"

# ── B: a key set ─────────────────────────────────────────────────────────────
export OPENFERMENT_RAG_KEY="$KEY_B"
bh_svc_start "$DB_B" "$PORT_B" >/dev/null || { echo "OBSERVED: service B did not start"; echo "RESULT: NO-DEFECT"; exit 0; }
unset OPENFERMENT_RAG_KEY
echo
echo "B: service on $B over fresh $DB_B, a throwaway OPENFERMENT_RAG_KEY set; paste into r1: $(paste_one "$B")"
: > "$OUT/b.codes"
for p in /rag/v1/status /rag/v1/corpus-manifest /rag/health /rag/openapi.json; do
  n=$(code -H 'X-OpenFerment-Project: r1' "$B$p")
  w=$(code -H 'X-OpenFerment-Project: r1' -H 'Authorization: Bearer wrong' "$B$p")
  k=$(code -H 'X-OpenFerment-Project: r1' -H "Authorization: Bearer $KEY_B" "$B$p")
  echo "$p $n $w $k" >> "$OUT/b.codes"
  printf '   GET %-24s no key %s, a wrong key %s, the key %s\n' "$p" "$n" "$w" "$k"
done
B_DOCS=$(curl -s --noproxy '*' -H 'X-OpenFerment-Project: r1' "$B/rag/v1/corpus-manifest" | python3 -c 'import json,sys; print(json.load(sys.stdin)["stats"]["documents"])' 2>/dev/null)
echo "   manifest stats.documents with no key: $B_DOCS"
grep -c "$KEY_B" "$BH_WORK/svc-$PORT_B.log" | sed 's/^/   lines of service B'"'"'s log holding the key: /'

# ── the contract ─────────────────────────────────────────────────────────────
echo
echo "-- the contract"
grep -n 'so `/rag` refuses every request' docs/decisions/ADR-002-sci-rag-kit.md | cut -c1-150 | sed 's/^/   ADR-002:/'
grep -n 'the kit'"'"'s `/mcp` endpoint is left out of the mount' docs/decisions/ADR-002-sci-rag-kit.md | cut -c1-120 | sed 's/^/   ADR-002:/'
grep -n 'its REST serves under `/rag` behind `OPENFERMENT_RAG_KEY`' CLAUDE.md | cut -c1-150 | sed 's/^/   CLAUDE.md:/'
KIT=$(bh_py -c 'import sci_rag, os; print(os.path.dirname(sci_rag.__file__))')
echo "   the kit's meta router ($KIT/server/routers/meta.py):"
sed -n 3,4p "$KIT/server/routers/meta.py" | sed 's/^/     /'
sed -n 41,45p "$KIT/server/routers/meta.py" | sed 's/^/     /'
echo "   the mount (core/openferment_core/literature/kit.py:848-849):"
sed -n 848,849p core/openferment_core/literature/kit.py | sed 's/^/     /'
echo "   the provider the kit is told (core/openferment_core/literature/kit.py:213): $(sed -n 213p core/openferment_core/literature/kit.py | sed 's/^ *//')"

# ── verdict ──────────────────────────────────────────────────────────────────
python3 - "$OUT" "$EMBED_VER" "$OAPI_TITLE" "$KIT_TITLE" "$REST_URL" "$MCP_URL" "$B_DOCS" <<'PY'
import json, sys, subprocess
out, embed_ver, oapi_title, kit_title, rest_url, mcp_url, b_docs = sys.argv[1:8]
a = dict(l.split() for l in open(f"{out}/a.codes"))
b = {l.split()[0]: l.split()[1:] for l in open(f"{out}/b.codes")}
m = json.load(open(f"{out}/a.manifest.json"))
check_on = a["/rag/v1/status"] == "401" and a["/rag/v1/documents"] == "401"
open_a = [p for p in ("/rag/health", "/rag/v1/corpus-manifest", "/rag/docs", "/rag/openapi.json") if a[p] == "200"]
counts = m["stats"]["documents"] >= 1 and m["stats"]["chunks"] >= 1
open_b = [p for p, (n, w, k) in b.items() if p != "/rag/v1/status" and n == "200"]
b_key_ok = b["/rag/v1/status"][0] == "401" and b["/rag/v1/status"][2] == "200"
wrong = []
if not m["endpoints"]["rest"].endswith("/rag/v1"): wrong.append(f"rest {m['endpoints']['rest']}")
if m["endpoints"].get("mcp"): wrong.append(f"mcp {m['endpoints']['mcp']}")
if oapi_title != kit_title: wrong.append(f"openapi {m['endpoints']['openapi']} is {oapi_title!r}")
if m["embedding"]["provider"] != "fastembed" and embed_ver.startswith("fastembed"):
    wrong.append(f"embedding.provider {m['embedding']['provider']!r} beside chunks embedded by {embed_ver}")
if m["features"].get("byo_llm_key"): wrong.append("features.byo_llm_key true with no byo_llm scope on the key")
print()
print("EXPECTED: with no OPENFERMENT_RAG_KEY set every /rag request is refused (ADR-002:107-108; ready.py:248), "
      "with one set every /rag request without it is refused (CLAUDE.md:67), and a manifest /rag serves names "
      "this mount's own address (/rag/v1), no MCP endpoint (ADR-002:109) and the FastEmbed embedder its chunks carry")
print(f"OBSERVED: A (no key set): /rag/v1/status {a['/rag/v1/status']}, /rag/v1/documents {a['/rag/v1/documents']}, "
      f"and with no key {', '.join(p + ' 200' for p in open_a) or 'nothing'}; the manifest gives r1's counts "
      f"{json.dumps(m['stats'])}")
print(f"OBSERVED: B (a key set): with no key {', '.join(p + ' 200' for p in open_b) or 'nothing'} "
      f"(manifest stats.documents {b_docs}); /rag/v1/status no key {b['/rag/v1/status'][0]}, with the key {b['/rag/v1/status'][2]}")
print(f"OBSERVED: the manifest names {'; '.join(wrong) or 'only what this mount serves'}")
defect = check_on and b_key_ok and bool(open_a) and counts and bool(open_b)
print("RESULT: DEFECT" if defect else "RESULT: NO-DEFECT")
PY
exit 0
