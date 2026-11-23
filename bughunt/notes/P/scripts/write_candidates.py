"""Write hunt P's candidates.json: the return value whole."""
import json
S = "bughunt/notes/P/scripts"
candidates = [
 {
  "id": "P-01",
  "title": "A route of local models alone fails with no Anthropic key: the call builds an Anthropic client first",
  "severity": "S3",
  "kind": "Contract break",
  "area": "llm.py, the local-model route (Paid row 2, fa9782e and 53c123c)",
  "statement": "llm._call builds the Anthropic client through _default_client before it looks at the route's provider, so with no ANTHROPIC_API_KEY a route naming only openai-compatible:<model> raises 'ANTHROPIC_API_KEY is not set' and the local endpoint is never asked, and the test that pays the row passes a client_factory, which hides it.",
  "contract": "CLAUDE.md:104 \"a local model behind an OpenAI-compatible endpoint `core/.env` names (`OPENFERMENT_LOCAL_BASE_URL`), which answers single calls through the kit's adapter\"; core/openferment_core/llm.py:161-166 \"a route's `openai-compatible:<model>` is called through Sci RAG Kit's adapter, its key read from core/.env too, at no charge on the day's cap. It answers a single call (`call`)\"; core/tests/test_llm.py:897-898 \"so the test holds alone, with no key in the environment, as CI runs it\"",
  "reproCommand": f"python3 {S}/stub_models.py 8951 /tmp/stub.jsonl & then bh_py {S}/row02_local.py ; bh_py {S}/row02_local.py placeholder",
  "expected": "With OPENFERMENT_LOCAL_BASE_URL set and OPENFERMENT_ROUTES naming explain as [openai-compatible:local-stub], llm.call(family='explain') is answered by the local endpoint whatever ANTHROPIC_API_KEY holds.",
  "observed": "With ANTHROPIC_API_KEY empty: ModelUnavailable 'ANTHROPIC_API_KEY is not set. Put it in core/.env (gitignored) and restart the service.' and the stub saw 0 requests. With a placeholder ANTHROPIC_API_KEY (never sent anywhere): answered by openai-compatible:local-stub, cost 0.0, one POST /v1/chat/completions at the stub.",
  "cause": "core/openferment_core/llm.py:844 `client = (client_factory or _default_client)()` runs before the loop over route.models (llm.py:862-867 checks the provider and `provider == LOCAL`); _default_client raises at llm.py:716-720 when no key is set. core/tests/test_llm.py:887-901 passes client_factory=lambda: unasked, so _default_client never runs in the test.",
  "confidence": "high",
  "fixSize": "small",
  "evidence": "Ran bughunt/notes/P/scripts/row02_local.py twice against the stub on 127.0.0.1:8951 (every proxy pointed at a dead port, ANTHROPIC_BASE_URL at a dead port): keyless it raised ModelUnavailable and the stub log stayed empty; with a placeholder key it answered from the stub at no charge. Workaround: set any value in ANTHROPIC_API_KEY."
 },
 {
  "id": "P-02",
  "title": "A review decision's provenance follows the label it carries: verified with no gold value and label gold is kept gold, and the browser reads the same decision as verified",
  "severity": "S2",
  "kind": "Contract break",
  "area": "biorepo.provenance_of, the review decision's class (Paid row 36, b9ba0d2; also import_alpha1)",
  "statement": "biorepo._is_gold reads `d.provenance == \"gold\"`, so a verified decision with no gold value is stored and served as gold when the request's label says gold and as verified when it says anything else; the browser's provenanceOf reads the same decision as verified, so Intake shows Verified and 0 in the gold set for a record BioRepo, the records table and Postdoc's evidence pool hold as gold.",
  "contract": "docs/decisions/ADR-006-quantities-and-estimates.md:137-140 \"`biorepo.provenance_of` computes the class a decision gives its record from what the decision is: `gold` for a verified decision with a gold value, `verified` for any other verified one ... `biorepo.write` stores that class whatever label the request carried\"; src/store.ts:3746-3747 \"a promoted record is gold with a gold value and verified without one\"; the Paid row \"A review decision's provenance was the label the browser sent; `biorepo.provenance_of` computes it from the decision\"",
  "reproCommand": f"bh_py {S}/row36_provenance_of.py ; on a service with a seeded project: bash {S}/row36_gold_label.sh ; node_modules/.bin/tsx {S}/row36_provenanceOf.ts ; node {S}/intake_rows.mjs",
  "expected": "A verified decision with gold null is computed verified whatever its label; the record row, biorepo_read and the Intake screen agree.",
  "observed": "provenance_of(verified, label 'gold', gold None) = gold; with labels 'verified', 'curated', 'unverified' = verified. POST /api/biorepo/decisions {status: verified, provenance: gold, gold: null} answered provenance gold; openferment.records kept provenance gold; biorepo_read served the record as gold; the overlay served {status: verified, provenance: gold, gold: null}; the browser's provenanceOf on it gives verified, and the Intake table in Chromium showed the record as Verified with '0 in the gold set'.",
  "cause": "core/openferment_core/biorepo.py:256-257 `_is_gold` returns true for `d.provenance == \"gold\"` with no gold value, and provenance_of (biorepo.py:272-280) and import_alpha1.py:176 use it; src/store.ts:3753 reads `r.gold` alone. The browser's own gold action always sends a gold value (src/store.ts:1296), so the label alone reaches the service from another caller: a script on the HTTP door or an alpha 1.0 import.",
  "confidence": "high",
  "fixSize": "small",
  "evidence": "On bh_p_main (kit demo corpus uploaded, three stand-in candidates extracted offline), row17_records.sh posted the same verified decision with labels gold then unverified: records versions 1 gold, 2 verified. row36_gold_label.sh on a third candidate: the check route ok for both labels, the decision kept gold, biorepo_read 'gold', the overlay gold label with gold null. row36_provenanceOf.ts ran the browser's provenanceOf under tsx: verified. intake_rows.mjs read the Intake table: '...da35d515 | ... | Verified | Ada Moreno'."
 },
 {
  "id": "P-03",
  "title": "Guild's review strip still names the retired identifier rule: records hidden 'on papers with no PMCID, DOI or PMID, which biorepo.write refuses'",
  "severity": "S4",
  "kind": "Drift",
  "area": "Guild review queue words (Paid row 31, 5287542)",
  "statement": "The client's paper rule is a paper the project holds (lib/review.ts paperHeld returns paper !== undefined; biorepo.write refuses a document the project does not hold), and the Guild review strip tells the reviewer the hidden records sit on papers with no PMCID, DOI or PMID, the alpha 1.0 rule the row says left; a comment in review.ts still speaks of a paper with no identifier.",
  "contract": "The Paid row: \"The client's review path kept alpha 1.0's curated-record machinery ... and its committed file's rule that a decision needs a PMCID, DOI or PMID\" (paid at 5287542); core/openferment_core/biorepo.py:26 \"paper      the record's paper is not a document the project holds\"",
  "reproCommand": "grep -n 'papers with no PMCID' src/screens/Guild.tsx; grep -n -A3 'export function paperHeld' src/lib/review.ts; grep -n 'a paper with no identifier' src/lib/review.ts",
  "expected": "The strip names the rule the code applies: records on documents the project does not hold.",
  "observed": "src/screens/Guild.tsx:627 renders '... on papers with no PMCID, DOI or PMID, which biorepo.write refuses' whenever hiddenByFilter > 0, and hiddenByFilter counts records whose paper paperHeld (src/lib/review.ts:215-217, `paper !== undefined`) does not find; src/lib/review.ts:224 says 'a paper with no identifier can still be decided here'.",
  "cause": "src/screens/Guild.tsx:621-629 and src/lib/review.ts:221-227 kept the words when the rule changed.",
  "confidence": "medium",
  "fixSize": "small",
  "evidence": "Read with grep; the strip itself was not drawn in Chromium, since no project here holds a record on a paper it does not hold."
 },
]
held = [
 "The agent builder's interface points: RECORD, auditIds, GET /api/audit by action/target/who, null fields left out, detail notes, ModuleRead, DETAIL, the recipe | dc02f20 | holds | test_agent_interface.py 13 passed; row01_audit.sh on a live service: catalogue_write through the tool door as a person and as an assistant answered auditIds [5] and [6]; ?action=&target= and ?who=probe/1 found them with detail.note and detail.via http; pb read none; gen-tools.py --check green",
 "The per-request key override and the local-model route | fa9782e, 53c123c | fails in part (P-01) | row02_key_override.sh: a service pointed at a local stub (ANTHROPIC_BASE_URL) sent the named needle as x-api-key on /api/ask and /api/ask/stream; the needle in 0 log lines (debug), 0 responses, 0 SSE events, 0 rows of both schemas; two key_override audit rows with detail {override: true}. The local route answers only with some ANTHROPIC_API_KEY set (P-01)",
 "A retrieval report over a project's own corpus, as far as it asks no model | adb9c8d, 0dd8415 | holds | seed_demo.py took the kit's demo corpus into a project and extracted three stand-in candidates; literature_live graph --dry-run: 34 chunks, 5 batches, 0 calls; report --configs interactive,vector_only,keyword_only: 3 questions, both relevance rules, spent.calls 0, exit 0; without --configs the run stops at full_deep in words, exit 1, as documented; tests 34 passed",
 "The kit's search_entities and get_entity_relationships read the project's graph alone | 19d129a | holds | row04_graph_scope.py wrote a graph into the kit's tables for two projects and asked the sci-rag server over stdio in each: pa saw rice straw and Colusa with pa's descriptions, pb saw zyxwort moss and quillstone ponds; each project's relationships lookup of the other's entity answered found false; /rag serves no graph route (its paths: /health, /v1/status, /v1/corpus-manifest, /v1/query, /v1/answer, /v1/documents)",
 "The catalogues are project stores; the catalogues screen; the store reads catalogues; protocols store with step skills held to the skill catalogue; lessons with bodies | a0c33bb, 50a4f96, 61c4e3f, 37addaf, c18c0e7 | holds | row05_catalogues.sh: a skill kept in pa is absent from pb (404); a protocol naming pa's skill refused in pb in words and kept in pa; a strain file through /api/intake/catalogue kept in pb; catalogue_read per project; screens_paid.mjs in Chromium: a strain kept on /catalogues as Ada Moreno (person), geneOS Hosts showing both pb strains and none in pa, the protocol editor's picker naming pa's skills; tests 117 passed",
 "competence.ts reads a skill kept with no policy as unrated | c18c0e7 | holds | export-competence-fixtures.ts run into scratch: competence.json and competence-unrated.json byte for byte; check:guild green; the skill's Guild page in Chromium says the entry holds no policy so Guild rates nobody on it",
 "The protocols page begins a protocol, its editor adds skills as 1.1 | 3b40de6 | holds | screens_paid.mjs: begun on /runbooks/protocols, the editor opened at its address, a skill chip pressed, kept: versions 1.0 and 1.1 by Ada Moreno, step s1 needing SK-P5",
 "stream_table on a scenario's kept run has its test again | 32b95f1 | holds | test_tools.py stream tests passed; stream_table on a kept cornstover run answered 45 rows in pa and refused in pb",
 "The module reads list depositions and readings; PARTIAL holds no runbooks line | fd17f32 | holds | row09_state.sh: runbooks_read in pa listed the runbook, the protocols, deposition dep-p9 and reading dep-p9/de-p9 with partial null; pb listed nothing; PARTIAL holds biorepo alone",
 "Proforma reads every scenario as the project's; GET /api/proforma/scenarios lists a broken custom_train_v1 scenario with words | f5405f8 | holds | row10_proforma_scenarios.sh: two composites with missing parts listed with their refusals in words, HTTP 200; a shelf scenario bound with 6 inputs; pb lists none; createdScenarioIds and needsBinding appear nowhere under src/",
 "The geneOS enumeration module and RunbookDetail's research funnel are deleted | e90deeb | holds | src/engine/geneos is gone; no 'enumeration' or 'clearance reading' under src/",
 "src/data/types.ts deleted; the screens read the generated types | a471f92 to 8281f5e | holds | the file is gone and nothing imports data/types; gen-api.py --check green; tsc --noEmit exit 0",
 "Readers of Override.origin, Runbook.note and Runbook.progressPct read a field left out | a471f92, ec90d5a | holds | check:state green (a change kept with no origin is sent as a person's assumption); the runbook page of a runbook kept with no note and no progress says it keeps no note and shows 0% in Chromium with 0 console errors",
 "store.adoptRunbookDraft takes the generated RunbookDraft with no assertion | ec90d5a | holds | check:state: a draft's predictions and measures enter as the service wrote them, each null and field left out kept",
 "A promoted or superseded runbook takes a timeId and joins the rows the page sends | ec90d5a | holds | check:state: the runbooks adopted, revised and promoted are among the rows sent under ids that hold across reloads (rb-<time>-<n>); the revision keeps the locked values and the original keeps its lock",
 "The project state's three routes answer models | c34c8c9 | holds | row09_state.sh: PUT answered a StateKept, GET a ProjectState with every key, DELETE a StateTakenBack; a deposition DELETE refused in words; a deposition write leaving out or changing a kept reading refused in words; test_route_models and test_project_state passed",
 "openferment.records is written by each decision and an undo | ae603d3 | holds | row17_records.sh: a decision then a second then an undo wrote versions 1, 2 and 3 of the row, the undo's status unverified, and biorepo_read moved the record back to the candidates",
 "fermOS's, pureOS's and Proforma's run requests take typed quantities; runs are rows of kinetics, train and biosteam | 0ad02c9, a4a739f, 17c5197 | holds | row18_kinetics_run.py: POST /api/engines/kinetics/run with person-assumption inputs and ks set to a reading: engine kinetics, each origin kept, the reading converted with its note; ?inputs= on /api/proforma/bind and /ceiling-check took typed quantities; a cornstover biosteam run kept as engine biosteam",
 "The train engine's rests_on names the project's depositions, and the completeness test fails without them | fd17f32 | holds | a pytest plugin (plugins/bh_drop_depositions.py) dropped depositions from rests_on and the completeness test failed on the missing key; unpatched it passed",
 "pureOS reads a library run as a train | 744e32e | holds | GET /api/pureos/train/<cornstover run> answered the train with 68 units and the stream table in pa, 404 in words in pb; the train page in Chromium drew it",
 "Studies' run card titles a kinetics configuration | 09e95dd | holds | GET /api/engines after a kinetics run: thing vessel with configuration titled 'a batch_v1 simulation, kept 2026-11-10 22:49 UTC'; pb has no vessel thing; check:state's configuration lines green",
 "The screens' words put a project's rows with the service | b70fa83 | holds | check:state read 19359 sentences green; Postdoc's empty list in Chromium: 'The service keeps each conversation with the project, so it is listed here after a reload'",
 "The shelf's hand-written reference entries retired; kept runs replay through kept_references.py | f5405f8 | holds | /api/proforma/shelf lists ethanol_glucose_v0 and custom_train_v1 alone; the library holds cornstover and corn; test_workers and test_proforma kept-reference tests passed (the sim replay was not run)",
 "Small handler mismatches the worker op reference found | 0c49630 | holds | grid and montecarlo take structure (proforma_worker.py:216, 258); the worker tests named for them passed",
 "Proforma's panel takes a reading in its own value and unit | 7e178bb | holds | row25_proforma_reading.sh: bind with titre set to reading dep-p9/de-p9 in g/L bound it as a fixed 1.5 g L-1 with the note '1.5 g/L as deposited, 1.5 g L-1 in the parameter's unit'; the same reading sent in mg/mL and in another project refused in words; check:state's panel lines green",
 "A review decision's provenance is computed by biorepo.provenance_of | b9ba0d2 | fails (P-02) | a verified decision with no gold value is kept gold when its label says gold and verified otherwise; the browser reads it verified",
 "The evidence pool applies the standing decisions | b9ba0d2 | holds | biorepo_read and search_records list a decided candidate as a record with its computed class and an undone one as a candidate unverified",
 "Dead service paths the deletions left | e738506 | holds | no ProjectionMissing, _example, check:seed entry point or yield cap under core/openferment_core, scripts or package.json (proforma._check_seed is the Monte Carlo seed check)",
 "nav.ts exports DESTINATIONS | 74d5e66 | holds | src/data/nav.ts:254 exports DESTINATIONS, no ELEVEN or THE TWELVE; the rail in Chromium lists Home to Catalogues",
 "selling_price, run_flowsheet, the params scope and pureOS's naming read the project's scenarios | 5287542 | holds | selling_price in pa read a kept scenario's refusal by its own inputs and the cornstover run's price 0.658813642 USD/kg; in pb both refused as no scenario or run of that project",
 "The client's review path lost alpha 1.0's curated-record machinery and its PMCID rule | 5287542 | holds in code, words drift (P-03) | lib/review.ts paperHeld is `paper !== undefined`; Guild's strip and a review.ts comment still name the identifier rule",
 "pnpm smoke checked nothing more; the walk goes through a project on the real service | b00721f | holds by reading | scripts/walk.ts drives Home, ingest, search, catalogues, protocols, hosts, a conversation, a runbook, the bench, a measured scenario and each engine; not run here, since smoke and prove choose their own ports and database names outside the hunt's",
 "Both MCP servers connect at a session's start and answer over stdio | 2d488fb, 85c7a26 | holds when measured, suspected at a cold start | row34_mcp_connect.py started each by .mcp.json's exact command: initialize and tools/list in 2.2 to 2.4 s, 50 and 8 tools; this session's own start reported both CONNECT_TIMEOUT after 30000 ms (see suspected)",
 "Open and Left by decision tables, read against the tree | n/a | none worse than stated | duration_h reaches no route or schema; units.json maps wt% and % (w/w) to % CDW as said; a deposition write that drops or changes a kept reading is refused; a reading's by is the deposition's maker, as studies.md:79 says; import_alpha1 reads core/data/biorepo.json by default when run, which the last row's 'a tracked file nothing reads' passes over",
]
suspected = [
 {"title": "The MCP servers can miss Claude Code's 30 s connect window at a session's start",
  "tried": "This session's start reported openferment and sci-rag CONNECT_TIMEOUT after 30000 ms. Started by .mcp.json's exact command (uv run --project core --all-extras python -m ...), warm, each answered initialize and tools/list in 2.2 to 2.4 s over two rounds; uv sync --dry-run said it would make no changes. A cold start under the load of many hunts starting at once is the likely cause; not reproduced."},
 {"title": "A reading appended to another person's deposition is credited to the deposition's first keeper",
  "tried": "A PUT of dep-p9 by Grace Hopper adding reading de-p9b was kept, and /api/depositions/readings names its by as Ada Moreno, the row's maker. docs/api/studies.md:79 defines a reading's by as the deposition row's maker, so this follows the contract; whether a second person may write another person's deposition at all is not settled in the pages read."},
]
needs_live = [
 "The key override against the real Anthropic API: a rejected named key said to be the request's in words (tested here with a local stub that accepted any key)",
 "The retrieval lanes that ask a model (full_deep, no_graph, no_hyde, the judge) and a real graph build; here they stop in words with no key",
]
unexamined = [
 {"item": "pnpm smoke and the walk (proof step 9) run whole", "reason": "smoke takes a free port and a database name of its own, outside 8950-8959 and bh_*; the walk needs the proof's filled project"},
 {"item": "kept_references.py replays of a kept benchmark run (test:sim)", "reason": "a sim suite; the offline tests named for it passed"},
 {"item": "Home's awaiting-review count for an accepted candidate (row 37's screen half)", "reason": "read through biorepo_read and the Intake table; Home's tile not opened"},
]
out = {"candidates": candidates, "suspected": suspected, "needsLiveModel": needs_live, "held": held, "unexamined": unexamined}
open("/home/user/openFermentUI/bughunt/notes/P/candidates.json", "w").write(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
print(len(candidates), len(held))
