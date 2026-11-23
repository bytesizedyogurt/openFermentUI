# H8-06: a deep search whose graph and HyDE stages fail names no degraded stage

**Statement.** With no model reachable, `GET /api/literature/search?profile=deep` answers profile `deep` with
`degradedStages: []`, although its graph and HyDE stages each fail on their model call (`ModelUnavailable`, logged as
`query_entity_extraction_failed` and `hyde_generation_failed`) and the kit's traces record both stages as `empty`.

**Contract.** `core/openferment_core/models.py:605-606`, generated into `docs/api/openapi.json:13180` (`SearchResponse`):
"GET /api/literature/search: the hits, best first, and the retrieval layers that timed out or failed, so a narrow
result says why." The screen reads the same field: `src/screens/BioRepoSearch.tsx:152-155` shows "Not every layer
answered (...)" only when `degradedStages` holds a stage.

**Command** (from the repository root):

    bash bughunt/repro/H8-06/run.sh

It makes a fresh database `bh_r_h8_06_deep`, starts the service keyless on 127.0.0.1:10030 (health says
`hasKey: False`, so `llm.py` refuses every model call with `ModelUnavailable` before any request leaves the machine),
makes one project, pastes one passage, asks one deep search through the route, reads the service log for the kit's
warnings, then repeats the search in process (`traces.py`, with the model client the service installs) to print the
kit's stage traces. It stops the service, drops the database and removes its data copy, and exits 0.

**Expected.** The route's `degradedStages` names `graph` and `hyde`, the two layers whose model call failed, so the
narrow result says why.

**Observed** (run1.log and run2.log, both `RESULT: DEFECT`):

    the route answers profile deep | degradedStages [] | hits 1
    the service logged, during the route call: [warning ] query_entity_extraction_failed error=ModelUnavailable
    the service logged, during the route call: [warning ] hyde_generation_failed error=ModelUnavailable
    in process, the kit's traces: {"vector": "success", "keyword": "success", "graph": "empty",
      "community": "skipped", "hyde": "empty", "rerank": "disabled"}, "degraded_stages": []

**Likely cause.** The kit's stages swallow the model failure and return an empty list:
`core/.venv/lib/python3.13/site-packages/sci_rag/retrieve/stages/graph.py:175-179` (`extract_query_entities`: on any
exception it logs `query_entity_extraction_failed` and returns `[]`) and `.../stages/hyde.py:37-41`
(`generate_hyde_passage`: logs `hyde_generation_failed` and returns `None`, so `hyde_stage` returns `[]`). The
retriever then records a stage that returned no keys as `empty` (`.../retrieve/retriever.py:365`), and
`RetrievalResult.degraded_stages` counts `timeout` and `error` alone (`.../retrieve/types.py:159-160`). openFerment
passes that list through unchecked at `core/openferment_core/api.py:2134` (`degradedStages=result.degraded_stages`),
so the response states a contract the kit's statuses cannot meet for a failed model call. The kit is Sci RAG Kit
0.5.0, installed in `core/.venv`; a fix in openFerment would read the kit's warnings or check a model before
counting graph and HyDE as answered.
