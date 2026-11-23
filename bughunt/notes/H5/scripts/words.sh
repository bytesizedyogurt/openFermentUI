#!/usr/bin/env bash
# H5-05, H5-06, H5-07, H5-08 against a service run_all.sh left running (KEEP=1): the forecast 500, requests that
# name no project, the alpha 2.0 skill words, and the sci-rag server started in a project the database lacks.
source /home/user/openFermentUI/bughunt/lib/env.sh
O=${H5_ORIGIN:-http://127.0.0.1:8851}; NAME=bh_h5_${NAME:-fresh}
c() { curl -s --noproxy '*' -o /tmp/claude-0/-home-user-openFermentUI/cfbc5c9f-640a-5002-a705-5ceaf850fdc6/scratchpad/bh/work/H5/w.out -w '%{http_code} ' "$@"; head -c 240 /tmp/claude-0/-home-user-openFermentUI/cfbc5c9f-640a-5002-a705-5ceaf850fdc6/scratchpad/bh/work/H5/w.out; echo; }
J='content-type: application/json'
echo "H5-05 forecast of a fit the project does not hold:"
for p in bh-a bh-b; do printf "  $p: "; c -H "X-OpenFerment-Project: $p" -H "$J" -X POST $O/api/fermos/forecast -d '{"by":"bob","fitArtifactId":"0123456789abcdef"}'; done
printf "  tool door: "; c -H 'X-OpenFerment-Project: bh-a' -H "$J" -X POST "$O/api/tools/growth_forecast?by=bob" -d '{"fitArtifactId":"0123456789abcdef"}'
echo "H5-06 no project named (no header):"
for r in "GET /api/protparam?product=product-a" "GET /api/thermo/volatility?product=product-a" "GET /api/engines"; do
  set -- $r; printf "  %s %s: " "$1" "$2"; c -X "$1" "$O$2"; done
printf "  POST /api/pureos/propose: "; c -H "$J" -X POST $O/api/pureos/propose -d '{"host":"strain-a","product":"product-a"}'
printf "  POST /api/guild/check: "; c -H "$J" -X POST $O/api/guild/check -d '{"id":"e-aaaa1","personId":"p-a","skillId":"SK-A","kind":"knowledge","at":"2026-11-10T07:00:00Z","source":{"kind":"lesson","ref":"lesson-a"},"raw":"x","outcome":"pass"}'
printf "  POST /api/tools/catalogue_read: "; c -H "$J" -X POST "$O/api/tools/catalogue_read?by=bob" -d '{"kind":"strain"}'
printf "  POST /api/tools/literature_document: "; c -H "$J" -X POST "$O/api/tools/literature_document?by=bob" -d '{"document":"0123456789abcdef0123456789abcdef"}'
printf "  the same routes naming bh-a, for comparison (protparam): "; c -H 'X-OpenFerment-Project: bh-a' "$O/api/protparam?product=product-a"
printf "  GET /api/audit (a store call answered as the contract says): "; c "$O/api/audit"
echo "H5-07 Guild's skill words in a project:"
printf "  bh-b POST /api/guild/evidence: "; c -H 'X-OpenFerment-Project: bh-b' -H "$J" -X POST $O/api/guild/evidence -d '{"id":"e-bbbb1","personId":"p-b","skillId":"SK-NONE","kind":"knowledge","at":"2026-11-10T07:00:00Z","source":{"kind":"lesson","ref":"l"},"raw":"x","outcome":"pass"}'
echo "H5-08 the two MCP servers started in a project the database does not hold (bh-zzz):"
cd /home/user/openFermentUI/core && bh_env OPENFERMENT_DATABASE_URL="$BH_SERVER/$NAME" .venv/bin/python - <<'PY'
import asyncio, os, sys
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
async def one(module, tool, args):
    p = StdioServerParameters(command=sys.executable, args=["-m", module, "--project", "bh-zzz"], env=dict(os.environ),
                              cwd="/home/user/openFermentUI/core")
    async with stdio_client(p) as s, ClientSession(*s) as c:
        await c.initialize()
        r = await c.call_tool(tool, args)
        return " ".join(getattr(x, "text", "") for x in r.content)[:300].replace("\n", " ")
for m, t, a in (("openferment_core.mcp_server", "literature_sources", {}),
                ("openferment_core.literature_mcp", "list_sources", {}),
                ("openferment_core.literature_mcp", "corpus_stats", {}),
                ("openferment_core.literature_mcp", "search_entities", {"name_contains": "a"})):
    print(f"  {m.split('.')[-1]} {t}:", asyncio.run(one(m, t, a)))
PY
