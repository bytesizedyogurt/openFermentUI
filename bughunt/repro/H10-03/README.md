# H10-03 (with H8-09): /rag answers four doors with no key, and its manifest misnames the mount

**Statement.** With `OPENFERMENT_RAG_KEY` unset, `/rag/health`, `/rag/v1/corpus-manifest`,
`/rag/docs` and `/rag/openapi.json` answer 200 with no key, the manifest giving the project's
document and chunk counts that `/rag/v1/status` refuses with 401; with a key set, the manifest,
health and OpenAPI doors still answer 200 to a request with no key or a wrong one; and the manifest
names a REST address at `/v1`, an MCP endpoint at `/mcp`, an OpenAPI document at `/openapi.json`
(openFerment's own), the embedder provider `local-hash` and `byo_llm_key: true`, none of which this
mount serves.

**Contract.**
- `docs/decisions/ADR-002-sci-rag-kit.md:107-108`: "with none set a key made in memory and never
  shown stands in, so `/rag` refuses every request".
- `docs/decisions/ADR-002-sci-rag-kit.md:109`: "the kit's `/mcp` endpoint is left out of the mount".
- `core/openferment_core/ready.py:248`: "/rag refuses every request: no {kit.RAG_KEY} in core/.env".
- `CLAUDE.md:67`: "a local FastEmbed embedder; its REST serves under `/rag` behind `OPENFERMENT_RAG_KEY`".

**Command.** `bash bughunt/repro/H10-03/run.sh` from the repository root. It makes two fresh
databases (`bh_r_h10_03_nokey`, `bh_r_h10_03_key`), starts a keyless service on 127.0.0.1:9170 with
`OPENFERMENT_RAG_KEY` empty and one on 127.0.0.1:9171 with a throwaway key, makes project `r1` in
each and pastes one placeholder note, asks each door with no key, then stops both services and drops
both databases. About 17 seconds, no model call.

**Expected.** With no key set, every `/rag` request is refused; with a key set, every `/rag`
request that lacks it is refused; a manifest `/rag` serves names this mount's own address
(`/rag/v1`), no MCP endpoint, and the FastEmbed embedder its chunks were embedded by.

**Observed** (run1.log and run2.log alike):
- No key set: `/rag/v1/status` 401 and `/rag/v1/documents` 401, while `/rag/health` 200,
  `/rag/v1/corpus-manifest` 200 with `r1`'s stats `{"documents": 1, "chunks": 1, "entities": 0,
  "communities": 0}`, `/rag/docs` 200, `/rag/openapi.json` 200; `/rag/` redirects 307 to
  openFerment's own `/docs`.
- A key set: `/rag/v1/status` 401 with no key or a wrong key and 200 with the key, while
  `/rag/v1/corpus-manifest`, `/rag/health` and `/rag/openapi.json` answer 200 with no key and with
  a wrong key; the manifest again gives `documents: 1`. The key appears in no line of the log.
- The manifest's `endpoints`: `rest` `http://127.0.0.1:9170/v1` (`/v1/status` there answers 404),
  `mcp` `http://127.0.0.1:9170/mcp` (no MCP server there; `/rag/mcp/` answers 404, as ADR-002
  says), `openapi` `http://127.0.0.1:9170/openapi.json` (info.title `openferment-core`, where the
  kit's own document at `/rag/openapi.json` is titled "openFerment bioprocess literature").
- `embedding.provider` reads `local-hash` while every row of `sci_rag.chunks` carries
  `embedding_version` `fastembed:BAAI/bge-small-en-v1.5@384`; `features.byo_llm_key` reads true
  while the key's scopes (`kit.py:88`) leave `byo_llm` out.

**Likely cause** (high confidence).
- `core/openferment_core/literature/kit.py:848-849` mounts the kit's `create_app` whole and takes
  out the `/mcp` mount alone. The kit's `sci_rag/server/routers/meta.py:21` (`/health`) and `:41`
  (`/v1/corpus-manifest`, "deliberately unauthenticated", lines 3-6) carry no `require_scopes`, and
  FastAPI's `/docs` and `/openapi.json` carry none either, so the key map from `kit.py:188-193` never
  reaches them, whether the key is set or made in memory.
- The manifest's endpoints come from `request.base_url` (`meta.py:44`), which Starlette builds from
  the top-level app's root path and so leaves `/rag` out; `sci_rag/server/service.py:331-340` writes
  `/mcp` and `byo_llm_key: True` as constants; `embedding.provider` reads the settings value
  `kit.py:213` sets to `local-hash`, while the embedder in use is FastEmbed (`kit.py:230`).
- `core/tests/test_literature_kit.py:235-242` (`test_rag_with_no_key_set_accepts_none`) asks
  `/rag/v1/query` alone, so the open doors pass it.

**Severity.** S4: a contract the ADR, `pnpm ready` and CLAUDE.md state does not hold, and the
manifest misdescribes the mount. What the open doors give (one project's counts, the kit's version,
whether the database answers, the kit's route list) holds no document content, and a loopback client
reads the same counts keyless at `/api/literature/stats`.
