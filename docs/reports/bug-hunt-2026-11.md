# Bug hunt on alpha 2.2, November 2026

**Commit hunted: `2047f5a7e9f6eedb0fe33649bad97c1b757b7bb7`**, the head of `claude/alpha-2-2-base` on 8 November 2026
(pull request #17 to `main` was open and unmerged throughout, so the base branch stood). The hunt ran from
10 to 11 November 2026 on the branch `claude/alpha-2-2-bughunt`, keyless and with no model call, on test databases
alone. Nothing under `core/`, `src/`, `scripts/` or `examples/` changed. Everything the hunt made is under `bughunt/`
and in this report.

## Owner's summary

**What was done.** Seventeen independent readers went through alpha 2.2 cold: fourteen hunts, one for each area the
brief names, a retest of every paid debt, and two readers of the records (PROGRESS.md, the 66 commit messages, the
handoff report). Between them they raised 149 candidate defects, eight of them duplicates. Every one of the 141 left
got a reproduction script in `bughunt/repro/<id>/`, run twice from a clean database, and then a fresh agent who saw
only the reproduction and the contract and was told to refute it. A candidate that agent set aside went to a second
fresh agent who judged it by the brief's own definition of each kind of defect. **92 defects survived. 49 did not**
and are listed under Suspected with what was tried.

| Severity | Count | What it means |
|---|---|---|
| S1 | 15 | a wrong number or provenance label shown as sound, lost or corrupted data, or one project reading another's |
| S2 | 2 | a main-path feature broken |
| S3 | 51 | an edge case fails, with a workaround |
| S4 | 24 | wording, cosmetic faults, drift |
| **All** | **92** | |

**What is broken, in everyday words.**

- **One project can read another's private text.** While project A is taking in a document, a literature search in
  project B can return A's private passage (H5-01). Every other door held this line under attack.
- **Two browser tabs can lose a person's work.** A reading recorded at the bench in one tab while the service was
  away is erased when a second tab saves (H7-01), and two tabs on one scenario's panel overwrite each other's
  settings with no warning (H7-04).
- **Numbers from papers can be stored under the wrong unit and called verified.** Anchoring accepts a number whose
  unit cannot convert to the field's (a price in dollars per gallon filed as dollars per kilogram, a percentage by
  volume filed as grams per litre) and BioRepo then keeps it as verified or gold (H3-01). Grams per gallon reads as
  grams per gram (H3-08). Letter case is folded, so megagrams read as milligrams (H3-07, S3).
- **Some computed figures are wrong and look sound.** A comparison puts two runs' values in different units on
  one row and reports a change of about +99,900 per cent between equal titres (H2-01). A scenario flowsheet keeps a
  base price that its own fixed samples contradict (H1-04). One cost card closes on a price per kilogram of stream
  under a label of per kilogram of product (H4-02). The concept graph's dry run prices the build at five times its
  cost (R1-03).
- **Records can carry a label they have not earned.** A review decision marked gold with no gold value is stored as
  gold (P-02, a debt the records list as paid). The alpha 1.0 import carries a model's estimate into the gold set
  (H6-02). The state door lets one kind of row overwrite another, so a study scenario or a model's kept train can be
  replaced and keep its first maker's name (H5-03).
- **Text can be altered on its way in.** A Latin-1 XML upload loses its micro and degree signs (H8-04), and a paste
  that differs from a held document in letter case alone is linked to the held text, so "2000 mg" reads as
  "2000 Mg" (H8-01).
- **Main-path breaks.** A kept strain's aliases never match a paper's organism, so strain pages count no records
  (H14-02), and the literature answer spends the service's own key when a request names its own (H9-01).
- **Tests that pass with the code broken.** Twelve hollow tests, among them the no-seed guard (passes with a titre and
  a price typed into the code), five conformance checks, the spend cap's lock, and the guard's check on a forwarded
  host.

**What held up under attack.**

- **Project isolation:** 133 operations from project B with A's ids, through every door (REST, tools, both MCP
  servers, the event stream, the graph reads). Nothing of A was read or changed apart from H5-01's race.
- **Keys:** no key reached a log, a response, a database row, the bundle or a commit. A sentinel key was searched for
  everywhere and found only in the model requests it was meant for, with one route using the wrong key (H9-01).
- **The guard and the loopback bind:** forged origins, hosts and cross-site writes from a browser were refused.
- **Path traversal and SQL:** no traversal, no SQL built from strings, and no stack trace or file path in a REST error body. At the tool door a NUL character in an id echoes the driver's SQL text (Suspected, H9-14).
- **The URL import:** it refused every loopback, private and redirect trick tried.
- **Units:** every conversion the unit table allows round-trips within 1e-12.
- **Provenance:** labels matched a hand-worked table of 21 mixes.
- **The record stores:** each refuses a model's estimate.
- **Independent numbers:** cornstover, corn and the composed flowsheet match the package run directly, number for
  number. The kinetics families close their mass balances on hand-solved cases, and train runs conserve mass at every
  unit.
- **Migrations:** run from empty, run twice, down and up, and from alpha 2.1 with every row reading back. Two
  exceptions sit under Suspected: products alpha 2.1 kept with a category the head does not accept (H6-01), and alpha 2.1's
  Proforma runs, which replay one unit in the last place apart.
- **Paid debts:** 30 of the 33 paid rows hold. One fails (the gold rule, P-02), one fails in part (the key
  override on one route and the local-model route, H9-01 and P-01), and one holds in code with its old words left on
  a screen (P-03).
- **The baseline:** every suite, the build, the proof and verify reproduced the recorded counts.

**What was left unexamined, and why.**

- **A live model.** The account refuses calls until 1 December 2026, so every path that asks a model was run to its
  keyless refusal and listed under "Needs a live model" (36 checks).
- **macOS.** The host scripts were read against macOS and run on Linux stand-ins. None ran on a Mac.
- **Docker.** `pnpm db:up` needs a Docker daemon this container lacks.
- **The ledger.** Of the 718 rows (files, operations, tools, rail entries, screens, engines), 716 were examined. The two left are
  files alpha 2.2 deleted.

**Where to start.** The fix order at the end groups the 92 findings by shared cause. The first groups close every S1:
- the search narrowing that lets a race through;
- the browser's one shared snapshot and whole-scope writes;
- the anchoring rule that compares bare numbers across units;
- the state door that accepts any kind's id;
- the gold rule that reads a label.

Ten of the fifteen S1 fixes are small, and five are medium.

## Baseline

Stage 0 ran on 10 November 2026 from 21:01 to 21:25 UTC at `2047f5a`, keyless: `core/.env` held no key line, the
session's model pins were unset, and the proof's spend table and the service's both read 0 calls. `node_modules` and
`core/.venv` were removed, `pnpm install --frozen-lockfile` ran, the virtual environment was
built from the lock by `pnpm db:migrate`'s `uv run --frozen --all-extras` (a later `uv sync --frozen --all-extras`
answered "Checked 169 packages", a no-op), and the suites ran one after the other on PostgreSQL 16.15 with pgvector,
Python 3.13.17. The logs are kept in the hunt's scratch folder and summarised here.

| Suite | Recorded (Last green runs) | Stage 0 | Same? |
|---|---|---|---|
| `pnpm test:core` | 3060 passed, 1 skipped, 175 deselected, 5 min 12 s (close review, stage H) | 3060 passed, 1 skipped, 175 deselected, 4 min 51 s (4 min 19 s inside verify) | yes |
| `pnpm test:sim` | 142 passed, 3091 deselected, 4 min 56 s (stage H verify, `9b6e5c7`) | 142 passed, 3094 deselected, 4 min 58 s (4 min 12 s inside verify) | yes: the three more deselected are the three `test_host.py` tests the close review added after that row, as 3060 + 1 + 175 = 142 + 3094 |
| `pnpm test:lit` | 10 passed, 10 s | 10 passed, 7 s | yes |
| `pnpm build` | built (4.7 s in the bundler) | built, 1751 modules, 5.5 s in the bundler (4.0 s inside verify) | yes |
| `pnpm prove` offline, steps 1 to 10 | 99 of 99 checks, 0 calls, 203 s | 99 of 99 checks, 0 calls, 168 s | yes |
| `pnpm verify`, sixteen stages | every stage green, 12 min 11 s; `check:guild` 146, `check:state` 95, `check:figures` 13, `smoke` 20 of 20 | every stage green, 10 min 11 s; `check:guild` 146, `check:state` 95, `check:figures` 13, `smoke` 20 of 20 with no key | yes |

Stage 0 found no difference from the record, so it gives no finding. One step of the stage's own script failed
(`uv sync` under `env -u`, which cannot run the shell's `cd`). The lock was installed by the next step and checked
after, as above.

### Verify and the bughunt folder

The brief asks for any verify stage that objects to the `bughunt/` folder to be logged here. `pnpm check:secrets`,
verify's first stage, objected three times to files the hunt wrote:

- a fuzz script holding two made-up database addresses with a password (`bughunt/notes/H11/scripts/env_setting_fuzz.py`);
- two reproductions that write a made-up key line, `sk-ant-` followed by a placeholder of the hunt's own
  (`bughunt/repro/H13-01/run.sh`, and `bughunt/repro/H11-08/run.sh` with its two logs).

The H11-08 files reached commit `d1cb6df`. The commit step piped the check's output through `tail`, whose exit status let the commit go ahead.
From then on the commit script stops on the check's exit status. The string committed was a
23-character placeholder, `sk-ant-` followed by `H11-08-NOT-A-KEY`. The real key is 106 characters long, and a search of every
commit on the branch, the working tree and the hunt's scratch files found it nowhere.

Each value is now joined at run time and each log masked, and the check passes on the tree. `check:secrets` reads
every tracked file, so moving the folder under `docs/reports/` would carry each objection with it. The folder stays
at `bughunt/`. The objections were the check doing its work on the hunt's own files.

A full `pnpm verify` ran keyless on `9bcfd4b`, the branch with every hunt file committed, on 11 November 2026 from
01:26 to 01:39 UTC (13 min 25 s). All sixteen stages passed:

- `check:secrets` found no secret;
- `test:core` gave 3060 passed, 1 skipped and 175 deselected;
- `test:sim` gave 142 passed, and `test:lit` 10 passed;
- `smoke` opened all 20 screens with no model key;
- `test:reconcile` reconciled the three kinds.

No stage objected to the `bughunt/` folder as it stands.

## Findings

Each finding below went through the same steps, and its entry says which of them it stood on.

1. **A hunt raised it.** The hunt was a fresh agent that read its area's contract pages and code with the PROGRESS
   log withheld, and proved the candidate by running something. Its notes and scripts are in
   `bughunt/notes/<hunt>/`.
2. **A reproduction was built and run twice.** A second agent wrote `bughunt/repro/<id>/run.sh`, which makes its own
   test database and prints `EXPECTED`, `OBSERVED` and `RESULT`. It ran the script twice from a clean database and kept
   both logs beside it.
3. **A first refutation.** A third agent, given the reproduction and the contract text alone, ran it again and tried
   to refute it, defaulting to refuted when unsure. It judged each candidate against the written contract.
4. **A second refutation, for candidates the first set aside.** The first pass read the written text so closely that
   it also set aside defects the brief defines without a written promise: a wrong number, a broken use, a hollow
   test, two doors answering differently. A fourth agent judged each set-aside candidate against the brief's own
   definition of its kind, still defaulting to refuted. Of 74 candidates, 25 stood on this second reading; their
   entries say so in "Stood on".
5. **Severity by three readings.** The level shown is the one at least two of three readings gave. The entry's writer
   applied the brief's scale to the refuter's reading. An independent panel judged every finding cold from the
   entry, the reproduction and the scale. Where the three readings differ, the entry's "Severity" line gives the
   dissenting reading.

Each entry gives the contract it breaks (file and line, quoted), the one command that reproduces it, the expected and
observed results, the likely cause with a confidence, and the size of the fix. Line numbers are 2047f5a's, and each was
checked against the tree when the entry was written.

### Paid debts that still reproduce

Each of these four is a claim the Paid table makes, and each reproduced. They stand first, as the brief asks; their levels follow the scale like every other finding.

#### P-02 · S1 · Contract break · BioRepo review decisions: `biorepo.provenance_of` and the browser's `provenanceOf`

`biorepo.provenance_of` computes a verified decision with no gold value as `gold` when the request's label says gold, so the records table and `biorepo_read` keep and serve that record as gold. The browser's `provenanceOf` and the Intake screen show the same record as Verified.

- **Contract:** `docs/decisions/ADR-006-quantities-and-estimates.md:137-140`, "`biorepo.provenance_of` computes the class a decision gives its record from what the decision is: `gold` for a verified decision with a gold value, `verified` for any other verified one" and "`biorepo.write` stores that class whatever label the request carried"; and `docs/decisions/ADR-006-quantities-and-estimates.md:145`, "The browser's `provenanceOf` reads a decided record by the same rule".
- **Reproduce:** `bash bughunt/repro/P-02/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** A verified decision with no gold value is `verified` whatever label it carries. The POST's answer, the `openferment.records` row, `biorepo_read`, the browser's `provenanceOf` and the Intake screen all say verified.
- **Observed:** `provenance_of(verified, label 'gold', gold None)` gave `gold`. The labels `verified`, `curated` and `unverified` each gave `verified`. `POST /api/biorepo/decisions` with label gold and gold null answered 200 `{'status': 'verified', 'provenance': 'gold', 'gold': None}`, the records row read `1|verified|gold|null`, `biorepo_read` listed the record with provenance `gold`, and the overlay served the decision with provenance `gold` and gold `None`. The browser's `provenanceOf` on that decision gave `verified` with a gold-set count of 0, and Intake in Chromium showed the row as `Verified` and "0 in the gold set".
- **Likely cause:** `core/openferment_core/biorepo.py:256-257`: `_is_gold` returns `d.provenance == "gold" or d.gold is not None`, so the label alone makes a decision gold; `provenance_of` returns that class for a verified decision (`biorepo.py:279`), `write` stores it (`biorepo.py:340`), `evidence_pool.py:97` and `import_alpha1.py:176` compute their classes with it, and the browser's `provenanceOf` reads `r.gold` alone (`src/store.ts:3753`). (confidence: high)
- **Fix size:** small: `_is_gold` in `biorepo.py` reads the gold value alone (its uses at lines 279, 321, 367 and 411 follow), and the tests that build a gold record from the label change with it (`core/tests/test_agent_interface.py:53`, `core/tests/test_biorepo.py:458` and `:469`).
- **Severity:** S1, the reading of the entry's writer and of an independent severity panel (the scale's words: a wrong provenance label shown as sound). The refuting agent read S3.
- **Stood on:** the first refutation.

#### H9-01 · S2 · Contract break · the per-request key override (owner question 10), the kit's cited answer

`POST /api/literature/answer` sent with `X-OpenFerment-Key` makes its model call on the service environment's key (core/.env's). The request's audit row records `{"override": true}`.

- **Contract:** `CLAUDE.md:116`, "a key sent on a request serves that request's model calls, openFerment's and the kit's"; and `docs/api/postdoc.md:226-228`, "every model call it makes, Postdoc's, extraction's and the kit's, runs on that key".
- **Reproduce:** `bash bughunt/repro/H9-01/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** Every model request the route makes carries the key the request named (`x-api-key` = SENTINEL at the loopback stand-in), as the kit's answer through `POST /rag/v1/answer` does, and the audit row's override then describes the call.
- **Observed:** In both runs `POST /api/literature/answer` sent 1 model request carrying ENVKEY, the key the service's environment held. `POST /rag/v1/answer` in the same service sent 3 carrying SENTINEL. `GET /api/audit?action=key_override` held `{"target": "POST /api/literature/answer", "detail": {"override": true}}`. Inside `llm.request_key`, `key_named()` read False in a `threading.Thread`. In `asyncio.to_thread`, inside the same `llm.request_key`, it read True. The service log held 0 lines with the request's key.
- **Likely cause:** `core/openferment_core/literature/kit.py:825` starts `threading.Thread(target=lambda: db.run(pump()), name="kit-answer", daemon=True)`, a thread that begins with an empty context (`core/openferment_core/llm.py:769-771` says so), so `llm._REQUEST_KEY` is None inside `pump` and `_default_client` (`core/openferment_core/llm.py:715-716`) builds the client on `os.environ.get("ANTHROPIC_API_KEY")`. The ask stream's thread at `core/openferment_core/api.py:614` runs on `contextvars.copy_context().run` and carries the key. (confidence: high)
- **Fix size:** small: start the kit-answer thread at `kit.py:825` on `contextvars.copy_context().run`, as `api.py:614` does, with a test that sends the header to `/api/literature/answer`.
- **Stood on:** the first refutation.

#### P-01 · S3 · Contract break · llm._call, the local-model route

`llm._call` builds the Anthropic client through `_default_client` before it reads any model's provider, so with `ANTHROPIC_API_KEY` empty a route whose one model is `openai-compatible:<model>` raises "ANTHROPIC_API_KEY is not set" and the local endpoint receives no request.

- **Contract:** `docs/decisions/ADR-008-postdoc-memory-routing.md:187-190` (Implementation 11), "`OPENFERMENT_LOCAL_BASE_URL` names the endpoint and `OPENFERMENT_LOCAL_API_KEY` its key (many local servers take any); a route's `openai-compatible:<model>` is then served (`llm.served_providers`). `llm.call` asks it through Sci RAG Kit's `OpenAICompatLLM`"; and `core/openferment_core/llm.py:162-164`, "a route's `openai-compatible:<model>` is called through Sci RAG Kit's adapter, its key read from core/.env too, at no charge on the day's cap. It answers a single call (`call`)".
- **Reproduce:** `bash bughunt/repro/P-01/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** With `OPENFERMENT_LOCAL_BASE_URL` naming a local endpoint and the `explain` route set to the one model `openai-compatible:local-stub`, `llm.call(family="explain")` is answered by the local endpoint at no charge, whatever `ANTHROPIC_API_KEY` holds.
- **Observed:** With `ANTHROPIC_API_KEY` empty, both runs printed "RAISED ModelUnavailable: ANTHROPIC_API_KEY is not set. Put it in core/.env (gitignored) and restart the service.", and the stub saw 0 POST /v1/chat/completions. With a placeholder key the same call printed "ANSWERED openai-compatible:local-stub cost=0.0 tried=['openai-compatible:local-stub']", and the stub saw 1 POST /v1/chat/completions and 0 POST /v1/messages. `served_providers()` read `('anthropic', 'openai-compatible')` in both arms.
- **Likely cause:** `core/openferment_core/llm.py:844` runs `client = (client_factory or _default_client)()` ahead of the loop that reads each model's provider (:861) and takes the local branch (:867), and `_default_client` (:715-720) raises ModelUnavailable when no key is set; the service's extract path (`core/openferment_core/extract.py:328`) calls `llm.call` with no `client_factory`, and `core/tests/test_llm.py:900` passes `client_factory=lambda: unasked`, so the suite never runs `_default_client` on this path. (confidence: high)
- **Fix size:** small: build the Anthropic client lazily in `llm._call`, at the first Anthropic model the loop reaches, and add a keyless test that passes no `client_factory`.
- **Stood on:** the first refutation.

#### P-03 · S4 · Drift · Guild review queue: the strip under "Papers the service can keep"

Guild's review strip tells the reviewer that the records it hides sit "on papers with no PMCID, DOI or PMID, which `biorepo.write` refuses". The filter it describes hides records on documents the project does not hold (`paperHeld`), `biorepo.write` keeps a decision on a held document with no identifier, and two comments in `src/lib/review.ts` describe the `paper` refusal by the same retired rule.

- **Contract:** `core/openferment_core/biorepo.py:26-27`, "paper      the record's paper is not a document the project holds — a decision stands on a text a reader can look up (§7.4)"; and `docs/PROGRESS.md:1210-1212`, the stage 8.5 log behind the Paid row at `docs/PROGRESS.md:601`, "`biorepo.write` keeps a decision on any document the project holds (an upload, an OSTI report, an SGD entry). The rule is the service's now (`paperHeld`)."
- **Reproduce:** `bash bughunt/repro/P-03/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** The strip names the rule the filter applies and `biorepo.write` refuses under: the hidden records sit on documents the project does not hold. The two comments in `src/lib/review.ts` name the same rule.
- **Observed:** In both runs `src/screens/Guild.tsx:627-628` read `on papers with no PMCID, DOI or PMID, which{' '}` and `<code className="font-mono">biorepo.write</code> refuses`, `paperHeld` at `src/lib/review.ts:215-217` read `return paper !== undefined;` with 0 lines naming an identifier, and `src/lib/review.ts:224` and `:310` read "a paper with no identifier can still be decided here" and "A paper with no identifier is still reviewable here". On the live service the project held 2 uploads with `doi=None pmcid=None`, and `POST /api/biorepo/decisions` kept a verified decision on one of them with HTTP 200 (`"status":"verified","provenance":"verified"`). Guild's filter, run with the tree's `paperHeld`, gave `hiddenByFilter=1`: it showed 1 waiting record on a held document with no PMCID or DOI. It hid 1 record on paper `PMC0000001`, which carries the DOI `10.1000/held-nowhere` and the PMCID `PMC0000001` and which the project does not hold (the reproduction's `filter.ts` adds that record to the filter's input).
- **Likely cause:** `src/screens/Guild.tsx:627-628`: the strip's sentence arrived with alpha 1.0's identifier rule in commit `0100041`, and commit `5287542` moved `keepable` (`src/screens/Guild.tsx:208-211`) to `paperHeld` (`src/lib/review.ts:215-217`) and left the sentence and the comments at `src/lib/review.ts:224` and `:310` as they stood. (confidence: high)
- **Fix size:** small: the strip's sentence at `src/screens/Guild.tsx:627-628` and the two comments at `src/lib/review.ts:224` and `:310`, each naming documents the project does not hold.
- **Stood on:** the first refutation.

### S1: 14 findings here, 15 with the paid debts above

#### H5-01 · S1 · Contract break · literature: kit.ProjectService narrowing

Once project B holds a document stored under project A's kit source, a literature search B runs during A's ingestion returns A's newly ingested private document, its text and a citable passage id, because B's exclusion list is read before the kit's retrieval runs.

- **Contract:** `core/openferment_core/literature/kit.py:15-16`, "Every read a project makes is narrowed to its linked documents"; and `docs/decisions/ADR-002-sci-rag-kit.md:82-85`, "the sources of the project's documents go to the kit as its `sources` allowlist and the other documents of those sources as `exclude_document_ids`, so a shared document is visible to each project that linked it and to no other".
- **Reproduce:** `bash bughunt/repro/H5-01/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** Every hit B's `GET /api/literature/search` returns is a passage of a document B holds. A's private notes stay out of B's hits during A's ingestion and after it.
- **Observed:** In both runs B held 1 document, under kit source `project:bh-a:paste`, and B's search returned "A private note 0" with passage id `p0` and its full text ("RACEMARKH501 appears in A's private race note number 0 with token RACEMARKH501N0."). For that note, heldByA was true. For the same note, heldByB was false. Run 1 caught it in 18 searches during A's 2 pastes, and run 2 in 17 searches during A's 1 paste, each window 0.5 s. One search from B after A stopped returned 0 of A's notes in both runs.
- **Likely cause:** `core/openferment_core/literature/kit.py:405-411` (`_narrowed`) reads `visible` (`kit.py:353-370`) in a session of its own and hands the kit the sources allowlist and exclusion list of that moment; the retrieval runs afterwards in separate statements (`kit.py:433-436`, and `answer_stream` at `kit.py:453-454`), so a document A commits under the shared source in between passes `Document.source.in_(...)` and `Document.id.not_in(...)` in the kit's `scope_conditions` (`sci_rag/retrieve/types.py:88-91`). (confidence: high)
- **Fix size:** small: the narrowing in `_narrowed` and `visible`, for example a condition on the documents B holds (`Document.id IN held`) that the retrieval statement evaluates itself.
- **Severity:** S1, the reading of the entry's writer and of an independent severity panel (the scale's words: one project reading or writing another project's rows). The refuting agent read S2.
- **Stood on:** the first refutation.

#### H7-01 · S1 · Contract break · client store: the Durable pending-writes queue

With two tabs open on one project during a service outage, each tab saves its own in-memory queue whole over the browser's one IndexedDB snapshot, so tab B's save erases tab A's queued bench reading, and once tab A closes that reading never reaches the service.

- **Contract:** `docs/decisions/ADR-014-durable-write-queue.md:20-22`, "a write the service has not yet acknowledged is, so a decision made while the service is away survives a reload and is sent when the service answers"; and `src/lib/projectState.ts:9-12`, "The browser keeps only the rows the service has not yet acknowledged: an outbox, saved with the preferences (durable.ts), so a deposition at the bench survives a reload while the service is away and is sent when it answers again."
- **Reproduce:** `bash bughunt/repro/H7-01/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** Tab A's reading (5.5 USD/kg) stays in the queue through tab B's save and both tabs closing. Once the service answers, it holds A's deposition with 5.5 USD/kg beside B's with 6.6 USD/kg.
- **Observed:** In both runs the snapshot queue held A's deposition with `["5.5 USD/kg"]` after A wrote, held B's deposition alone with `["6.6 USD/kg"]` after B wrote, and held B's alone with both tabs closed; tab A had shown "1 measured" before it closed. Once the service answered and a new tab opened, the service held A's deposition with entries `[]` and B's with `["6.6 USD/kg"]`, the queue was `[]`, and the new tab showed no words about a dropped reading.
- **Likely cause:** `src/store.ts:3669` calls `saveDurable(snapshotOf(s))`, which writes this tab's own queue (`src/store.ts:3539`, `outbox: s.stateOutbox,`) whole under the one browser-wide key (`src/lib/durable.ts:50`, `const KEY = 'snapshot';`, written by `put(snapshot, KEY)` at `src/lib/durable.ts:277`); a tab reads the stored outbox once, at hydrate (`src/store.ts:2544`), so the tab that saves last sets the queue for the whole browser. (confidence: high)
- **Fix size:** medium: the Durable save path in `src/store.ts` and `src/lib/durable.ts`, merging the stored outbox with the tab's own before each write or coordinating the tabs; review decisions and Guild writes ride in the same snapshot.
- **Severity:** S1, the reading of the entry's writer and of an independent severity panel (the scale's words: lost or corrupted data). The refuting agent read S2.
- **Stood on:** the first refutation.

#### H7-04 · S1 · Broken use · client store and project state: a scope's parameter overrides

With two tabs open on one Proforma scenario's parameter panel, each typing a value for a different parameter, the second tab sends the scope's whole override list as it loaded it, and the service replaces the scope with that list, so the first tab's kept override is deleted with no refusal and no word on either page.

- **Contract:** `src/store.ts:2391`, the comment on `setOverride`: "A person's change, under their name, by scope and key: one a parameter."; and `src/components/ParameterPanel.tsx:14-17`, "each change is an `Override` under the reviewer name, at now, kept in the open project's rows (`setOverride`; lib/projectState.ts)".
- **Reproduce:** `bash bughunt/repro/H7-04/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** The service keeps both overrides of the scenario's scope, `feed_glucose_conc=1.234` from tab A and `titre=5.678` from tab B. If a write must stand for the whole scope, a page says in words that it replaced the other tab's override.
- **Observed:** In both runs the service held `[]` before either tab typed, `["feed_glucose_conc=1.234"]` after tab A typed, and `["titre=5.678"]` after tab B typed; tab A sent `[["feed_glucose_conc=1.234"]]` and tab B sent `[["titre=5.678"]]`. After a reload tab A showed `feed_glucose_conc` as `{"value":"—","overridden":"false"}`, and the toasts read `{"A":[],"B":[]}`.
- **Likely cause:** `src/lib/projectState.ts:78`: `rowsOf` keys overrides by scope (`overrides: entries(state.overrides)`), so the row `changes()` sends is the scope's whole list as this tab holds it; `setOverride` (`src/store.ts:2393-2400`) builds that list from the tab's own `parameterOverrides[scope]`, which `hydrateProjectState` (`src/store.ts:1043-1084`) loads once, and the `overrides` branch of `_put` (`core/openferment_core/project_state.py:601-607`) deletes every override row of the scope and inserts the list it was sent. (confidence: high)
- **Fix size:** medium: the override write path in `src/lib/projectState.ts` and `src/store.ts` and the `overrides` branch of `project_state._put`, by a write per key or a check against the rows a write replaces, with words on the page when the service refuses.
- **Severity:** S1, the reading of the entry's writer and of an independent severity panel (the scale's words: lost or corrupted data (a person's or the project's kept data is gone, overwritten)). The refuting agent read S2.
- **Stood on:** the second refutation, by the kind's own standard; the first set it aside because it read `core/openferment_core/project_state.py:156` and the state route's docstring (`core/openferment_core/api.py:2845`, "One row kept whole") as making a whole-scope replace the documented write, with no text promising that two tabs' writes to one scope merge.

#### H5-03 · S1 · Contract break · project state: PUT /api/state/{kind}/{item_id} (scenarios, trains)

`PUT /api/state/scenarios/{id}` naming a study scenario's id and `PUT /api/state/trains/{id}` naming a model's kept train each answer 200 and overwrite that row in place, so the study scenario reads 404 from the studies routes, the kept train leaves the kept store, the row keeps its first maker in `created_by`, and the audit records each overwrite as a first keep.

- **Contract:** `core/openferment_core/pureos/kept.py:12`, "ONE WRITE FUNCTION. `keep_train` is the only function that writes the store" (the store is the `trains` rows of kind `kept`, `kept.py:41-42`); and `core/openferment_core/db/models.py:214-216`, "Two kinds of scenario share the table (migration 0004): `proforma`, the rows the Proforma screens keep (project_state.py), and `engine`, a study's scenario on a library plant or an openFerment flowsheet (studies/)."
- **Reproduce:** `bash bughunt/repro/H5-03/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** Each PUT is refused in words, a 422 naming the row another kind keeps under that id. The study scenario reads back from `GET /api/studies/scenarios/{id}`, and the kept train stays in `GET /api/pureos/trains-kept`.
- **Observed:** In both runs `PUT /api/state/scenarios/ssc-21b4b9fdadce` as bob answered 200; `GET /api/studies/scenarios/ssc-21b4b9fdadce` then answered 404 "the project holds no scenario ssc-21b4b9fdadce", the list read `[]`, the row went from "engine, made by alice" to "proforma, made by alice", and `DELETE /api/state/scenarios/ssc-21b4b9fdadce` answered 200 and removed the row. `PUT /api/state/trains/{id}` as bob on the model's kept train (tr-e65355ec8787 in run 1, tr-c0c571ba0d79 in run 2) answered 200, `GET /api/pureos/trains-kept` went from that one id to `[]`, and the row went from "kept, made by bh-h5-03-agent/0.1" to "made, made by bh-h5-03-agent/0.1". The audit holds `keep_scenarios` and `keep_trains` by bob as ordinary first keeps.
- **Likely cause:** `core/openferment_core/project_state.py:522-531`: `_held`, called at `project_state.py:579`, reads the rows of the kind being written through the `where` clauses at `project_state.py:146-149` (scenarios of kind `proforma`, trains of kind `made`), so a row of the other kind under the same id reads as absent; `project_state.py:611` then calls `rows.put`, which upserts on `(project_id, id)` (`core/openferment_core/db/rows.py:61-66`) and replaces body and kind in one statement. (confidence: high)
- **Fix size:** small: `project_state._put` refuses an id its table holds under another kind, in words naming that row, with a test for scenarios and one for trains.
- **Severity:** S1, the reading of the entry's writer and of an independent severity panel (the scale's words: lost or corrupted data; a wrong provenance label shown as sound). The refuting agent read S3.
- **Stood on:** the first refutation.

#### H3-01 · S1 · Contract break · validate.py anchoring (§2.4 rule 3) and biorepo.write's re-anchoring

`validate.anchor_candidate` compares a quote's number bare when the quote's unit does not convert into the candidate's and labels the match `converted`, so six cross-unit candidates anchor (2.15 USD kg⁻¹ on "2.15 USD/gal" and 45 g L⁻¹ on "45% (v/v)" among them), and `biorepo.write`, which re-anchors through the same check, stores the first as `verified` and the second as `gold`.

- **Contract:** `CLAUDE.md:54`, "A record's value stands inside the verbatim quote it anchors to, in a unit its field is denominated in"; and `core/openferment_core/models.py:934`, `ValueBasis` records "How §2.4 rule 3 found the value in the sentence".
- **Reproduce:** `bash bughunt/repro/H3-01/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** Each of the six candidates whose quote states its number in a unit `units.convert` refuses to turn into the candidate's unit is refused on rule `value`, as the control 45 g/L on "45 mg/L" is. `biorepo.write` refuses with rule `quote` the accept of 2.15 USD kg⁻¹ on "2.15 USD/gal" and the gold 45 g/L on "45% (v/v)".
- **Observed:** Both runs anchored all six cross-unit candidates with valueBasis 'converted' after `units.convert` raised `UnitError` for each pair, the USD gal⁻¹ to USD kg⁻¹ pair with the words "guessing it would fabricate a price". "$2.15/gal" parsed as 2.15 with no unit and anchored as 'exact'. The control was refused on rule 'value'. `biorepo.write` stored the accept of `cl1-R1-00000001` with provenance 'verified' and the gold 45 g/L on `cl1-R1-00000002` with provenance 'gold'. It refused the control gold on rule `quote`. `openferment.records` then held `minimum_selling_price | 2.15 | USD kg⁻¹ | verified` on "The minimum ethanol selling price was 2.15 USD/gal in the base case." and `ethanol_titre | 45 | g L⁻¹ | gold` on "The final ethanol concentration was 45% (v/v) after fermentation."
- **Likely cause:** `core/openferment_core/validate.py:789` returns the quote's number unchanged when `convert` raises inside `_as_candidate_unit` (`validate.py:780-789`), so rule 3 compares the two numbers bare, and `value_basis` (`validate.py:846-849`) labels any match `converted` when the two unit strings differ; `core/openferment_core/biorepo.py:392` re-anchors each promoted value through `anchor_candidate`, so an accept and a gold decision pass the same check. (confidence: high)
- **Fix size:** small: `_as_candidate_unit` and `value_basis` in `validate.py`, refusing on rule `value` once rule 4 has accepted the candidate's unit and the quote's unit does not convert, and setting the `converted` label from whether `convert` ran; the quantity parser reads "$2.15/gal" as USD gal⁻¹.
- **Severity:** S1, the reading of the entry's writer and of an independent severity panel (the scale's words: a wrong number or a wrong provenance label shown as sound; lost or corrupted data). The refuting agent read S2.
- **Stood on:** the first refutation.

#### H6-02 · S1 · Contract break · upgrade path: pnpm db:import-alpha1 into BioRepo

`pnpm db:import-alpha1` carries an alpha 1.0 `biorepo.json` whose verified decision holds a gold value with an origin of kind `model-estimate` into the project's decisions, and BioRepo then serves that record as verified with provenance gold; the case needs a file edited by hand or made outside alpha 1.0, since alpha 1.0's own `Quantity` holds a value and a unit alone.

- **Contract:** `CLAUDE.md:54` (R), "a model estimate never enters a record store, and each store refuses one (ADR-006; `core/tests/test_estimates.py`, acceptance A6)"; and `docs/decisions/ADR-006-quantities-and-estimates.md:97-100`, "No record store takes an estimate: `basis.refuse_estimates` finds an origin or a source of kind `model-estimate`, or a provenance `assumed`, anywhere in what a store is asked to keep, and BioRepo (`WriteRefused` rule `estimate`, a dry run included), the candidates store and a project's depositions and measurements (`StateRefused`) refuse it before writing."
- **Reproduce:** `bash bughunt/repro/H6-02/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** The importer refuses the directory the way `biorepo.write` refuses the decision (rule `estimate`), naming `biorepo.json` and `cl1-P1-0001`, and writes nothing.
- **Observed:** In both runs the importer exited 0 with "carried … into project alpha-1-0-estimate:" and 1 decision, and the decisions row read `verified|gold|model-estimate|claude-x` (status, provenance, gold origin kind, origin by). `GET /api/biorepo/overlay` served `cl1-P1-0001` as status verified, provenance gold, gold 3.0 mg L-1 with origin kind `model-estimate` by `claude-x`. `POST /api/biorepo/check` with the same decision answered ok False, rule `estimate`, "cl1-P1-0001: BioRepo keeps records, and gold.origin is a model's estimate or rests on an assumption".
- **Likely cause:** `core/openferment_core/import_alpha1.py:174-180` (`_write`) inserts each decision straight into `t.decisions` and recomputes its provenance through `biorepo.provenance_of` alone, a path that skips the `basis.refuse_estimates` call `biorepo.write` makes first (`core/openferment_core/biorepo.py:304-307`), and the file is read through alpha 2.0's models, whose `Quantity` types an `origin` (`core/openferment_core/models.py:803`), so the origin is kept whole. (confidence: high)
- **Fix size:** small: run `basis.refuse_estimates` on each decision in `import_alpha1._write` before any insert, and refuse the whole import in words naming the file and the record; the docstring at `import_alpha1.py:16-18` then names the estimate rule among the ones the import runs.
- **Severity:** S1, the reading of the entry's writer and of an independent severity panel (the scale's words: a wrong provenance label shown as sound). The refuting agent read S3.
- **Stood on:** the first refutation.

#### H8-01 · S1 · Contract break · Intake: the kit's dedupe (kit._store, sci_rag content_hash_for)

A pasted text that differs from a held document in letter case alone is answered `linked` to that document, so project `rb`'s paste of "2000 mg" stores nothing of its own, and `rb`'s passages and search read project `ra`'s "2000 Mg", a unit 10^9 times the one `rb` gave.

- **Contract:** `docs/api/intake.md:53`, "`linked` (the kit held the same text, and the project now holds it too)"; and `core/openferment_core/literature/kit.py:13-14`, "A document the kit already holds (the same text, whoever collected it) is linked".
- **Reproduce:** `bash bughunt/repro/H8-01/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** "2000 mg" and "2000 Mg" are two texts, so `rb`'s paste is ingested as a document of its own, and `rb`'s passage reads `rb`'s "2000 mg".
- **Observed:** In both runs `ra`'s paste came back `ingested` (run 1 `2a5c87bf45d946b3a5d99d729431ba2c`, run 2 `de622e366ba34a0c8c1227288bfe5f07`). `rb`'s paste came back `linked` with the same id, and `rb`'s passage and search hit read "The biorefinery processes 2000 Mg of dry corn stover per day in the H8-01 repro." `sci_rag.chunks` held 1 row with "2000 Mg", 1 with "2000 kg" and 0 with "2000 mg". The control one word apart ("2000 kg") came back `ingested` as a document of its own (`56bd167f79354fb6bcacf75974440631`, then `dc74692f0dc54ba0a7233e44c162ed62`).
- **Likely cause:** `core/openferment_core/literature/kit.py:604`: `_store` (`kit.py:584-605`) links any `skipped_duplicate` to the project and reports it `linked` (or `held`) with no comparison of the held chunks' text against the entry's own, and the kit answers `skipped_duplicate` with the held document's id (`sci_rag/ingest/ingester.py:125-137`) because `content_hash_for` collapses white space and lower-cases the joined chunk bodies before hashing (`ingester.py:55-58`, both in `core/.venv/lib/python3.13/site-packages/`). (confidence: high)
- **Fix size:** medium: `kit._store` compares the held text with the entry's own before it links and says in words when a case variant was held, or the kit's hash keeps letter case; either path meets the kit's unique `content_hash` (`sci_rag/db/models.py:92`).
- **Severity:** S1, the reading of the entry's writer and of an independent severity panel (the scale's words: a wrong number or a wrong provenance label shown as sound; lost or corrupted data). The refuting agent read S3.
- **Stood on:** the first refutation.

#### H8-04 · S1 · Contract break · Intake upload of JATS XML (collectors.uploaded)

A JATS XML upload that declares and uses ISO-8859-1 is decoded as UTF-8 with replacement and answered `ingested` with no reason, and the kit stores its "5 µg/L of furfural at 30 °C" with U+FFFD for the micro sign and the degree sign.

- **Contract:** `core/openferment_core/literature/collectors.py:8-9`, "A file a person uploads (`upload`) and text a person pastes (`paste`) are taken as given."; and `docs/api/intake.md:17`, "`upload` | a file a person uploads: PDF, Markdown, text, HTML or JATS XML, at most 50 MB".
- **Reproduce:** `bash bughunt/repro/H8-04/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** The file is read in the encoding it declares, and its passage keeps "5 µg/L of furfural at 30 °C", which the standard library's XML parser reads from the same bytes. The other outcome the contract offers is `failed` with the reason in words, the answer the Markdown door gives the same Latin-1 bytes.
- **Observed:** In both runs `assay.xml` (bytes `b'5 \xb5g'` and `b'30 \xb0'`) was answered `ingested | no reason given`, and the project's passage and the kit's chunk row read `'The supernatant held 5 \ufffdg/L of furfural at 30 \ufffdC after 48 h in the H8-04 repro.'`, each `\ufffd` a U+FFFD. The same sentence in Latin-1 as `assay.md` was answered `failed | the kit did not store it: parse error: 'utf-8' codec can't decode byte 0xb5 in position 32: invalid start byte`. The UTF-8 control `assay-utf8.xml` was `ingested` and kept "5 µg/L ... 30 °C", and `sci_rag.chunks` held 1 row of the sentence with U+FFFD before g/L and 1 with the micro sign.
- **Likely cause:** `core/openferment_core/literature/collectors.py:1688`: `xml = data.decode("utf-8", errors="replace")` turns the uploaded bytes into a string before `split_jats` (`collectors.py:1018`) and `jats_citation` (`collectors.py:1328`) call `ET.fromstring(xml)`, so expat receives text whose 0xB5 and 0xB0 bytes are already U+FFFD and never reads the encoding declaration. (confidence: high)
- **Fix size:** small: `uploaded` hands the parser the file's bytes, or decodes strictly and refuses in words, with a test on a Latin-1 file.
- **Severity:** S1, the reading of the entry's writer and of an independent severity panel (the scale's words: lost or corrupted data). The refuting agent read S3.
- **Stood on:** the first refutation.

#### H3-08 · S1 · Contract break · unit engine: units.py LABELLED_MASS_RATIO and src/engine/units.ts

The labelled-mass-ratio rule in `units.normalize` and in the browser's `normalizeUnit` reads a gallon, a gram-mole or a gallon per minute joined to a `g` as a labelled gram, so `g/gal`, `gal/g`, `g/gmol`, `gmol/g`, `g gal-1`, `gal g-1`, `g/gallon`, `gpm/gpm` and `g/gpm` normalise to the yield unit `g g⁻¹`, `convert` applies a factor the engine invents, and a quote's 0.45 g/gal is stored as a verified ethanol yield of 0.45 g g⁻¹.

- **Contract:** `core/openferment_core/units.py:24-27`, "An unknown unit is `UnitError` ... Nothing here invents a conversion factor."; and `core/openferment_core/units.py:104-105`, the rule's own scope, "Grams per gram with each gram labelled by what it weighs: g EtOH/g glucose, gx/g, gDW gglucose⁻¹, g biomass [g glucose]⁻¹."
- **Reproduce:** `bash bughunt/repro/H3-08/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** Each spelling that holds `gal`, `gmol` or `gpm` returns None, as `gal`, `gmol`, `gpm` and `g/furlong` do, and `convert` raises `UnitError` for it. Anchoring refuses 0.45 `g/gal` for `ethanol_yield_substrate` on rule `unit`, as it refuses 0.45 `g/furlong`.
- **Observed:** In both runs all nine probes normalised to `g g⁻¹` in the family `yield`, in `units.py` and in `src/engine/units.ts` alike, and `convert` returned 180.16 for (180.16, `g/gmol`, `g g⁻¹`), 1.0 for (1, `gal/g`, `kg kg⁻¹`) and 1000.0 for (1, `g/gal`, `mg g⁻¹`). The candidate 0.45 `g/gal` on "The broth held 0.45 g/gal of residual ethanol at harvest." anchored as 0.45 g g⁻¹ with `valueBasis 'exact'`, and `biorepo.write` left the records row `ethanol_yield_substrate | 0.45 | g g⁻¹ | verified`. The controls held: the five labelled grams read `g g⁻¹`, and 0.45 `g/furlong` was refused on rule `unit` ("unit 'g/furlong' does not normalise").
- **Likely cause:** `core/openferment_core/units.py:108-111`: each gram in `LABELLED_MASS_RATIO` is `g(?:\s*[a-z]+)?`, so a label may join the `g` with no space, and `gal`, `gallon`, `gmol` and `gpm` each match as `g` plus the label `al`, `allon`, `mol` or `pm`; `units.py:144-145` then returns `g g⁻¹` for the whole spelling, and `src/engine/units.ts:369-372` holds the same two patterns, read at `src/engine/units.ts:390`. (confidence: high)
- **Fix size:** small: the two pattern pairs in `units.py` and `src/engine/units.ts` keep a joined label from completing a unit word, with a fixture pair for each spelling.
- **Severity:** S1, the reading of the entry's writer and of an independent severity panel (the scale's words: a wrong number or a wrong provenance label shown as sound). The refuting agent read S3.
- **Stood on:** the first refutation.

#### H3-02 · S1 · Contract break · Rule 1's detector: validate.find_number, validate_plan and held_to_rule_one (Postdoc's claims and gaps)

`validate.find_number` finds no number in "two dollars per gallon", "Ten per cent", "Ten tonnes", "Two thirds", "Hundreds of litres" or a superscript "²", so `validate_plan` keeps a Postdoc claim stating any of them with its cited record's class `verified`, and `held_to_rule_one` keeps such a gap. This entry holds to these six forms. The three forms `core/openferment_core/practice.py:73-76` names as `find_number`'s known gaps (pH5, x10, doubled) stand outside this entry.

- **Contract:** `CLAUDE.md:55`, "a claim with a number in its words is dropped and counted (ADR-006)"; and `src/components/AnswerPlanView.tsx:7-8`, the screen that prints a kept claim's words at line 177, "Nothing here prints model prose containing a quantity, because the validator guarantees the prose has none".
- **Reproduce:** `bash bughunt/repro/H3-02/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** Each claim or gap whose words state a number in one of these six forms is dropped and counted with its reason, the way its twin in digits or in a word the rule knows is dropped.
- **Observed:** In both runs, their output byte-identical, `find_number` returned None for all six word forms. It caught each twin as '2', 'Ten', 'Ten', 'Half', 'hundred' and '½'. `validate_plan`, each claim citing record r1 (0.72 USD kg⁻¹, class verified by `biorepo.provenance_of`), printed "KEPT verified" for w1 to w6. It dropped d1 to d6 with "rejected 6", each reason reading "claim text contains a number (...) — values come from the record". `held_to_rule_one` kept the gap "Two thirds of the plant's cost has no record behind it."
- **Likely cause:** `core/openferment_core/validate.py:176-177` blanks a determiner one to ten (`_DETERMINER`, `:152-154`) whenever `_is_unit_word` (`:157-166`) misses the next word, and that test knows the closed list at `:141-148` and what `units.normalize` resolves, which is None for "dollars", "per" and "tonnes"; `_WORD_NUMBER` (`:74-76`) ends in `(?![a-z])`, so "thirds" and "Hundreds" match nothing; `_DIGIT` (`:60`) starts its superscript range at U+2070 and leaves out U+00B2, U+00B3 and U+00B9, the code points the same file lists in `_SUP_DIGITS` at `:547`. (confidence: high)
- **Fix size:** medium: the three patterns in `validate.py` (the determiner's unit test, the plural number words, the digit class), each form with a fixture in the validator's tests, held against the false positives the comment at `validate.py:62-65` guards.
- **Severity:** S1, the reading of the entry's writer and of an independent severity panel (the scale's words: a wrong number or a wrong provenance label shown as sound). The refuting agent read S3.
- **Stood on:** the first refutation.

#### H2-01 · S1 · Wrong number · studies/comparisons (POST /api/studies/comparisons, study_compare, study.md)

A comparison row labels every run's value of one name with the first run's unit and reckons each run's relative change from the raw numbers, so one product titre forecast in g L-1 and in mg L-1 sits on one row labelled g L-1 with a change of +998.9998, which the export's `study.md` prints as +99899.98%.

- **Contract:** `docs/api/studies.md:140`, "`[{key, unit, values, change}]`: every output any run answers, each run's value (null for a run with no output of that key), and its relative change from the first run's" and "a run of any other engine's are its outputs.values (`values.<name>`, each in its unit; `docs/api/runs.md`, Outputs)"; and `docs/api/runs.md:23`, "each output as `{name, quantity}`, the quantity in the unit the run's artifact states".
- **Reproduce:** `bash bughunt/repro/H2-01/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** The row keeps each run's value in its own unit, or holds both values to one unit before it reckons the change. Run 2's 19533.85 mg L-1 is 19.5338 g L-1, so its change from run 1's 19.5338 g L-1 is 0.
- **Observed:** Both runs read `finals.product` as 19.533849398401337 g L-1 from `GET /api/runs/77b2c4bb17cb986b` and as 19533.8458971344 mg L-1 from `GET /api/runs/e123b1d660888267`. The comparison row `values.finals.product` carried unit 'g L-1', values [19.533849398401337, 19533.8458971344] and change [0.0, 998.9998207589879]. The export's `study.md` printed `| values.finals.product | g L-1 | 19.5338494 | 19533.8459 | +99899.98% |`.
- **Likely cause:** `core/openferment_core/studies/comparisons.py:135` takes the row's unit as the first non-null unit of the runs (`unit = next((u for u in units if u is not None), None)`) and drops the others, and `comparisons.py:137` reckons `_change(v, values[0])` over the raw values, `_change` (`comparisons.py:74-77`) taking two numbers and no unit; `core/openferment_core/studies/exports.py:315` prints that unit and change into `study.md`. (confidence: high)
- **Fix size:** small: `_rows` in `studies/comparisons.py` gives each unit of a key its own row, or converts each value into the first run's unit through the units engine before `_change`.
- **Severity:** S1, the reading of the entry's writer and of an independent severity panel (the scale's words: a wrong number or a wrong provenance label shown as sound). The refuting agent read S2.
- **Stood on:** the first refutation.

#### H1-04 · S1 · Contract break · biosteam engine: scenario flowsheets (Proforma worker)

A biosteam run of `ethanol_glucose_v0` with all six inputs fixed keeps a base price of 6.360 USD/kg and prices each of its 500 samples of the same inputs at 7.372 USD/kg, and a replay of the kept artifact in the same service answers 7.372 with 51 differences under a stated precision of `rtol` 0, `atol` 0.

- **Contract:** `docs/api/engines.md:616-618`, "A scenario flowsheet's is `rtol` 0, `atol` 0: `proforma.run` registers no tolerance, so its replay holds every output identically."; and `core/openferment_core/flowsheets/ethanol_glucose_v0.py:222`, "Empty it, so a case gives one answer whatever came first".
- **Reproduce:** `bash bughunt/repro/H1-04/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** With every input fixed, each of the 500 samples prices as the base case does, so every quantile equals `basePrice`. A replay of the kept artifact is identical, as a precision of `rtol` 0, `atol` 0 asks.
- **Observed:** Both runs served the stated precision `{'rtol': 0.0, 'atol': 0.0}` and kept run `4f2ccc41f73b2f66` with 500 samples, 500 feasible, `basePrice` 6.36040554632803 USD/kg and quantiles p5, p25, p50, p75 and p95 all 7.371976772110385. The replay in the same service answered `identical` False, `withinTolerance` False and 51 differences, among them `basePrice` 6.36040554632803 -> 7.371976772110385 and `baseCostLines.capex` 1.1303753027262005 -> 1.2980509548267865. A replay after a restart, in a fresh worker, was identical with 0 differences.
- **Likely cause:** `core/openferment_core/flowsheets/ethanol_glucose_v0.py:225-227` empties the recycles and simulates under BioSTEAM's default recycle tolerances (1 kmol/h and 0.01 relative), and at 1000 t/yr the whole sieve recycle `s9` (about 1.0 to 1.2 kmol/h) falls inside them, so the loop `SYS4` stops after two iterations on the first case after a build and after one on each later case; `core/openferment_core/workers/proforma_worker.py:191-202` keeps that one built plant per flowsheet (`_BUILT`), and `run` (`proforma_worker.py:547-557`) evaluates the base case and then every sample on it. (confidence: high)
- **Fix size:** medium: the recycle tolerances `ethanol_glucose_v0.simulate` sets on the system and its subsystems, and a replay test at a plant scale near 1000 t/yr.
- **Severity:** S1, the reading of the entry's writer and of an independent severity panel (the scale's words: a wrong number or a wrong provenance label shown as sound). The refuting agent read S2.
- **Stood on:** the first refutation.

#### H4-02 · S1 · Wrong number · cost card: proforma_worker.tea_breakdown, flowsheets/custom_train_v1.parts, CostWaterfall

A `custom_train_v1` run's cost card closes on 9.0791, the TEA's price per kg of the whole product stream, labelled in USD per kg of Ethanol contained. The card's lines are per kg of Ethanol contained and sum to 9.1546, the run's base price. The note under the card says the lines sum to 9.0791 and that the TEA solved a second price.

- **Contract:** `core/openferment_core/flowsheets/__init__.py:20-21`, "the solved `price` (USD per kg of the product stream), `basis_flow` (kg/hr the price is per)"; and `src/components/figures/CostWaterfall.tsx:6-9`, "The last row is the product price the breakdown was read at (`TeaBreakdown.productPrice`) ... the lines sum to it by construction in the service."
- **Reproduce:** `bash bughunt/repro/H4-02/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** The price a flowsheet hands the worker and its `basis_flow` name one flow. The cost card then closes on 9.1546 USD per kg of Ethanol contained in the train's product stream, the sum of its lines and the run's base-case price, labelled "Base-case price", with the price note empty.
- **Observed:** Both runs (composite run 15b34d70b7e48a76) gave lines 2.8848 + 0 + 1.0575 + 3.9195 + 1.2928 summing to 9.1545818834, equal to `basePrice`. The same runs gave `tea.productPrice` 9.0790885100 and `basisFlow` 122.429856 kg/h, the Ethanol in the 123.447870 kg/h stream `T304_outlet`. `tea.productPrice` × stream mass / `basisFlow` = 9.1545818834. In Chromium the card's closing row read "Price the lines are read at 9.0791", and its note read "The breakdown is read at the product's set price, 9.0791 USD per kg of Ethanol contained in the train's product stream, and its lines sum to that price. The TEA solves the price at its internal rate of return to 9.1546 USD per kg of Ethanol contained in the train's product stream, the run's base-case price."
- **Likely cause:** `core/openferment_core/flowsheets/custom_train_v1.py:384-386`: `parts` returns `"price": b.price`, the TEA's price per kg of the product stream, beside `"basis_flow": float(b.product.imass[b.product_chemical])`, the product contained; `core/openferment_core/workers/proforma_worker.py:452` sets `productPrice` from that price, and `proforma_worker.py:469` divides every line by `basisFlow` × hours, so the lines sum to the price per kg contained, which `evaluate` computes for `basePrice` at `custom_train_v1.py:358`. (confidence: high)
- **Fix size:** small: `custom_train_v1.parts` hands a price and a basis flow on one basis (the stream's mass, or the price converted per kg contained), with a test that the lines sum to `productPrice` for `custom_train_v1`.
- **Severity:** S1, the reading of the entry's writer and of an independent severity panel (the scale's words: a wrong number ... shown as sound). The refuting agent read S3.
- **Stood on:** the first refutation.

#### R1-03 · S1 · Wrong number · `pnpm lit:graph --dry-run` and the records that carry its figures

`pnpm lit:graph --dry-run` prices the summed characters of every batch as one request, so past 100,000 tokens Haiku 5.5's long-prompt prices (0.50 and 2.50 USD a million) apply to every batch, and the dry run prints, and the records carry, input and ceiling figures five times what the build's requests cost one batch at a time.

- **Contract:** `core/openferment_core/literature_live.py:12-13`, "what their input and the most a build could cost come to on the route's first model (each batch's whole answer, the figure the day's cap holds against)"; and `core/openferment_core/llm.py:340-342`, "past the threshold (in prompt tokens, cache reads and writes included) the whole request pays the second pair".
- **Reproduce:** `bash bughunt/repro/R1-03/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** The dry run prices each batch as the one request the build sends for it and sums those prices. That comes to 0.012816 USD of input and 0.074772 USD at most for the fresh database's 12 batches, and to 0.0440 and 0.4648 USD for F.5's 92 batches, and a given batch keeps one price at any batch count.
- **Observed:** On the fresh database the dry run printed `inputUsd` 0.064058 and `mostUsd` 0.373881 over 12 batches. The build sent 12 requests of 42,705 characters each (about 10,676 kit tokens), the prompts the dry run measured, and priced one request at a time they come to 0.012816 and 0.074772 USD, so the dry run's figures are 5.00 times these. One batch's input is 0.001068 USD in the 4-batch `--limit 40` dry run. In the 12-batch dry run, one batch's input is 0.005338 USD. F.5's measure through `graph_command` printed `inputUsd` 0.219862 and `mostUsd` 2.32393, the records' 0.2199 and 2.3239 to the digit (`docs/reports/literature-retrieval.md:116-117`, `docs/PROGRESS.md:3372` and `:609`). The same 92 prompts priced request by request come to 0.0440 and 0.4648 USD.
- **Likely cause:** `core/openferment_core/literature_live.py:106` sums every batch's prompt characters (`chars = sum(len(p) for p in prompts)`), and lines 110-112 pass that sum to `llm.cost_usd` as one request; `cost_usd` takes its tier from `prices_for(model, input_tokens + ...)` (`llm.py:509`, `prices_for` at `llm.py:491-496`), and `LONG_PROMPT_PRICES` (`llm.py:343-345`) then prices every token of the sum at 0.50 and 2.50 USD a million. (confidence: high)
- **Fix size:** small: `graph_command` prices each prompt with `llm.cost_usd` and sums the results; `core/tests/test_literature_live.py:97`, which asserts `0 < inputUsd < mostUsd` alone, gains a case past the threshold; the record lines at `docs/reports/literature-retrieval.md:116-117` and `docs/PROGRESS.md:3372` and `:609` take the per-request figures.
- **Severity:** S1, the reading of the entry's writer and of an independent severity panel (the scale's words: a wrong number ... shown as sound). The refuting agent read S3.
- **Stood on:** the first refutation.

### S2: 1 finding here, 2 with the paid debts above

#### H14-02 · S2 · Contract break · geneOS Hosts and strain pages, Catalogues, anchoring (validate.strain_id), fermOS strain binding

Anchoring resolves a record's organism through `validate.vocabulary()`, whose strain map is empty in the service, so a record whose organism is a kept strain's alias keeps the raw wording with no strain id, and the strain page, the Hosts counts and fermOS's strain filter, which match on that id, count no record for the strain.

- **Contract:** `src/screens/Organisms.tsx:46-47`, "anchoring resolves the wording a paper uses to a strain's id by the name and the other names its entry keeps (validate.strain_id on the service)"; and `core/openferment_core/validate.py:1165-1167`, "the organism, resolved to a strain id where the wording names one (an exact alias, or an alias standing in it as a whole word). The id is what every screen matches on".
- **Reproduce:** `bash bughunt/repro/H14-02/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** With strain `ethanol-red` kept under the aliases "Ethanol Red" and "Saccharomyces cerevisiae Ethanol Red", a candidate whose organism is "Saccharomyces cerevisiae Ethanol Red" is anchored with `strainId` `ethanol-red` and `organism` `ethanol-red`, the wording kept as `organismText`.
- **Observed:** Both runs served the candidate from `GET /api/biorepo/overlay` as `{"organism": "Saccharomyces cerevisiae Ethanol Red", "organismText": null, "strainId": null}`. In the project, `catalogues.as_strain_aliases()` held `{'ethanol red': 'ethanol-red', 'saccharomyces cerevisiae ethanol red': 'ethanol-red'}`, `validate.vocabulary()['strains']` was `{}` and `validate.strain_id('Saccharomyces cerevisiae Ethanol Red')` returned None. The control `validate.match_whole_word` over the catalogue's aliases returned `ethanol-red`.
- **Likely cause:** `core/openferment_core/validate.py:889` sets `strains = {}` whenever `vocabulary()` takes no path, and `strain_id` (`validate.py:932-934`), which `anchor_candidate` calls at `validate.py:1170`, reads that map alone, so anchoring never reads the catalogue's aliases (`catalogues.as_strain_aliases`, `core/openferment_core/catalogues.py:600`), whose one caller is `module_stores._strain_aliases` (`core/openferment_core/module_stores.py:304-309`) for search rows. (confidence: high)
- **Fix size:** medium: `strain_id` reads the open project's strain catalogue, with the `vocabulary()` cache keyed by project and cleared on a keep, and the two tests that hand in a strain table of their own by monkeypatching `validate.vocabulary` (`core/tests/test_validate.py:160-169`, `core/tests/test_fermos_bind.py:142`) keep a strain in the catalogue.
- **Severity:** S2, the reading of the refuting agent and of the entry's writer. An independent severity panel read S1: Anchoring serves a candidate whose organism is a kept strain's alias with strainId null and the raw wording as its organism.
- **Stood on:** the first refutation.

### S3: 50 findings here, 51 with the paid debts above

#### H1-01 · S3 · Contract break · engine runs: keep_run, run_engine, compute_kept

When four askers send the same kinetics run request at the same moment, every ask computes, and the one `runs` row keeps one asker in its `created_by` column and another in its body `by`, which `GET /api/runs/{id}` serves; the reproduction confirmed this on the kinetics engine.

- **Contract:** `docs/api/engines.md:541-544`, "The same request twice is one row, answered as it was first kept: its `by` and `created_by` are the first asker's, whoever asks again. `created_by` is the `runs` table's column for the asker, the request's person or model, served on every run as `EngineRun.by`, and check 8 reads both".
- **Reproduce:** `bash bughunt/repro/H1-01/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** One row whose `created_by` column and body `by` both name the first asker, served under that name by `GET /api/runs/{id}`, with every asker answered by that name.
- **Observed:** In each run 4 of 5 `mu_max` values gave a row whose names disagree, for example run 1's `c4efafb9ec0199cc` with `created_by 'asker-3'` and body `by 'asker-2'`, and run 2's `a6b532af461e088a` with `created_by 'asker-3'` and body `by 'asker-1'`, each served by `GET /api/runs/{id}` under the body's name. Each of those values showed 4 `job.running` events for its one run id, and on run 1's `mu_max=0.42` the four askers were answered with two names for the one row, 'asker-2' and 'asker-3'.
- **Likely cause:** `core/openferment_core/engine/runs.py:463-467` and `:484` (`keep_run`) read the held row, take `first` from this asker when none is held, and write through `_put` to `rows.put` (`core/openferment_core/db/rows.py:61-66`), an `INSERT ... ON CONFLICT DO UPDATE` that keeps the first insert's `created_by` and replaces `body`; the held check in `compute_kept` (`runs.py:546-559`) holds no lock up to that write, so every ask computes and writes, and the insert-once `rows.put_first` (`rows.py:69`) sits unused on this path. (confidence: high)
- **Fix size:** small: `keep_run`'s write in `engine/runs.py`, through `rows.put_first` or a lock held from the held check to the write.
- **Stood on:** the first refutation.

#### H1-03 · S3 · Broken use · conformance: conform._inside

`python -m openferment_core.engine.conform biosteam --thing ethanol_glucose_v0 --inputs <file>`, the documented form for a scenario flowsheet, stops with `ProjectRequired: This names no project` and keeps no verdict, with the file's six values set and with no file at all; the command needs `OPENFERMENT_PROJECT` set to some id, and no document asks for it.

- **Contract:** `docs/api/engines.md:670-672`, "`python -m openferment_core.engine.conform biosteam --thing ethanol_glucose_v0 --inputs <file>`. Named with a value it waits for left unset, the thing cannot run as it stands (the engine's `unready`), and the command refuses it in words before anything is made, keeping no verdict." The command's own docstring, `core/openferment_core/engine/conform.py:19`, says the checks "run in a project made for them, so nothing a person keeps is touched".
- **Reproduce:** `bash bughunt/repro/H1-03/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** With a file setting all six values, the command makes the eight checks on `ethanol_glucose_v0` and keeps one `engine_checks` row for `biosteam`. With no file, it refuses in words that name the six values that wait, and keeps nothing.
- **Observed:** In both runs the command with the file printed one row, "✗ the checks could not be made on biosteam: openferment_core.projects.ProjectRequired: This names no project. A request sends the X-OpenFerment-Project header (or ?project= on an event stream); a command sets OPENFERMENT_PROJECT.", exited 1 and kept 0 verdict rows; the command with no file gave the same words and exited 1. The control, the no-file command with `OPENFERMENT_PROJECT=any-id`, gave the documented refusal: "ethanol_glucose_v0 waits for 6 values its parameters give no default, which a run sets: feed_glucose_conc, glucose_price, plant_scale, productivity, titre, yield; set its values with --inputs <file>".
- **Likely cause:** `core/openferment_core/engine/conform.py:1050`: `_inside` asks `engine.unready(first[0], values)` before it makes and enters the checks' project at lines 1054-1055, and `BiosteamEngine.unready` reads the scenario flowsheet's parameters at `engine/biosteam.py:296` through the Proforma provider, which reaches `projects.current()` and raises `ProjectRequired` at `projects/__init__.py:58`. (confidence: high)
- **Fix size:** small: `_inside` in `engine/conform.py`, asking `unready` with the checks' project entered.
- **Severity:** S3, the reading of the refuting agent and of the entry's writer. An independent severity panel read S2: The documented command for checking a scenario flowsheet, `conform biosteam --thing ethanol_glucose_v0 --inputs <file>`, stops with ProjectRequired and keeps no verdict on every run in a default environment, with or without the file.
- **Stood on:** the first refutation.

#### H1-05 · S3 · Contract break · biosteam engine: the run and parameters routes

The biosteam engine's run and parameters routes take `AFEX, IB` for `cellulosic_ethanol_v0`, a configuration the engine's listing omits, build the plant in it and answer in BioSTEAM's words, and the run route keeps a refused runs row for it. (This entry holds the configuration half of the candidate, which the verdict confirmed. The lactic half meets the shelf rule at `docs/api/engines.md:639-642`.)

- **Contract:** `docs/api/engines.md:244-247`, "so is a configuration the thing does not name, and any configuration for a thing that takes none. The rule holds at every door: the run route, the parameters route and the engine tools, so the worker's `parameters` op receives the configuration a run would use"; and `docs/api/engines.md:611`, on the biosteam thing's configurations, "those it built in here".
- **Reproduce:** `bash bughunt/repro/H1-05/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** A run or a parameters read of `cellulosic_ethanol_v0` naming `AFEX, IB` is a 422 in words naming the four listed configurations. The refusal comes before any build, and the run keeps no row.
- **Observed:** `GET /api/engines` listed `cellulosic_ethanol_v0` in `dilute acid, IB`, `dilute acid, SCF`, `hot water, IB` and `hot water, SCF`. The run route with `AFEX, IB` answered HTTP 422 after 16 s in run 1 and 19 s in run 2, in BioSTEAM's words "cellulosic_ethanol_v0 AFEX, IB is infeasible here (BioSTEAM's InfeasibleRegion): <Mixer: M207> conversion of 'NH3' is over 100%; reaction conversion is infeasible", and kept refused row `a9c4e1880088113d` with configuration `AFEX, IB`; the parameters route answered 422 in the same words after 1 s. The control `dilute acid, SSCF` was a 422 in 0 s naming the shelf's eight configurations, `AFEX, IB`, `AFEX, SCF`, `alkaline, IB` and `alkaline, SCF` among them.
- **Likely cause:** `core/openferment_core/engine/biosteam.py:160`: `default_configuration` returns any configuration a request names, and the engine's `parameters` (`biosteam.py:265`) and `run` (`biosteam.py:277`) pass it on unchecked against the engine's own thing, so the one check left is `library._runnable` (`core/openferment_core/engine/library.py:121`), which holds it to the shelf's eight; `runs.thing_of` (`core/openferment_core/engine/runs.py:784`) holds the listing's rule, and `runs.py:814` and `:916` apply it to contract engines alone (`is_contract`, `runs.py:778`), a set the biosteam engine stays outside. (confidence: high)
- **Fix size:** small: the biosteam engine's `run` and `parameters` check a named configuration against the thing's listed configurations (`_library_things`, `biosteam.py:129-130`) before any build, with a test at both routes.
- **Severity:** S3, the reading of the entry's writer and of an independent severity panel (the scale's words: an edge case fails and a workaround exists). The refuting agent read S4.
- **Stood on:** the first refutation.

#### H1-06 · S3 · Contract break · engine contract: EngineThing shape, run_engine

A contract engine's worker whose `things` answer states a precision with an infinite `atol` passes the service's shape check, so `GET /api/engines` lists that `atol` as `null` with no error, and `POST /api/engines/{name}/run` for that thing answers a plain-text `500 Internal Server Error`.

- **Contract:** `docs/api/workers.md:62-68`, "An answer outside the shapes below (... a number that is NaN or infinite, ...) breaks the contract: the service raises `EngineBroken`, keeps no runs row and answers 503 in words."
- **Reproduce:** `bash bughunt/repro/H1-06/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** The service refuses the `things` answer as outside the protocol with `EngineBroken`: the engine is listed with those words in its `error`, and its run route answers 503 in words with no runs row kept, as it does for the control engine whose `atol` is -1.
- **Observed:** Both runs listed `h106: things=[('fine', {'rtol': 0.0, 'atol': 0.0}), ('infprec', {'rtol': 0.0, 'atol': None})] error=''`, and `POST /api/engines/h106/run {thing: infprec}` answered `500 text/plain; charset=utf-8 Internal Server Error` with 0 runs rows kept. The service log ended in `ValueError: Out of range float values are not JSON compliant: inf`, raised at `openferment_core/artifacts.py` line 148 (`artifact_id`) and line 130 (`canonical`). The controls held: `fine` in the same engine answered 200 with a run, and `h106neg` (atol -1) was listed with "EngineBroken: the h106neg worker's things op answered things outside their shape: precision.atol: Input should be greater than or equal to 0", its run answering 503 in words.
- **Likely cause:** `core/openferment_core/models.py:4509`: `EnginePrecision.atol` is `float = Field(ge=0)`, which admits `inf`, and `WorkerEngine._listed` (`engine/contract.py:141`) holds the things to that model alone, so `run_engine` puts the `inf` into the run's basis (`engine/runs.py:855`), `artifacts.canonical` raises `ValueError` under `allow_nan=False` (`artifacts.py:130`), and `engine_run` (`api.py:1415-1424`) maps no `ValueError`. (confidence: high)
- **Fix size:** small: a finite check on `EnginePrecision` in `models.py` (pydantic's `allow_inf_nan=False`), which `_listed` then turns into `EngineBroken`.
- **Stood on:** the first refutation.

#### H1-08 · S3 · Contract break · contract engines: a thing's configuration names at every door

A contract engine's thing listed with the configuration `" two "` passes the shape and stays listed, and the run route, the parameters route and the `engine_run` tool each strip the name a request gives and refuse it as `'two'`, so every door refuses a configuration the thing lists.

- **Contract:** `docs/api/engines.md:231-232`, "`configurations`: the configurations it runs in, each name 1 to 80 characters, or `[]` when it takes none."; and `docs/api/engines.md:244-246`, "so is a configuration the thing does not name, and any configuration for a thing that takes none. The rule holds at every door: the run route, the parameters route and the engine tools".
- **Reproduce:** `bash bughunt/repro/H1-08/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** Either the service refuses a things answer naming `" two "` as outside the shape and lists the engine with the words (`EngineBroken`), or `" two "` runs at `POST /api/engines/{name}/run`, reads at `GET /api/engines/{name}/parameters` and runs through `engine_run`, the worker receiving `" two "`.
- **Observed:** `GET /api/engines` listed the stand-in engine as `h108: things=[('cfg', ['one', ' two '], 'one')] error=''`, and the control run in `"one"` answered 200 with a done run. The run route in `" two "` and in `"two"` and the parameters route in `" two "` each answered `422 {"detail":"cfg runs in one,  two ; 'two' is none of them"}`, and `engine_run` answered `error: engine_run refused: cfg runs in one,  two ; 'two' is none of them`. The worker received `[('parameters', 'one'), ('run', 'one')]` alone, and the one runs row kept was `one:done`.
- **Likely cause:** `core/openferment_core/engine/runs.py:797`: `thing_of` strips the request's name (`cfg = (configuration or "").strip() or found.defaultConfiguration`) and tests it at line 801 against `found.configurations` as listed, and `ConfigurationName` (`core/openferment_core/models.py:4487`) holds a thing's names to a length of 1 to 80 alone, so a listed name with spaces around it can never equal a stripped request; the tool door strips once more first (`core/openferment_core/tools/writes.py:478`). (confidence: high)
- **Fix size:** small: `EngineThing` refuses a configuration name that differs from its stripped self, or `thing_of` matches the name as listed, with a test in the engine contract's suite.
- **Severity:** S3, the reading of the entry's writer and of an independent severity panel (the scale's words: an edge case fails and a workaround exists). The refuting agent read S4.
- **Stood on:** the first refutation.

#### H10-02 · S3 · Contract break · api.py routes over text columns

A path id, query filter or body text field holding U+0000 reaches PostgreSQL at 20 /api doors, and each answers 500 with the bare body `Internal Server Error` and no `detail`. The finding stands on these 20 doors. The kit's two /rag doors, which answer a problem+json 500 naming `DBAPIError`, count as weaker evidence.

- **Contract:** `core/openferment_core/api.py:208` (the OpenAPI document's `info.description`, also in `docs/api/openapi.json`), "A refusal is a status with its reason in `detail`, in words." For an id the project does not hold, `core/openferment_core/api.py:1433-1434` declares the 404 of `GET /api/runs/{run_id}` as "The project holds no run of that id, in words."
- **Reproduce:** `bash bughunt/repro/H10-02/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** At every door, an id the project does not hold answers a 404 in words, and a filter or text field the service will not take answers a 422 in words, as the five controls answer.
- **Observed:** In both runs the five controls answered 404 with a `detail` in words, for example `{"detail":"the project holds no runbook a\\x00b"}` at `GET /api/studies/runbooks/a%00b` and `{"detail":"the project holds no run no-such-run"}` at `GET /api/runs/no-such-run`. All 20 /api doors answered 500 with the bare body `Internal Server Error`, among them `GET /api/projects/a%00b`, `GET /api/runs/a%00b`, `GET /api/audit?who=a%00b`, `POST /api/projects` with the NUL in `name`, `by` or `description`, and `POST /api/practice/record` with a NUL `sessionId`. The service log named `asyncpg.exceptions.CharacterNotInRepertoireError: invalid byte sequence for encoding "UTF8": 0x00` 22 times, once a 500 across the /api and /rag doors, and afterwards `GET /api/projects/r1` answered 200 and the three refused projects answered 404.
- **Likely cause:** `core/openferment_core/api.py:424-426`: the handlers map `OperationalError`, `InterfaceError` and `ConnectionRefusedError` to a 503 in words and map no other database error, and no model or parameter refuses U+0000 before the store call, so the `DBAPIError` PostgreSQL raises for 0x00 in a text parameter reaches Starlette's generic 500. (confidence: high)
- **Fix size:** small: refuse U+0000 in ids, filters and text fields with a 404 or 422 in words, or map the database's data error to a refusal in words beside `api.py:424-426`.
- **Stood on:** the first refutation.

#### H11-01 · S3 · Inconsistency · host scripts: the key check across install.sh, pnpm ready, /api/health and the nightly

Over the `core/.env` that the live-host runbook's step 1 makes, whose key line is the example's placeholder `ANTHROPIC_API_KEY=sk-ant-...`, install.sh's `has_key` and `pnpm ready` read no key. Over the same file, `GET /api/health` answers `hasKey: true` and `checks brief --missing` takes its drafting branch, so the Postdoc screen hides its no-key callout.

- **Contract:** `core/openferment_core/models.py:4667-4668` (the `Health` description in `docs/api/openapi.json`), "whether it holds a key, so a page can say the service is up with no key to call a model with". `scripts/host/install.sh:54` names the placeholder state as keyless: "core/.env holds no key yet. The app runs; Postdoc and extraction wait for one."
- **Reproduce:** `bash bughunt/repro/H11-01/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** Every door reads the placeholder as no key: `has_key` false, ready's key row ✗, `checks brief --missing` printing "N check(s) without a brief; no key in core/.env, so they wait" (`scripts/host/nightly.sh:50-51`), and `hasKey` false, so the Postdoc screen shows "Postdoc is running without an API key".
- **Observed:** Both runs gave `has_key` no-key and the ready key row ✗ with "core/.env holds no key. Postdoc and extraction need one". Both runs gave `checks brief --missing` on its drafting branch (exit 0, no output, the run's database holding no check) and `GET /api/health` `hasKey=True`. The control with the key line emptied gave no-key, ✗, "0 check(s) without a brief; no key in core/.env, so they wait" and `hasKey=False`, so the placeholder alone makes the split.
- **Likely cause:** `core/openferment_core/api.py:488`: `hasKey=bool(os.environ.get("ANTHROPIC_API_KEY"))` and `checks.py:664` (`if not os.environ.get("ANTHROPIC_API_KEY"):`) test that the variable is set and non-empty, so they accept the placeholder. `ready.py:81` (`key == PLACEHOLDER_KEY`) and `scripts/host/lib.sh:92` refuse that placeholder. (confidence: high)
- **Fix size:** small: one shared placeholder test, ready's `check_key` rule, used at `api.py:488` and `checks.py:664`.
- **Stood on:** the first refutation.

#### H11-03 · S3 · Contract break · host scripts: ensure_database in scripts/host/lib.sh and install.sh

Run from a shell that exports `OPENFERMENT_DATABASE_URL`, over the runbook's step 1 `core/.env` with no database line, `scripts/host/install.sh` exits 0 and writes no database line into `core/.env`, so the service its LaunchDaemon starts reaches no database and answers `GET /api/projects` 503. install.sh's health wait and the two `pnpm ready` rows the reproduction ran (data and service) report ok.

- **Contract:** `scripts/host/lib.sh:122-124`, ensure_database's comment: "a database named `openferment`, and its address in core/.env. Makes what is missing and says what it made." The runbook says the same at `docs/runbooks/live-host-install.md:137-139`: "when no database is named in `core/.env`, checks for pgvector, makes the database `openferment` and names it there".
- **Reproduce:** `bash bughunt/repro/H11-03/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** With no database line in `core/.env`, install.sh names a database there, the live address or the value the shell exports. The service the LaunchDaemon starts then reads its database from `core/.env`, and `GET /api/projects` answers 200.
- **Observed:** In both runs install.sh exits 0 and says "OPENFERMENT_DATABASE_URL names the database." python-dotenv then reads `core/.env`'s database as `None`, and the server job's `EnvironmentVariables` are `HOME,PATH,PYTHONUNBUFFERED`. The job's service answers `GET /api/health` 200. It answers `GET /api/projects` 503 "OPENFERMENT_DATABASE_URL is not set. Put it in core/.env: ... on the live host scripts/host/install.sh writes it". From the install shell, ready's rows read "ok data: 0 projects, 0 review decisions, at revision 0010" and "ok service: answers on 127.0.0.1:9370". The control with nothing exported writes `postgresql://owner@127.0.0.1:5432/openferment` into `core/.env`. With the example's development address exported, the refusal says "Delete that line from core/.env and run this again" over a file holding 0 database lines.
- **Likely cause:** `scripts/host/lib.sh:147-153`: ensure_database sets `named="$(env_setting OPENFERMENT_DATABASE_URL)"`, `env_setting` (`lib.sh:106-110`) answers from the shell's environment first, and any value there takes the `?*)` branch, which echoes "names the database" and returns before line 163, the one line that writes `core/.env`; `scripts/host/launchd.py:71` gives the jobs `PATH`, `HOME` and `PYTHONUNBUFFERED` alone, so the service reads its database from `core/.env` alone (`core/openferment_core/api.py:178`). (confidence: high)
- **Fix size:** small: ensure_database decides from `core/.env`'s own line and writes the line when the file lacks one.
- **Stood on:** the first refutation.

#### H11-05 · S3 · Contract break · scripts/session-start.sh: its core/.env appends

`scripts/session-start.sh` appends `OPENFERMENT_DATABASE_URL` and `OPENFERMENT_WORKSPACE_ID` to `core/.env` with no leading newline, so over a `core/.env` whose last line lacks its newline the setting joins the key line: the key reads with the setting's text on its end, and the setting reads as unset.

- **Contract:** `scripts/session-start.sh:18-20`: "when PostgreSQL answers on 127.0.0.1 and core/.env names none, the development address (compose.yaml's) joins core/.env". The tree's own form for the same append is `scripts/host/lib.sh:162`, "On a line of its own, whether or not the file's last line ends in one.", held by `core/tests/test_host.py:243-257` over a key line with "no newline at the end".
- **Reproduce:** `bash bughunt/repro/H11-05/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** Each setting session-start adds lands on a line of its own. The key reads as `sk-ant-...`, the database as the development address, and with `OPENFERMENT_WORKSPACE_ID` set the workspace reads as the id the session named.
- **Observed:** Over `# hand-written\nANTHROPIC_API_KEY=sk-ant-...` with no final newline, session-start exits 0 in both runs, says "OPENFERMENT_DATABASE_URL added to core/.env (the development address)" and leaves the last line `ANTHROPIC_API_KEY=sk-ant-...OPENFERMENT_DATABASE_URL=postgresql://openferment:openferment@127.0.0.1:5432/openferment_dev`. python-dotenv and the service's loader read the key as `'sk-ant-...OPENFERMENT_DATABASE_URL=postgresql://openferment:openferment@127.0.0.1:5432/openferment_dev'` and the database as `None`, and `database_url()` raises "DatabaseUnavailable: OPENFERMENT_DATABASE_URL is not set". With `OPENFERMENT_WORKSPACE_ID=wrkspc_h11_placeholder` set the key reads `'sk-ant-...OPENFERMENT_WORKSPACE_ID=wrkspc_h11_placeholder'` and the workspace `None`, and a second run over the glued file appends the database line again on a line of its own with the key still glued.
- **Likely cause:** `scripts/session-start.sh:63` and `:48` append with `printf 'NAME=...\n' >> core/.env` and no leading `\n`, and the guards at `:62` and `:47` (`grep -q '^NAME='`) then miss the glued setting, so a second run appends again. `scripts/host/lib.sh:163` writes the same setting with `printf '\nOPENFERMENT_DATABASE_URL=...\n'`. (confidence: high)
- **Fix size:** small: a leading newline in the two `printf` lines, as `lib.sh:163` has.
- **Stood on:** the first refutation.

#### H11-06 · S3 · Contract break · scripts/session-start.sh: its database guard

`scripts/session-start.sh` tests whether `core/.env` names a database with `grep -q '^OPENFERMENT_DATABASE_URL='`, so a `core/.env` that names one as `export OPENFERMENT_DATABASE_URL=...` or `OPENFERMENT_DATABASE_URL = ...`, forms python-dotenv and `env_setting` both read, gains the development address on a later line, and the service then reads `openferment_dev`.

- **Contract:** `scripts/session-start.sh:18-20`: "when PostgreSQL answers on 127.0.0.1 and core/.env names none, the development address (compose.yaml's) joins core/.env". `scripts/host/lib.sh:97-99` writes what "names" means for this setting, "the file's last line for it, in the forms of python-dotenv these settings take: an `export` before the name, blanks around `=`", and `core/tests/test_host.py:195-196` holds it.
- **Reproduce:** `bash bughunt/repro/H11-06/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** A `core/.env` that names a database in a form python-dotenv reads stays as it is, and the service reads the same database after the session start as before it.
- **Observed:** For `export OPENFERMENT_DATABASE_URL=<url>` and for `OPENFERMENT_DATABASE_URL = <url>`, in both runs the service's reading names `bh_r_h11_06_named` and connects to it before the session start. The script then exits 0, prints "OPENFERMENT_DATABASE_URL added to core/.env (the development address)" and appends `OPENFERMENT_DATABASE_URL=postgresql://openferment:openferment@127.0.0.1:5432/openferment_dev`, after which the service's reading and `lib.sh`'s `env_setting` both name `openferment_dev` and the stand-in records `pnpm --silent db:migrate` as the next call. The control line `OPENFERMENT_DATABASE_URL=<url>` gains 0 lines and reads `bh_r_h11_06_named` after the run.
- **Likely cause:** `scripts/session-start.sh:62`: `! grep -q '^OPENFERMENT_DATABASE_URL=' core/.env` matches a line that starts with the name and `=`, so an `export` line or a line with blanks around `=` fails the match, and line 63 appends the development address, which python-dotenv takes as the file's last line for the name. `env_setting` at `scripts/host/lib.sh:111` matches all three forms with `^[[:space:]]*(export[[:space:]]+)?${name}[[:space:]]*=`. The workspace guard at `session-start.sh:47` has the shape of line 62. (confidence: high)
- **Fix size:** small: the guards at `session-start.sh:47` and `:62` take the pattern of `lib.sh:111`.
- **Stood on:** the first refutation.

#### H11-09 · S3 · Broken use · scripts/host/lib.sh REPO

`scripts/host/lib.sh:6` captures the output of a `cd` on a relative path, so with CDPATH exported with a `.` entry, `REPO` holds the checkout twice on two lines, and `install.sh`, `deploy.sh` and `nightly.sh`, typed from the checkout as the live-host runbook writes them, each stop at their first `cd`.

- **Contract:** `docs/runbooks/live-host-install.md:133`, step 3's command "scripts/host/install.sh", typed in the checkout that step 2 enters at `:113` with "cd ~/openferment"; and `:253`, "Bring the Mini to `main` and restart | `scripts/host/deploy.sh`".
- **Reproduce:** `bash bughunt/repro/H11-09/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** Typed from the checkout, the three scripts run the same with CDPATH exported as `.:$HOME` as with CDPATH unset: `REPO` is the checkout's one absolute path, and each script gets past its first `cd`.
- **Observed:** With CDPATH unset, `REPO` was the checkout, the run counted 0 cd failures, and `install.sh`, `deploy.sh` and `nightly.sh` each exited 0 on the stand-ins. With CDPATH `.:$HOME` exported, `REPO` was `$'<checkout>\n<checkout>'` and all 3 scripts exited 1 at their first cd: "scripts/host/install.sh: line 23: cd: $'<checkout>\n<checkout>': No such file or directory", the same words at `deploy.sh` line 17, and at `nightly.sh` line 18 with `$'<checkout>\n<checkout>/core'`.
- **Likely cause:** `scripts/host/lib.sh:6`: `REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"` runs `cd` on the relative path `scripts/host/../..`; bash's `cd` prints the new directory to stdout when a non-empty CDPATH entry resolves the path, and the command substitution keeps that line beside the line `pwd` prints. (confidence: high)
- **Fix size:** small: the one `REPO` line in `scripts/host/lib.sh`, written as `CDPATH= cd -- "..." >/dev/null && pwd`.
- **Stood on:** the second refutation, by the kind's own standard. The first set it aside because it read the runbook, the scripts' headers, CLAUDE.md and `core/tests/test_host.py` and found no line naming CDPATH or a person's shell settings.

#### H12-02 · S3 · Hollow test · engine/conform.py checks and their tests

Five one-line mutations of `core/openferment_core/engine/conform.py` each make one conformance check hold a break it exists to fail (check 1 ignoring that the engine was reached, check 3 ignoring a run that no row keeps, the reproduction's reading of the hunt's "a second row", check 4 ignoring the replay, check 5 ignoring an SFF file that fails validation, check 8 ignoring the row's `created_by`), and every suite test that reaches each mutated function stays green.

- **Contract:** `core/openferment_core/engine/conform.py:67-78`, the `CHECKS` table: 1 "a JSON number outside a quantity is refused in words before the worker is reached", 3 "a run writes one runs row keyed by its basis", 4 "a replay holds every output within the precision the thing states", 5 "the run's SFF file validates and scores, or sffRefused holds words", 8 "created_by on every run is the person or the model that asked for it"; and `docs/api/engines.md:479-481`, "an output that moves between two runs of one request, a clock reading among them, makes the replay differ and fails conformance check 4, and `pnpm prove` with it wherever the engine is installed".
- **Reproduce:** `bash bughunt/repro/H12-02/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** Under each mutation, at least one suite test that reaches the mutated function fails, as `core/tests/test_engines.py:571` (`test_a_check_that_fails_says_which_and_why`) does for check 2.
- **Observed:** Unmutated, the six test files gave 365 passed, 0 failed, and the five probes passed 5 of 5. Under M52 (check 1), M51 (check 3), M50 (check 4), M53 (check 5) and M54 (check 8), the suite tests reaching each function passed 15 of 15, 18 of 18, 15 of 15, 15 of 15 and 15 of 15, and each check's probe failed with the check holding its break, for example "outside the precision (rtol 0, atol 0); 1 difference" for check 4 and "record run-e067248c61c709e3: not valid, score 0.5" for check 5. The control mutation of check 2 failed 2 of 19 suite tests, `test_a_check_that_fails_says_which_and_why` among them.
- **Likely cause:** `core/tests/test_engines.py:491`: the suite reads checks 1, 3, 4, 5 and 8 through `assert all(c.ok for c in found)` on engines that conform (here and at `:514`, `:1002`, `:1726`, `:2046`, `:2743`, and `core/tests/test_engine_diagnostics.py:179`, `:300`), no test gives those checks an engine or a service that breaks them, and `test_engines.py:2047` asserts the substring `"valid, score 0.5"`, which "not valid, score 0.5" also contains. (confidence: high)
- **Fix size:** small: five negative tests in `core/tests/`, each an engine or a service that breaks one check (drafted in `bughunt/repro/H12-02/test_zz_h12_02_probe.py`), and a whole-word read of check 5's words at `test_engines.py:2047`; `conform.py` stays as it is.
- **Stood on:** the second refutation, by the kind's own standard. The first set it aside because it read `docs/api/engines.md:479-481` and the `CHECKS` table as statements of what conform decides, which the unmutated tree meets, and found no written line asking for a negative test of each check.

#### H12-03 · S3 · Hollow test · spend.py: the daily cap's lock and its tests

The day's advisory lock in `spend._reserve` (`core/openferment_core/spend.py:156`) can be deleted with every offline test green, because the race test R5c (`core/tests/test_phase3_review.py:97-117`) runs its ten threads one after another on the test binding's one connection; the verdict confirmed this part and found that R5c fails when check and hold are split into two sessions.

- **Contract:** `core/openferment_core/spend.py:175-177`, `reserve`'s docstring: "Check and hold are one step under the day's lock, so two calls at once cannot each see room that only one of them has (§3.R)." The race test names that property at `core/tests/test_phase3_review.py:96`, "R5c — check and charge are one step: concurrent calls cannot each pass.", under its module's "Each test failed before its fix." (`:1-2`).
- **Reproduce:** `bash bughunt/repro/H12-03/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** Once the lock goes from `_reserve`, a test fails: R5c, which races ten threads asking $0.30 each against a $1.00 cap and asserts three are granted, or another test with reservations on separate connections.
- **Observed:** At the head the probe (two threads behind a barrier, each asking $0.60 against a $1.00 cap on a connection of its own) held both reservations in 0 of 20 rounds, the most held at once $0.60, and `test_spend.py`, `test_phase3_review.py`, `test_llm.py` and `test_ready.py` gave 175 passed. With the one line `await db.lock(s, "spend", day.isoformat())` deleted, the probe held both in 20 of 20 rounds in each run, the most held at once $1.20, and the four files again gave 175 passed with `test_concurrent_reservations_cannot_together_pass_the_cap` PASSED.
- **Likely cause:** `core/openferment_core/db/session.py:99`: `async with binding.turn:` makes every session wait its turn on one asyncio lock over the one connection that the autouse `Binding` of `core/tests/conftest.py:234-235` sets, so R5c's ten threads reserve one after another whatever `_reserve` does, and the advisory lock at `spend.py:156` decides nothing in any offline test. (confidence: high)
- **Fix size:** small: one test that points `spend._ENGINE` at an engine of its own on the test database, as `conftest.py:47-48` does for live tests, races threads through `spend.reserve` behind a barrier, asserts the cap holds, and deletes the day's committed rows after.
- **Stood on:** the first refutation.

#### H12-04 · S3 · Hollow test · request guard (core/openferment_core/guard.py, core/tests/test_request_guard.py)

With `answers_to(hostname(forwarded))` deleted from `guard.refusal` at `core/openferment_core/guard.py:133`, a POST whose Host is a proxy's loopback address and whose Origin and X-Forwarded-Host name a hostile site gets through and writes a project, and `test_request_guard.py`, `test_key_override.py` and `test_projects.py` all stay green.

- **Contract:** `CLAUDE.md:52`, "the loopback bind and `core/openferment_core/guard.py` are the access control until accounts exist"; and `core/tests/test_request_guard.py:1-4`, the guard's own test file, "Only the owner's own pages may change anything" and "a changing request blocked by the guard comes back 403 with the reason".
- **Reproduce:** `bash bughunt/repro/H12-04/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** With the check at `guard.py:133` deleted, a test in the guard's suite fails, because it holds a POST with Host `127.0.0.1:8000`, Origin `http://rebind.evil.example.com` and X-Forwarded-Host `rebind.evil.example.com` to 403. That request is the DNS-rebinding request of `guard.py:10-12` as a proxy that rewrites Host passes it on (`guard.py:124-125`, `test_request_guard.py:99-103`).
- **Observed:** At the head, in both runs, that POST to `/api/projects` answered 403 with "a page on 'http://rebind.evil.example.com' may not change anything here" and made no project. With the one-line mutation, `guard.refusal` returned None, the POST answered 201 and the project `rebound-write` was written to the fresh database. The three test files gave 58 passed at the head and with the mutation in both runs (4.19 s and 4.24 s in run 1, 4.23 s and 4.45 s in run 2).
- **Likely cause:** `core/tests/test_request_guard.py:70-77` sends a hostile Host with a loopback X-Forwarded-Host, which the Host check at `core/openferment_core/guard.py:115-120` refuses before line 133 is reached, and every other case with X-Forwarded-Host (`test_request_guard.py:87`, `:91`, `:97`, `:102`) is one the guard lets through, so no test sends a loopback Host with a hostile forwarded name. (confidence: high)
- **Fix size:** small: one refused case in `core/tests/test_request_guard.py` with Host `127.0.0.1:8000`, Origin `http://rebind.evil.example.com` and X-Forwarded-Host `rebind.evil.example.com`, expecting 403.
- **Stood on:** the first refutation.

#### H12-05 · S3 · Hollow test · core/tests/test_no_seed.py

`core/tests/test_no_seed.py`, the test CLAUDE.md names as the hold on typed science, passes with a service module typing a titre, a yield, a composition and a price and with a `src/data/` file exporting a yield table by strain, and `test_boundaries.py` and `test_guidance.py` pass beside it.

- **Contract:** `CLAUDE.md:11`, "R: The repository holds software alone: no composition, yield, price, titre, strain fact or paper's finding is typed in code or seed, and science arrives at run time through Intake and the library plants (§1 item 7; `core/tests/test_no_seed.py`, acceptance A4)."; and `docs/PROGRESS.md:510`, "`test_no_seed.py` holds what A4 names (each deleted module absent, no `.ts` under `src/data/` exporting content, the shipped stores empty)".
- **Reproduce:** `bash bughunt/repro/H12-05/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** `test_no_seed.py` fails on the planted service module and on the `src/data/` file exporting a yield table by strain, as it fails on a control file exporting `RECORDS`.
- **Observed:** In both runs the baseline gave 47 passed, and the control (`src/data/control.ts` exporting `RECORDS`) gave 1 failed, 46 passed, with "AssertionError: ['src/data/control.ts: RECORDS']". With `core/openferment_core/typical_values.py` (`ETHANOL_TITRE_G_PER_L = 92.0`, `ETHANOL_YIELD_G_PER_G = 0.48`, `CORN_STOVER_GLUCAN_FRACTION = 0.35`, `ENZYME_PRICE_USD_PER_KG = 4.24`) and `src/data/yields.ts` (`export const TYPICAL_YIELDS`) planted, `test_no_seed.py` exited 0 with 47 passed, and with `test_boundaries.py` and `test_guidance.py` beside it exited 0 with 69 passed.
- **Likely cause:** `core/tests/test_no_seed.py:101`: `if SEEDED_NAMES.match(name) or typed:` fails a `src/data/` export in two cases, a name matching the seed's names (`:77`, `RECORDS|PAPERS|PRODUCTS|STRAINS|...`) or an annotation naming a seed type (`:75`), so an untyped export named `TYPICAL_YIELDS` passes; the one scan across the service and `src/` (`:116-124`) reads the alpha 1.0 record id pattern (`:80`), and no test reads typed numbers across `core/openferment_core/` or `src/`. (confidence: high)
- **Fix size:** medium: a scan of typed numbers beside science words across `core/openferment_core/` and `src/`, with an allowance for what `CLAUDE.md:12` counts as software (versions, ports, tolerances, unit-conversion factors, file hashes, the library's own regression values).
- **Severity:** S3, the reading of the refuting agent and of the entry's writer. An independent severity panel read S4: The planted titre, yield, glucan fraction, price and strain yield table passed test_no_seed.py (47 passed) and its two neighbours (69 passed), and nothing in the repro reads them, so no screen, answer, record or export shows a number.
- **Stood on:** the second refutation, by the kind's own standard. The first set it aside because it read the test's docstring (`core/tests/test_no_seed.py:1-8`) and the A4 row (`docs/PROGRESS.md:510`) as scoping the test to the stage 1 deletion, with the clause on the service's code left to the `rg` measured once by hand at stage 8.

#### H12-06 · S3 · Hollow test · worker boundary tests (core/tests/test_workers.py, core/tests/test_boundaries.py)

No test holds biorefineries out of the service process: a function-level `import biorefineries` planted in the service function `proforma.retired_entry_of` (`core/openferment_core/proforma.py:145`) passes `test_workers.py`, `test_boundaries.py`, `test_proforma.py`, `test_proforma_runs.py` and `test_engines.py`, and leaves biorefineries loaded in the service's process.

- **Contract:** `CLAUDE.md:41`, "BioSTEAM, thermosteam, biorefineries, the vendored SFF toolkit and cobra run in worker processes (`core/openferment_core/workers/`), one JSON request a line; the service process imports none of them (§7.1; `core/tests/test_boundaries.py`)"; and `core/tests/test_boundaries.py:16-19`, the test the rule names, "BioSTEAM, thermosteam and biorefineries: the worker's side alone (workers/, flowsheets/, the vendored SFF toolkit and the pureOS functions that run in the worker; test_workers.py names each file)".
- **Reproduce:** `bash bughunt/repro/H12-06/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** A service module that imports biorefineries fails a boundary test, as an `import biosteam` at the same line fails `test_workers.py`'s grep, and the service process holds none of the worker libraries.
- **Observed:** In both runs the control, an `import biosteam` at that line, failed `test_workers.py -k heavy_libraries` with "biosteam is imported outside its worker: ['proforma.py']". With the planted `import biorefineries` the five files exited 0 with "198 passed, 6 deselected" (49.74 s in run 1, 50.98 s in run 2). The probe listed the worker libraries in the service process after `retired_entry_of` as `[]` at the head and `['biorefineries']` on the planted tree.
- **Likely cause:** `core/tests/test_workers.py:133-157`: `ALLOWED`, which drives the grep `test_heavy_libraries_are_imported_in_their_worker_alone` (`test_workers.py:162-176`), has rows for cobra, biosteam, thermosteam, scipy and pisces_sff and none for biorefineries (both runs read it as `['biosteam', 'cobra', 'pisces_sff', 'scipy', 'thermosteam']`), and `core/tests/test_boundaries.py:44-50` holds `SIMULATION` away from `db/`, `projects/`, `literature/`, `engine/` and `studies/` alone, so a top-level service module such as `proforma.py` or `api.py` falls under neither test. (confidence: high)
- **Fix size:** small: a `"biorefineries"` row in `ALLOWED` in `core/tests/test_workers.py` naming `workers/library_plants.py` and `workers/kept_references.py`, the two worker modules that import it today, with `flowsheets/` skipped as the biosteam row skips it.
- **Severity:** S3, the reading of the refuting agent and of the entry's writer. An independent severity panel read S4: The planted `import biorefineries` passed the five files (198 passed) and left biorefineries in the service's sys.modules after `retired_entry_of`.
- **Stood on:** the first refutation.

#### H12-11 · S3 · Hollow test · ready.check_literature

The one test of `pnpm ready`'s literature row runs on a kit schema at its head, so a break of the row's revision check (`at != head` dropped from `ready.py:206`, mutation M65) leaves `test_ready.py`, `test_db.py` and `test_import_alpha1.py` green, and the broken row then reads ok on a kit schema one revision behind.

- **Contract:** `core/openferment_core/ready.py:160-161`, "Sci RAG Kit's side of the database, as its own `sci-rag doctor` sees it: the vector extension, the kit's schema at its newest revision"; `CLAUDE.md:29`, "`pnpm ready` (or `pnpm ready --offline`) says in rows whether the service can run: the database, both schemas, pgvector".
- **Reproduce:** `bash bughunt/repro/H12-11/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** A test holds the literature row to the kit's revision, as `test_data_reports_a_database_behind_the_newest_schema` holds the data row, so the three files turn red with M65 applied.
- **Observed:** On a fresh database with `sci_rag` taken back to 0005 of 0006, the row as the tree stands answers "fail | Sci RAG Kit's schema is at revision 0005 of 0006. Run: pnpm db:migrate". With M65 it answers, on the same database, "ok | pgvector 0.6.0, revision 0006, 0 documents, 0 chunks". With M65 the three files give "95 passed" in both runs (12.34 s and 18.69 s). The control M64 on the data row gives "1 failed, 64 passed" in both runs, the failure being `test_data_reports_a_database_behind_the_newest_schema`.
- **Likely cause:** `core/tests/test_ready.py:398-401`: `test_the_literature_row_reads_the_kits_schema` is the one caller of `check_literature`, it runs on the session database at head, and its check `"revision 0006" in check.detail` reads the head that the ok summary prints (`ready.py:217`), so the `at != head` half of `ready.py:206` stands untested; a 0005 schema keeps the vector column, so the `width is None` half passes it. (confidence: high)
- **Fix size:** small: one test in `test_ready.py` that migrates a database, takes `sci_rag` back one revision and asserts the literature row fails with "pnpm db:migrate" in its words.
- **Stood on:** the second refutation, by the kind's own standard. The first set it aside because it read `ready.py:160-161` and `CLAUDE.md:29` as describing what the unmutated row does today, and found no written rule asking each ready row for a negative test.

#### H13-01 · S3 · Broken use · first run: README.md Run it, scripts/session-start.sh, scripts/prototype-up.sh

On a fresh clone with no key and no `core/.env`, README's Run it block leaves the app with no database: `pnpm db:migrate` refuses for want of `OPENFERMENT_DATABASE_URL`, and `pnpm prototype:up` runs `scripts/session-start.sh`, whose database step writes the development address into `core/.env` when that file already exists, so the service reports health ok and Home's `GET` and `POST /api/projects` answer 503.

- **Contract:** `scripts/session-start.sh:18-20`, "4. the database (ADR-001): when PostgreSQL answers on 127.0.0.1 and core/.env names none, the development address (compose.yaml's) joins core/.env; then pnpm db:migrate, whatever it exits with"; `README.md:46-47`, "Without a key the app runs whole, and the steps that need a model say so."
- **Reproduce:** `bash bughunt/repro/H13-01/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** With PostgreSQL answering on 127.0.0.1 and no `core/.env`, session-start's database step writes the development address and `db:migrate` migrates it. The keyless app then lists and makes projects, as the control service over a named database does.
- **Observed:** README line 41's `db:migrate` exits 2 with "refused: OPENFERMENT_DATABASE_URL is not set. Put it in core/.env: ...", and `session-start.sh` run keyless leaves `core/.env` absent with 0 address lines. With a placeholder key line in `core/.env` the same step prints "OPENFERMENT_DATABASE_URL added to core/.env (the development address)" and writes 1 line. The service as `prototype-up.sh` starts it answers `GET /api/health` `{"ok":true,...,"hasKey":false}`, `GET /` 200, and `GET` and `POST /api/projects` 503 with the detail "OPENFERMENT_DATABASE_URL is not set. Put it in core/.env: ...". The control service over a fresh database named in `OPENFERMENT_DATABASE_URL` answers `POST /api/projects` 201 and `GET /api/projects` 200, in both runs.
- **Likely cause:** `scripts/session-start.sh:62`: the guard `if [ -e core/.env ] && ! grep -q '^OPENFERMENT_DATABASE_URL=' core/.env && ...` skips the write when the file is absent, and step 1 (lines 28-43) makes `core/.env` from `OPENFERMENT_API_KEY` alone; `core/openferment_core/api.py:467-489` then reports `ok=True` with no database, so the health wait at `scripts/prototype-up.sh:51-56` passes. (confidence: high)
- **Fix size:** small: the database step makes `core/.env` (mode 600, checked as ignored by git) when it is absent, and step 1 appends the key line to a `core/.env` that lacks one, so a later run with a key writes it into that file.
- **Stood on:** the second refutation, by the kind's own standard. The first set it aside because it read `session-start.sh:18-20` as appending to a present `core/.env`, as the workspace-id step at lines 44-50 does, and read `core/.env.example` and `compose.yaml`'s header as leaving the address to the person.

#### H14-04 · S3 · Inconsistency · BioRepo Witness (src/screens/Witness.tsx)

With no value a reviewer typed and one rejected candidate, the Witness screen's headline tile shows PRECISION 0.0% on the gold tick "Gold · a value a reviewer typed" directly beneath its own callout "Precision and recall are undefined without a gold set"; the refutation pass confirmed the defect in the tile, its gold tick and the metrics CSV, and found the service's count of one false positive correct by `core/openferment_core/witness.py:27-28`.

- **Contract:** `src/screens/Witness.tsx:573-576`, the callout drawn when `metrics.goldSize === 0`, "No gold annotations yet" and "Precision and recall are undefined without a gold set. Flag records for gold in the review queue and this screen fills in."; and `src/components/Provenance.tsx:18`, the gold tick's label, "Gold · a value a reviewer typed".
- **Reproduce:** `bash bughunt/repro/H14-04/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** With `goldSize` 0 and `results` empty, the precision tile reads "—", undefined, as the recall tile does, in agreement with the callout above it.
- **Observed:** In both runs, after two candidates were accepted as written and one rejected, `GET /api/witness/runs` returned run `claude-1` with 0 results and 1 false positive. The screen showed the callout "No gold annotations yet / Precision and recall are undefined without a gold set. Flag records for gold in the review queue and this screen fills in.", the precision tile "0.0%" with class `tick-gold` and the label "Gold · a value a reviewer typed.", the recall tile "—", and the counts "tp 0 · fp 1 · fn 0".
- **Likely cause:** `src/screens/Witness.tsx:480` sets `precisionDefined = metrics.micro.tp + metrics.micro.fp > 0`, which one rejection makes true with `goldSize` at 0 (the callout tests `metrics.goldSize === 0` at line 569), so `src/engine/metrics.ts:28` gives 0/(0+1) = 0 for the tile, `Witness.tsx:490` marks it gold for `claude-1` at any gold-set size, and the metrics CSV at `Witness.tsx:379` makes the same `tp + fp > 0` test and, read from the code, writes 0.0000 for this state. (confidence: high)
- **Fix size:** small: the precision tile, its delta and the CSV row in `src/screens/Witness.tsx` count precision as defined once the gold set holds a value (`goldSize > 0`), as the callout does.
- **Stood on:** the first refutation.

#### H14-07 · S3 · Wrong number · Deposition bench capture (src/engine/capture.ts, DepositionPanel)

The bench's capture box drops every comma before it reads a number, so "titre came in at 7,4 g/L", said with a decimal comma, is previewed and filed as 74 g/L, "0,74 g/L" files as 74 g/L too, and a person who presses "That is right" keeps a confirmed measurement ten or a hundred times the value said.

- **Contract:** `src/engine/capture.ts:9-13`, "So matching is deliberately conservative: when in doubt this returns null and the text is kept verbatim as an Observation. A false negative costs a person one reclassification later; a false positive silently writes a number into a slot it does not belong in and the reconciliation is quietly wrong."; `src/components/DepositionPanel.tsx:80-81`, "Say it however you say it. Anything that matches the plan is filed as a measurement; everything else is kept word for word."
- **Reproduce:** `bash bughunt/repro/H14-07/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** The line "titre came in at 7,4 g/L" is kept as an observation, as a doubtful line is, or is filed as 7.4 g/L. A decimal comma reads "7,4" as 7.4 and "0,74" as 0.74, and a thousands group holds three digits.
- **Observed:** In both runs `matchToSchema` over a g/L measure labelled "Ethanol titre" gives 7.4 for "titre came in at 7.4 g/L" (the control), 74 for "titre came in at 7,4 g/L" with read-back text "74 g/L", 74 for "titre came in at 0,74 g/L" and 1250 for "titre came in at 1,250 g/L". The built bundle `dist/assets/index--9-JuXoK.js` carries the same comma strip, and the panel files its preview through `capture(deposition.id, stepId, raw, preview)` (`src/components/DepositionPanel.tsx:65`) into an entry holding `value: match.value` (`src/store.ts:2136`).
- **Likely cause:** `src/engine/capture.ts:28`: `normalise()` runs `.replace(/[,]/g, '')` over the whole line before the number regex `/(-?\d+(?:\.\d+)?)/g` at line 100, so "7,4" reaches the regex as "74" and "0,74" as "074". (confidence: high)
- **Fix size:** small: `normalise` keeps a comma between digits as a thousands separator when exactly three digits follow it, and `matchToSchema` returns null, keeping the line as an observation, for any other comma between digits.
- **Severity:** S3, the reading of the refuting agent and of the entry's writer. An independent severity panel read S1: For "titre came in at 7,4 g/L" the capture box previews "files as Ethanol titre = 74 g/L" (and 74 for "0,74 g/L") with no doubt marked on the parse, the read-back sets 74 g/L above the words said, and a press of "That is right" keeps 74 g/L as a confirmed measurement a scenario's measurement origin may name.
- **Stood on:** the second refutation, by the kind's own standard. The first set it aside because it read `capture.ts:9-13` as the rule for which measure a line lands in, and read `normalise`'s docstring at `capture.ts:24` as dropping commas on purpose.

#### H2-02 · S3 · Contract break · runs/replay (proforma.run; POST /api/biorepo/artifacts/{id}/replay; nightly checks)

A `proforma.run` artifact of `ethanol_glucose_v0`, kept by a worker that built the corn stover library plant before the scenario plant, replays identically in that worker. After the service restarts, it replays with nine last-digit differences, so the replay answers `identical` false and `withinTolerance` false against the `rtol` 0, `atol` 0 the biosteam engine states for the flowsheet. The reproduction and the refutation pass narrowed the claim to this run order. A run kept in a fresh worker replays identically after a restart.

- **Contract:** `docs/api/engines.md:616-618`, "A scenario flowsheet's is `rtol` 0, `atol` 0: `proforma.run` registers no tolerance, so its replay holds every output identically."; and `docs/api/engines.md:466-468`, "Every output is a function of the request alone: the same request gives the same outputs, in the same order, within the precision the thing states".
- **Reproduce:** `bash bughunt/repro/H2-02/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** Each replay answers `identical` true, since the same request gives the same outputs whatever the worker built before, within the `{rtol 0.0, atol 0.0}` the engine states for `ethanol_glucose_v0`. Or the thing states the precision its outputs keep, as a library thing states ten digits.
- **Observed:** In both runs `GET /api/engines` listed `ethanol_glucose_v0` with precision `{'rtol': 0.0, 'atol': 0.0}`, and artifact `1b467e933631368e`, kept after the cornstover library run `bfda026530692adc`, replayed in the same worker with `identical` True and 0 differences. After the service restarted over the same database it replayed with `identical` False, `withinTolerance` False, `tolerance` None and 9 differences: `tea.FCI` stored 21777995.078954738 and replayed 21777995.078954734 (relative 1.7e-16), and `tea.TCI`, `tea.installedEquipmentCost`, `tea.lines[2].perUnit`, `tea.lines[2].usdPerYear`, `tea.purchaseCost`, `tea.utilityCost`, `utilities.electricityConsumption` and `utilities.heating`, each a relative 1.3e-16 to 2.1e-16.
- **Likely cause:** `core/openferment_core/workers/proforma_worker.py:197-198` builds the scenario plant inside `package_defaults()`, and the build picks up last-digit state from the corn stover plant the worker built first (the summation-order drift for which `core/openferment_core/engine/library.py:68-74` rounds library runs to `DIGITS = 10`); `core/openferment_core/proforma.py:808-809` registers `proforma.run` with no `tolerance_of`, so its output keeps every digit, and `proforma.py:1521` states `EnginePrecision(rtol=0.0, atol=0.0)` for it. (confidence: medium)
- **Fix size:** medium: the scenario build in `core/openferment_core/workers/proforma_worker.py` made free of what the worker built before, or `proforma.run` given a stated precision and a replay tolerance in `core/openferment_core/proforma.py`, with `docs/api/engines.md:616-618` and `docs/api/runs.md:229-231` to match, as a library run keeps ten digits.
- **Stood on:** the first refutation.

#### H2-06 · S3 · Inconsistency · library routes: GET /api/library/{plant}/regression and the reference page /proforma/reference/:plant

For a plant that takes configurations, `GET /api/library/{plant}/regression` naming no configuration answers `null`, so before a run the reference page for oilcane tells a person that `test_oilcane_S1`, the test a run of oilcane naming no configuration is held to, "was not found in the installed package".

- **Contract:** `core/openferment_core/api.py:1312-1313`, "The values the package's own test for this plant asserts, read from the installed file; null when it has none."; and `src/screens/ProformaReference.tsx:24`, the page's read of that route, "the package test's values, before a run".
- **Reproduce:** `bash bughunt/repro/H2-06/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** The read naming no configuration answers the package test of the configuration a run naming none takes, as the parameters route does: for oilcane, `test_oilcane_S1` in its default `S1`. Before a run, the reference page sets out that test's values.
- **Observed:** In both runs `GET /api/engines` named `S1` as oilcane's default, and `GET /api/library/oilcane/regression` answered `200 null`. In both runs `GET /api/library/oilcane/regression?configuration=S1` answered `200` with `test_oilcane_S1` and 11 values. Before any run the page's header read "Held to biorefineries/tests/test_biorefineries.py::test_oilcane_S1 · in its default configuration, S1" and its card read "The service read no package test for this plant (test_oilcane_S1 was not found in the installed package)." `POST /api/library/oilcane/run` naming no configuration then answered `200` with configuration `S1`, status `done`, `outputs.regression` `{"within": 11, "of": 11}`, and its artifact held to `test_oilcane_S1` with 11 of 11 checks within.
- **Likely cause:** `core/openferment_core/api.py:1315` passes the configuration as asked to `_library.regression`, and with `None` `library.package_test` (`core/openferment_core/engine/library.py:148-154`) looks for `test_oilcane`, which the installed test file lacks, and answers `None`. The parameters route resolves the configuration first through `default_configuration` (`api.py:1303`, `core/openferment_core/engine/biosteam.py:160`). The client asks the regression route with no configuration (`src/lib/proforma.ts:113-114`), and the page words the null as the test missing from the package (`src/screens/ProformaReference.tsx:116-121`, the name from `:339`). (confidence: high)
- **Fix size:** small: `library_regression` in `api.py` resolves the configuration through `default_configuration`, as `library_parameters` does, with a test pinning the route's answer for a configured plant.
- **Stood on:** the first refutation.

#### H3-05 · S3 · Broken use · the bench's corrections and sample times (measurements.corrected_by, TimeSeriesPanel)

On the bench's own path of correcting a reading and then typing hours in an open deposition's Time series panel, a write that gives the correction an hour of its own, or moves either row's hour, makes the corrected mis-read stand again, and the readings list and the lookup take it as a confirmed measurement; the second refutation upheld the claim as a broken use of that path.

- **Contract:** `docs/decisions/ADR-006-quantities-and-estimates.md:238`, "A run looks its readings up again each time it runs, and refuses in words one corrected since."; `src/engine/readings.ts:5-7`, "a reading in a series (an entry with a sample time) is corrected by a later entry at its own time alone, as the bench's correction carries the time across (store `amendEntry`)".
- **Reproduce:** `bash bughunt/repro/H3-05/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** A reading the person corrected at the bench stays corrected as they give or fix the deposition's hours. The resolve on the mis-read stays a 422 naming its correction and the readings list leaves the mis-read out, or the write that splits the pair is refused in words.
- **Observed:** Untimed pair, both runs: the resolve on `dep10/s1` (4.0 g/L, corrected by `dep10/s2` 40.0 g/L) is a 422, "titre: reading dep10/s1 was corrected by dep10/s2, the reading that stands for its measure now"; the write giving s2 alone 5 h is a 200, and the resolve on `dep10/s1` is then a 200 setting the titre to (4.0, 'measurement', 'deposition', 'dep10/s1'), with the readings list offering [('dep10/s1', 4.0, None), ('dep10/s2', 40.0, 5.0)]. Timed pair: with both rows at 5 h the resolve on `dep9/s1` is a 422 and the list offers [('dep9/s2', 40.0, 5.0)]; the write moving s2 to 6 h is a 200, and the resolve on `dep9/s1` is then a 200 setting (4.0, 'measurement', 'deposition', 'dep9/s1'), with the list offering [('dep9/s1', 4.0, 5.0), ('dep9/s2', 40.0, 6.0)].
- **Likely cause:** `core/openferment_core/measurements.py:101-103`: `corrected_by` finds a correction as a later entry on the same measure whose current sample time equals the entry's (`times.get(e.get("id")) == when`), so the hour is the one tie between a correction and its reading; `project_state.py:325` holds `sampleTimes` once the deposition is closed, which leaves `setSampleTime` (`src/store.ts:2194-2204`) free to set one row's hour from the panel's box (`src/components/TimeSeriesPanel.tsx:76-82`) during the run. (confidence: high)
- **Fix size:** small: `setSampleTime` and `deposition_refusal` move a correction's hour together with its reading's hour, in the panel and on the service.
- **Severity:** S3, the reading of the refuting agent and of the entry's writer. An independent severity panel read S1: After a write that gives the correction an hour of its own, the readings list offers the corrected mis-read 4.0 g/L as a standing reading and the resolve sets a scenario's titre to 4.0 g/L with origin `measurement`, the label of a confirmed bench reading, with nothing saying the person corrected it to 40.0 g/L.
- **Stood on:** the second refutation, by the kind's own standard. The first set it aside because it read ADR-006:174-177 and `docs/api/studies.md:58` as defining a correction by the current sample time, and ADR-006:236 as letting an open deposition's hours change.

#### H3-07 · S3 · Wrong number · units.normalize (core/openferment_core/units.py, src/engine/units.ts)

`units.normalize` lower-cases a spelling for its alias lookup and then compares it case-blind against every table key, so a spelling whose letter case carries the SI prefix or unit symbol lands on another unit: `Mg` and `MG` (megagram) read as `mg`, `ML` (megalitre) as `mL`, `Mm` and `MM` as `mmol L⁻¹`, `S` as `s` and `G` as `g`, and `convert(1, 'Mg', 'kg')` answers `1e-06`, a factor of 10⁹ below the SI value of 1000, in the service and in `src/engine/units.ts` alike.

- **Contract:** `core/openferment_core/units.py:24-27`, "An unknown unit is `UnitError`" and "Nothing here invents a conversion factor."
- **Reproduce:** `bash bughunt/repro/H3-07/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** A spelling whose letter case names a unit the table holds no key for (`Mg`, `MG`, `ML`, `Mm`, `MM`, `S`, `G`) raises `UnitError` ("Unknown unit"), as `Mg/d` does, and the lesson door answers 422 to a 2 Mg answer, as it does to 2 Mg/d.
- **Observed:** Seven of seven probes folded onto another unit (`Mg` and `MG` to `'mg'`, `ML` to `'mL'`, `Mm` and `MM` to `'mmol L⁻¹'`, `S` to `'s'`, `G` to `'g'`), `convert(1, 'Mg', 'kg')` gave `1e-06`, `convert(2, 'Mg', 'g')` gave `0.002` and `convert(1, 'ML', 'L')` gave `0.001`. `convert(1, 'Mg/d', 'kg d⁻¹')` raised "Unknown unit: Mg/d". `POST /api/catalogues/lesson` kept a numeric answer of 2 Mg (HTTP 200, unit `'Mg'` read back). The same route refused 2 Mg/d (HTTP 422). The browser's `normalizeUnit` folded the same seven probes to the same keys. The Primer's grading call marked "2000 kg" wrong against the 2 Mg answer. It marked "2 mg" correct against the same answer.
- **Likely cause:** `core/openferment_core/units.py:135-143`: line 135 lower-cases the spelling, line 138 then reaches the lower-case aliases `"ml"` and `"mm"` (`schema/units.json:511`, `:506`), and lines 140-143 compare `_strip(t)` with `_strip(key)` for every key, with `_strip` ending in `.lower()` (line 117), so an upper-case SI prefix or unit symbol meets the lower-case key; `src/engine/units.ts:377-379` and `:384-389` run the same steps (confidence: high).
- **Fix size:** small, the two normalize functions (`units.py`, `src/engine/units.ts`) and fixture pairs in `scripts/export-unit-fixtures.ts` for `Mg`, `ML`, `Mm`, `S` and `G`.
- **Stood on:** the second refutation, by the kind's own standard. The first set it aside because it read normalize's docstring at `core/openferment_core/units.py:124-125`, "a superscript-blind, middot-blind, case-blind comparison against every key", as making `Mg` a known spelling.

#### H3-09 · S3 · Wrong number · schema/units.json, the percent family

The unit table files `%`, `% DW`, `% v/v`, `% of native sites`, `% sedimentable`, `% of total expressed` and `% of total protein` in one family, `percent`, each at factor 1, so `units.convert` turns a share of dry weight, a volume fraction and a share of total protein into each other 1:1, and a 42 % DW quote anchors for `disruption_protein_yield`, is stored `verified` and reads back as 42 % of total protein; this entry leaves out the `wt%` alias the hunt also named, which `docs/PROGRESS.md:614` records as an open debt.

- **Contract:** `core/openferment_core/schema/units.json:558`, "Both are percentages ... of different denominators" and "Comparing them directly is a category error."; `core/openferment_core/units.py:26-27`, "Nothing here invents a conversion factor."
- **Reproduce:** `bash bughunt/repro/H3-09/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** Two percentages of different denominators raise `UnitError` with a reason, as `% TSP` against `% DW` does, and anchoring refuses 42 `% DW`, 42 `% v/v` and 42 `% of native sites` on rule `unit` for `disruption_protein_yield`, whose canonical unit is `'% of total protein'`.
- **Observed:** The control `convert(5, '% TSP', '% DW')` raised `UnitError` with the reason of `units.json:558`. Six of six pairs inside `percent` returned `5.0` with `explain_refusal` None (among them `% DW` to `% of native sites`, `% v/v` to `% DW` and `% DW` to `% of total protein`), and `quantity_equals((5, '% DW'), (5, '% of native sites'))` was True. `disruption_protein_yield` anchored 42 in `'% DW'`, `'% v/v'` and `'% of native sites'` with `valueBasis 'exact'`. Anchoring for the same field refused 42 `'% TSP'` on rule `unit`. `biorepo.write` stored the accept as `cl1-R1-00000002 | disruption_protein_yield | 42 | % DW | verified`, `to_canonical(42.0, '% DW', 'disruption_protein_yield')` returned `42.0`, and the browser's `convert` gave 5 for six of six pairs.
- **Likely cause:** `core/openferment_core/schema/units.json:123-137` and `:286-305` give each of these units `"family": "percent"` and `"factor": 1`. `units.convert` raises when the two families differ (`core/openferment_core/units.py:198-202`). Within one family it applies the table's factors (`:203-204`). The one refusal row on the boundary (`units.json:555-559`) names `proteinShare` and `percent`; `src/engine/units.ts:51-53` and `:87-90` hold the same rows (confidence: high).
- **Fix size:** small, a family for each denominator in `schema/units.json` and `src/engine/units.ts`, refusal rows in the words of `:558`, and a fixture pair for each.
- **Severity:** S3, the reading of the refuting agent and of the entry's writer. An independent severity panel read S1: A quote's 42 % DW anchors for `disruption_protein_yield`, is kept with provenance `verified`, and `to_canonical` reads it as 42 % of total protein, the conversion `runbook_draft._from_records` applies to make a prediction from that record.
- **Stood on:** the second refutation, by the kind's own standard. The first set it aside because it read the refusal row at `core/openferment_core/schema/units.json:555-559` as guarding the `proteinShare` / `percent` boundary alone, with `units.py:247-248` making family membership the test of a field's unit.

#### H3-14 · S3 · Inconsistency · src/screens/DepositionDetail.tsx, the Released to BioRepo band

After a reconciliation, the deposition screen's "Released to BioRepo" band draws every released value under the badge "Measured · first-party" with a `tick-measured` tick, the value nobody read back included. The runbooks module read marks that same row `unverified`.

- **Contract:** `docs/decisions/ADR-006-quantities-and-estimates.md:21-22`, "Provenance is computed from origins by code (`basis_provenance`, `weakest_provenance`, the client's display of the server's answer)"; `docs/decisions/ADR-006-quantities-and-estimates.md:242-243`, "the measured evidence a reconciliation released (kind `measured-evidence`, marked `unverified` where nobody read its number back)".
- **Reproduce:** `bash bughunt/repro/H3-14/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** The band draws each released value in the class the service computes for it, as `runbooks_read` answers. It draws the value a person read back as `measured`. It draws the value nobody read back as `unverified`.
- **Observed:** In each run the screen's own "Record as inconclusive" button released two values, both kept with `provenance=measured`. `runbooks_read` answered `provenance=measured confirmed=true` for the read-back one. It answered `provenance=unverified confirmed=false` for the unread one (`me-mwbbwt3s-2` in run 1, `me-mwbbx2zi-2` in run 2). The band drew the badge "Measured · first-party", and the unread item "Titre never read back" carried `tick=tick-measured`, `sr="Measured · first-party."`, `title="Measured · first-party"` and the caption "with no protocol’s steps · unconfirmed".
- **Likely cause:** `src/screens/DepositionDetail.tsx:511` and `:516` draw `<ProvenanceBadge p="measured" />` and `<Tick p="measured">` for every released value, and the one use of `e.confirmed` is the caption's " · unconfirmed" at `:534`; `src/store.ts:2458` (`reconcileDeposition`) writes `provenance: 'measured'` on every released row. The service computes `unverified` from `confirmed` at `core/openferment_core/module_stores.py:475-476` (confidence: high).
- **Fix size:** small, the band's badge and tick in `DepositionDetail.tsx`, drawn from `e.confirmed` or from the service's computed class.
- **Stood on:** the second refutation, by the kind's own standard. The first set it aside because it read `ADR-006:242-243` and `core/openferment_core/module_stores.py:469-471` as words about the service's module read, and `ADR-006:21-22` as aimed at a model or a person setting provenance.

#### H3-16 · S3 · Broken use · units.normalize, micro written with U+03BC

Every micro key and alias in `schema/units.json` is spelled with the micro sign U+00B5, and `units.normalize` folds no Greek small letter mu U+03BC onto it, so `μg/mL`, `μL`, `μM` and every other micro unit typed with U+03BC normalise to None, and a candidate that copies such a unit as the paper wrote it is refused on rule `unit`. This entry covers text that spells micro with U+03BC. Text with U+00B5 anchors.

- **Contract:** `core/openferment_core/extract.py:111`, "Give the unit as the paper wrote it."; `core/openferment_core/units.py:121`, "The table key for a unit as somebody wrote it, or None."
- **Reproduce:** `bash bughunt/repro/H3-16/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** `'μg/mL'` (U+03BC) normalises to `'µg mL⁻¹'` as `'µg/mL'` (U+00B5) does, and a candidate whose unit is copied as the paper wrote it is proposed under either code point.
- **Observed:** On 7 of 7 spellings, `units.normalize` gave a key for the micro sign (`'µg/mL'` to `'µg mL⁻¹'`). On the same 7 spellings it gave None for the Greek mu (`'μg/mL'` to None). `units.convert(150, 'μg/mL', 'g L⁻¹')` raised "UnitError: Unknown unit: μg/mL". The table holds 10 keys and 5 aliases with U+00B5. It holds 0 with U+03BC. On the service, the Greek-mu document's candidate drew "biorepo_write refused on rule unit: unit 'μg/mL' does not normalise". The micro-sign document's candidate came back `state='proposed'`. The Greek-mu quote with its unit retyped in U+00B5 came back `state='proposed'`. The browser's `normalizeUnit` returned null for `"μg/mL"`, `"μL"` and `"μM"`.
- **Likely cause:** `core/openferment_core/units.py:91-101`: `_STRIP_STEPS` folds middots, U+2212, the en dash and the superscripts and holds no step from U+03BC to U+00B5, so `normalize` (`units.py:120-146`) misses every micro key and alias; the browser's `strip` at `src/engine/units.ts:384-385` lacks the same step (confidence: high).
- **Fix size:** small, one fold step in `_STRIP_STEPS` and in `strip` in `src/engine/units.ts`, with a fixture pair in `scripts/export-unit-fixtures.ts`.
- **Stood on:** the second refutation, by the kind's own standard. The first set it aside because it read the fold list at `core/openferment_core/units.py:87-101` and normalize's five attempts at `units.py:123-128` as the full written set of folds, a set with no U+03BC step.

#### H4-04 · S3 · Contract break · fermOS mass balance: kinetics.mass_balance, fermos simulation flags

fermOS's mass balance divides its gap by the sugar consumed, so a fed-batch whose cells take up no sugar, and whose series meets the closed form within 1.3e-6, reports closure 1 from 8.5e-5 g of integrator error (closure 1.5 with a feed of water), sets `massBalance.ok` false, carries the flag "The mass balance does not close" and says in its note that the rate laws or their parameters do not hold together.

- **Contract:** `core/openferment_core/kinetics.py:91-93`, "Both are invariants of the equations, which LSODA keeps to rounding: the check catches a wrong right-hand side (a dropped 1/Yps reads 30 % off), never integrator error".
- **Reproduce:** `bash bughunt/repro/H4-04/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** A fed-batch with μmax 0 and no maintenance or product terms takes up 0 g of sugar, and its series follows the equations to the integrator's tolerance. Its `massBalance.ok` is true and its flags hold no mass-balance line.
- **Observed:** In both runs `noUptakeSugar` (1 L, 0.05 L/h for 20 h, feed 100 g/L) met the closed form within 1.20e-06, and `POST /api/fermos/simulate` answered `massBalance` closure 1 with `ok` False, the note "Sugar consumed, 8.45561e-05 g, ... within 1 of it, outside the 1% closure, so the rate laws or their parameters do not hold together" and the flag "The mass balance does not close: 1 against 1%." `noUptakeWater` met the closed form within 1.33e-06 and answered closure 1.5 with `ok` False, sugar consumed -1.5429e-05 g, and the flag "The mass balance does not close: 1.5 against 1%." The control with growth closed at 2.13e-07 with `ok` True.
- **Likely cause:** `core/openferment_core/kinetics.py:1346`: `scale = max(abs(consumed), ATOL)` divides the gap by `consumed` (`kinetics.py:1338`), a difference of two sums near 120 g, each integrated at RTOL 1e-6; with zero true uptake `aux` and `cross` are zero to rounding, so the ratio is |consumed| / |consumed| = 1 or more, `fermos.py:2300` sets `ok` false and `fermos.py:2312` adds the flag. (confidence: high)
- **Fix size:** small: the scale in `kinetics.mass_balance` becomes the sugar the run handled (the start plus what was fed), with a test on a no-uptake fed-batch.
- **Stood on:** the first refutation.

#### H5-05 · S3 · Contract break · fermOS forecast (POST /api/fermos/forecast; growth_forecast and fermos_write forecast at the tool door)

`POST /api/fermos/forecast` naming a `fitArtifactId` the acting project does not hold (an unknown id, or another project's kept fit) answers HTTP 500 with no words, and the tool door `growth_forecast` refuses with the bare quoted id.

- **Contract:** `core/openferment_core/api.py:208`, "A refusal is a status with its reason in `detail`, in words."; and `CLAUDE.md:87`, "a refusal is a 422 in words."
- **Reproduce:** `bash bughunt/repro/H5-05/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** A forecast of a fit the acting project does not hold answers a 404 or 422 whose `detail` names the fit in words, the words `fermos.py:928` already holds ("there is no kept fit <id>"). The tool door refuses in the same words.
- **Observed:** In both runs the route answered `500 'Internal Server Error'` for `fitArtifactId` `0123456789abcdef` in project h505-a and for h505-a's kept fit `47f69f1f59ee0243` asked from project h505-b, and the service log shows `openferment_core.artifacts.ArtifactNotFound` raised at `fermos.py` line 926 in `forecast_run` through `api.py` line 735 in `fermos_forecast` for each id. `POST /api/tools/growth_forecast` answered 200 with error `"growth_forecast refused: '0123456789abcdef'"`. The control, h505-a's own fit asked from h505-a, answered 200 with a kept forecast. `GET /api/params/fermos:forecast:0123456789abcdef` answered 404 with "there is no kept kinetic fit 0123456789abcdef: fermOS keeps a fit when it fits a deposited run".
- **Likely cause:** `core/openferment_core/fermos.py:927` wraps `artifacts.get(fit_artifact)` in `except FileNotFoundError`. `artifacts.get` raises `ArtifactNotFound`, a `KeyError` subclass (`core/openferment_core/artifacts.py:54`), so the worded `FitRefused` at line 928 is never raised and `core/openferment_core/api.py:737`, which catches `fermos.FitRefused` alone, lets the `KeyError` reach the server as a 500. The tool door at `core/openferment_core/tools/writes.py:341` catches `ArtifactNotFound` and prints `str(e)`, which for a `KeyError` is the quoted id. (confidence: high)
- **Fix size:** small: catch `artifacts.ArtifactNotFound` and `artifacts.ArtifactDamaged` at `fermos.py:927` and raise `FitRefused` in words, as `_fit_art` does at `fermos.py:1704-1711`; the tool door then carries the same words.
- **Stood on:** the first refutation.

#### H5-08 · S3 · Inconsistency · MCP: the sci-rag server (literature_mcp.py) against the openferment server

Started with `--project` naming an id the database does not hold (`bh-zzz`, `../bh-a`, `BH-A`), the sci-rag MCP server answers every store read exactly as it answers a held empty project and tells the client the project's documents enter on Intake, so it disagrees with the openferment MCP server and the REST routes, which refuse those ids as missing or malformed.

- **Contract:** `core/openferment_core/literature/kit.py:22-24`: "the calls below, the kit's REST app at /rag (`rest_app`) and its MCP server (`openferment_core/literature_mcp.py`) answer alike for one project". `CLAUDE.md:98` pairs the two MCP servers: "both in `.mcp.json`, each acting in the project `--project` names and refusing in words without one".
- **Reproduce:** `bash bughunt/repro/H5-08/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** For an id the database does not hold, the sci-rag server answers as its paired doors answer: every call refused in words saying the database holds no such project. The openferment server says "holds no project named ..." (`core/openferment_core/mcp_server.py:339`), and the REST app at /rag says 404 "no project named ..." or, for an id of no project's shape, 422 "... is not a project id" (`core/openferment_core/api.py:393-400`).
- **Observed:** In both runs the openferment server answered `literature_sources` for each of the three ids with "The database bh_r_h5_08_mcp on 127.0.0.1:5432 holds no project named 'bh-zzz'" (and '../bh-a' and 'BH-A' in turn). For the same ids the sci-rag server gave six answers equal to the held empty `bh-a`'s with the id swapped (6/6 for each id): `corpus_stats` `"documents": 0`, `list_sources` `"sources": {}`, `get_document` and `get_citations` "No such document", and both graph tools "The project bh-zzz holds no passage yet: its documents enter on Intake". With no project named, the sci-rag server refused every call in words ("This Sci RAG Kit server acts in no project").
- **Likely cause:** `core/openferment_core/literature_mcp.py:68-70`: `_named()` raises `NO_PROJECT` when `projects.current_or_none() is None` and passes any named id, and `act_in` (`core/openferment_core/literature_mcp.py:128-134`) writes whatever `--project` gives into `OPENFERMENT_PROJECT`, with none of the `projects.held` check that the openferment server's `_Store.refusal` makes (`core/openferment_core/mcp_server.py:329-343`). The kit's `ProjectService` then reads an empty scope, and `NO_PASSAGES` (`core/openferment_core/literature/graph.py:77-80`) gives the empty project's words for the missing id. (confidence: high)
- **Fix size:** small, one check in `_named` for a valid id held by the store, cached once held as `_Store.refusal` caches it, with words naming the missing project.
- **Stood on:** the second refutation, by the kind's own standard; the first set it aside because it read `docs/TOOLS.md:907` as the sci-rag server's full list of refusals and the landing-review note at `docs/PROGRESS.md:3351-3355` as leaving the held check to the owner.

#### H7-02 · S3 · Contract break · client store hydration and the Deposition bench (src/store.ts, src/screens/Deposition.tsx)

A page reloaded with the service away leaves the project's rows unloaded for the rest of its life, so the bench reads "Deposition not found" and the reading queued during the outage stays in the browser until a second reload after the service answers.

- **Contract:** `docs/decisions/ADR-014-durable-write-queue.md:21-22`, "so a decision made while the service is away survives a reload and is sent when the service answers". For the bench in particular, `src/lib/projectState.ts:11-12`, "so a deposition at the bench survives a reload while the service is away and is sent when it answers again".
- **Reproduce:** `bash bughunt/repro/H7-02/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** The reading queued at the bench during the outage survives the reload and goes to the service once the service answers, in the page already open.
- **Observed:** In both runs, after a reload with every `/api` request refused, the bench read `data-state="missing"` and "Deposition not found This project holds no deposition dep-mwbbhkag-1, or its rows have not loaded from the service yet." (run 2: dep-mwbbkcjm-1), and the IndexedDB queue held that deposition with `["4.4 USD/kg"]` and 1 observation. 45 s after the service answered again, with no reload, the service held `{"entries":[],"observations":0,"state":"running"}` and the queue still held the entry. Within 30 s of a second reload the service held `{"entries":["4.4 USD/kg"],"observations":1,"state":"running"}` and the queue was `[]`. The `dbaway` scenario, the service serving the page with its database refusing connections so every `/api` call answered `{"error":503}`, gave the same sequence in both runs.
- **Likely cause:** `src/store.ts:1050`: `hydrateProjectState` catches the failed `GET /api/state`, sets `stateProblem` and returns at line 1051, before it lays the queue over the held rows (line 1073) and before it calls `flushProjectState` (line 1083); `src/App.tsx:378` calls it once per page load, and the change subscriber returns whenever `stateSeen` is null (`src/store.ts:3634`), so nothing sends the queue before the next page load. (confidence: high)
- **Fix size:** medium: the store runs `hydrateProjectState` again after a failed load once the service answers, which lays the queue over the rows and flushes it.
- **Stood on:** the second refutation, by the kind's own standard; the first set it aside because it read ADR-014's note of E.19 (`docs/decisions/ADR-014-durable-write-queue.md:46-58`) and the words at `src/store.ts:2800`, "sent when the project next loads with the service answering", as the ADR's own reading of "sent when the service answers".

#### H7-05 · S3 · Contract break · client routing and project opening (src/App.tsx, src/store.ts)

Opening `/#/p/<id>/...` for an id the service holds no project under reloads the page without end, about eight to eleven times a second, each load asking `GET /api/projects`, and the page never settles on a screen.

- **Contract:** `docs/decisions/ADR-009-ui.md:21-22`, "an address naming another project opens it (the page reloads in it, as a project switch does)"; and `docs/decisions/ADR-009-ui.md:3-4`, the ADR's requirement "something on screen at the earliest moment".
- **Reproduce:** `bash bughunt/repro/H7-05/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** The address reloads the page once at most and then settles on one screen, as the held project's address does (2 loads, then still).
- **Observed:** In both runs the held project's address `#/p/h7-05/runbooks` made 2 page loads and 2 `GET /api/projects` in 10.2 s and 0 more loads in the next 2 s. The address `#/p/nosuchproject/runbooks` made 108 and 87 page loads, each with a `GET /api/projects`, in 10.2 s, then 22 and 17 more loads in the next 2 s. The address stayed `#/p/nosuchproject/runbooks` and `localStorage` `openferment.project` read `'nosuchproject'`.
- **Likely cause:** `src/App.tsx:141` calls `openProject(route.project)` whenever the address's id differs from the store's `projectId`, `loadProjects` at `src/store.ts:1017-1018` swaps an open id the project list lacks for the one project held (or null when several or none are held) and stores the swap, and `openProject` at `src/store.ts:1023-1027` writes the address's id back to localStorage and reloads, so every load ends with the two ids apart and a fresh reload. (confidence: high)
- **Fix size:** small: compare the address's id with the project list before opening it, in the effect at `src/App.tsx:140-142` or in `openProject`, and show a screen that names the missing project.
- **Stood on:** the first refutation.

#### H7-06 · S3 · Broken use · client screens' service-down words (RunbookDetail, DepositionDetail, PaperReader, GuildSkills, Postdoc)

Narrowed to what the reproduction and the second refutation hold: when a page loads with the service down, the runbook, deposition, paper and Guild skill pages say the project holds no row of that id and name nothing of the service, and the Postdoc page lists no conversation for the one its address names, with its composer naming the service. A page opened before the service stops keeps showing its rows.

- **Contract:** `src/lib/http.ts:3-4`, "`ServiceDown`: nothing answered, or it answered with an error a person cannot act on here; the remedy names the command that starts the service." The store keeps that failure for the pages at `src/store.ts:696`, "Why the open project's rows could not be loaded, in words; null when they were."
- **Reproduce:** `bash bughunt/repro/H7-06/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** Each of these pages says the service is not running and names the command that starts it, as the strain, lesson and protocol pages do from the same failed loads.
- **Observed:** In both runs, with the service stopped, 65 of 66 `/api` requests failed at the connection and 0 answered; the runbook page said "This project holds no runbook with this id." and "The project keeps no runbook of that id; the link may be from another project.", the deposition page "This project holds no deposition with this id.", the paper page "5a47dfa76d424933b40b573c4bba752c is not a document this project holds." (run 2: 64739b3a12164d06a9b4979dc15dd372) and the skill page "The project's skill catalogue holds no skill h706-skill.", and none of the four named the service. Postdoc listed "No conversation yet: a person asks the first question." and its composer said "Postdoc needs the service Start it with pnpm prototype:up from the repository root". The strain, lesson and protocol pages said "The service is not running. Start it with pnpm prototype:up from the repository root.", and with the service up all eight pages showed their row.
- **Likely cause:** `src/screens/RunbookDetail.tsx:584`: the page's `if (!runbook)` branch draws its not-found words from the store's list and reads none of the failure the store kept (`stateProblem`, `cataloguesProblem`, `serviceUp`); the same branch stands at `src/screens/DepositionDetail.tsx:249` (line 220 reads `stateProblem` to end the loading state), `src/screens/PaperReader.tsx:254` and `src/screens/GuildSkills.tsx:83`, and `src/screens/Postdoc.tsx:395` draws its list from `liveConversations` and reads no failure. (confidence: high)
- **Fix size:** small: each not-found branch reads its load's problem and says it, as `src/screens/StrainPage.tsx:908-917` does.
- **Stood on:** the second refutation, by the kind's own standard; the first set it aside because it read `src/lib/http.ts:3-4` and the store's field comments as a description of the `ServiceDown` error that sets no duty on what a page renders, and found no written rule that a page tell a failed load from a missing row.

#### H7-07 · S3 · Contract break · src/screens/Deposition.tsx, the bench takeover

At 810x1080 with touch, the protocol run's Next step button measures 43 x 56 px on every step and the staged run's link to its runbook measures 174.1 x 18 px, two targets under the takeover's 44 px; the verdict confirmed these two sizes and held the link's underline, which shows on hover alone, to be a weaker point.

- **Contract:** `CLAUDE.md:59` (R), "`src/screens/Deposition.tsx` is a glove-tolerant full-screen takeover (810 px portrait, 44 px targets, 7:1 step-text contrast, no hover affordance); extend it and keep its header comment."; and `src/screens/Deposition.tsx:9`, "touch targets ≥ 44px, because the hand operating this is gloved;".
- **Reproduce:** `bash bughunt/repro/H7-07/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** At 810 px portrait every target in the takeover measures at least 44 x 44 px, the Next step button and the staged run's runbook link among them.
- **Observed:** In both runs Next step measured 43 x 56 px on steps 1, 2 and 3 (min-width auto), beside Back 96 x 56, Mark step complete 527.9 x 56 and Skip 75.1 x 56. The staged view's runbook link "H7-07 placeholder runbook" (class `text-accent hover:underline`, display inline) measured 174.1 x 18 px, with Begin recording beside it at 171.1 x 56 px. The link's `text-decoration-line` read none at rest. Under a hover it read underline, from the one matching rule `.hover\:underline:hover`.
- **Likely cause:** `src/screens/Deposition.tsx:954-960` gives the Next step `Button` `style={{ minHeight: 56 }}` and no width around `<ArrowRight size={17} />`, and `.btn` at `src/styles.css:366-376` adds `padding: 6px 12px` and a 1px border, so the width comes to 17 + 24 + 2 = 43 px; the anchor at `src/screens/Deposition.tsx:351` is inline with class `text-accent hover:underline` and no `min-h-[44px]`, so its box is one line of text tall. (confidence: high)
- **Fix size:** small: a `minWidth` of 44 px or more on the Next step button, and on the link at `Deposition.tsx:351` the classes the bench's own runbook link at `Deposition.tsx:1152` already carries (`underline underline-offset-2 inline-flex items-center min-h-[44px]`).
- **Stood on:** the first refutation.

#### H7-08 · S3 · Contract break · client shell: the rail's logo link (src/App.tsx, src/router.tsx)

Inside a project, the rail's logo links to `#/`: one click opens Home with no project in the address, every rail link on that screen then carries a plain path, and the address drops the project. The page goes on acting in that project.

- **Contract:** `docs/decisions/ADR-009-ui.md:21`, "a navigation or a link from inside a project stays inside it (`inProject`)"; and `src/router.tsx:7-8`, "A link or a navigation to a plain path from inside a project stays inside it."
- **Reproduce:** `bash bughunt/repro/H7-08/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** The logo, a link to the plain path `/` from inside project `h7-08`, opens `#/p/h7-08`, the project's home, as the rail's own Home entry does. The rail's links after it keep `#/p/h7-08/`.
- **Observed:** In both runs, at `#/p/h7-08/runbooks` the logo's href was `#/`. On the same screen 13 of the 13 other rail links kept `#/p/h7-08/`, and the rail's Home entry (`to: '/'`, `src/data/nav.ts:88`) read `#/p/h7-08`. After the logo the address was `#/`, the screen was Home ("Bioprocess literature you can operate on ..."), the top bar still read "H7-08 repro", `localStorage` `openferment.project` still held `'h7-08'`, and 13 of the 13 rail links were plain paths (`#/ #/intake #/biorepo #/postdoc ...`). The rail's Intake link then gave `#/intake`.
- **Likely cause:** `src/App.tsx:498`: the logo's anchor is written by hand as `<a href="#/" className="flex items-center gap-2 min-w-0">`, so it skips `href()` (`src/router.tsx:86-88`), the function that applies `inProject` (`src/router.tsx:44-47`) and maps `/` to `/p/<project>` for the rail entries (`src/App.tsx:517`) and Settings (`src/App.tsx:559`); the built bundle carries the same `href:"#/"`. (confidence: high)
- **Fix size:** small: `href={href('/')}` on the one anchor in `src/App.tsx`.
- **Stood on:** the first refutation.

#### H8-03 · S3 · Contract break · Intake upload (collectors.uploaded, intake.store, kit._store)

`POST /api/intake/upload` of a file named `report%00.md` answers HTTP 500 after the kit has committed the document. The uploading project holds nothing. A second project that uploads the same bytes is linked to that document, whose `sourceRef` is the server's removed temporary file.

- **Contract:** `docs/api/intake.md:55-56`, "A failure is an answer the Intake board renders: the route raises no 5xx for a document it could not collect."; and `core/openferment_core/literature/kit.py:613-614`, "`sourceRef`, when it has one, is where a newly stored document points back to".
- **Reproduce:** `bash bughunt/repro/H8-03/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** The upload answers HTTP 200 with a `CollectOutcome`: status `failed` with the reason in words, or the document stored under a name the database can keep. Every document the kit keeps is linked to a project.
- **Observed:** In both runs `h803a`'s upload answered HTTP 500 `Internal Server Error`, and the service log held asyncpg's `invalid byte sequence for encoding "UTF8": 0x00` on `UPDATE documents SET source_ref=$1::VARCHAR` with the parameter `'upload:report\x00.md'`. `h803a` then held 0 documents and 0 project links. The kit kept 1 document that no project links, with source `project:h803a:upload` and source_ref `/tmp/openferment-collected-3ietbq48/report-.md.md` (run 2: `/tmp/openferment-collected-atg4k6fa/report-.md.md`). `h803b`'s upload of the same bytes as `report.md` answered `linked` to that document, its source `project:h803a:upload` and its sourceRef that temporary path, with `file exists: no`.
- **Likely cause:** `core/openferment_core/literature/kit.py:600`: after `ingest_entries` has committed the document (`kit.py:588`), a second session (`kit.py:596-602`) sets `source_ref` to `upload:report\x00.md`, a value whose NUL comes from `unquote(filename)` (`core/openferment_core/literature/collectors.py:1671`) by way of `selection["sourceRef"]` (`core/openferment_core/intake.py:74`); PostgreSQL refuses the NUL, the exception leaves `_store` before `_link` (`kit.py:603`), and `intake.upload` (`intake.py:113-117`) catches `NotCollected` alone around a `store` (`intake.py:88`) with no guard of its own, so the error reaches the route (`core/openferment_core/api.py:2087`) as a 500. (confidence: high)
- **Fix size:** small: `collectors.uploaded` refuses or strips a NUL in the name, and `intake.store` answers a store error as a `failed` outcome.
- **Stood on:** the first refutation.

#### H8-05 · S3 · Contract break · POST /api/flowsheets/import-url (collectors._fetch)

When a host answers the import-url fetch with 302 and a Location that has a scheme and no host (`https:127.0.0.1/x`, `javascript:alert(1)`), `POST /api/flowsheets/import-url` answers `500 Internal Server Error` with no words, because httpx raises `httpx.InvalidURL` and no handler on the path catches it.

- **Contract:** `docs/api/sff.md:88-94`, "Each refusal is said in words a person reads: 413 for a file past the size; 422 for an address that is not https, ... (a redirect to any of these included), ...; 502 when the host name could not be found, the host refused the connection, could not be reached, or was not read in time, or it answered an error"; and `core/openferment_core/literature/collectors.py:469-471`, `fetch_file`'s docstring, "Raises AddressRefused, TooLarge, HostFailed (the host could not be found, reached or read in time, or answered an error) or NetworkRefused, each in words."
- **Reproduce:** `bash bughunt/repro/H8-05/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** The route refuses each malformed redirect in words that name the address, 502 (the host answered an error) or 422 (a redirect to an address that is not https), and keeps nothing. The control redirect from `/to-http` to `http://public.test/x` shows that shape: 422 in words.
- **Observed:** In both runs `/bad-location` (Location `https:127.0.0.1/x`) and `/js-location` (Location `javascript:alert(1)`) each answered `500 Internal Server Error` with the body `Internal Server Error`. In both runs the control `/to-http` answered 422 "https://public.test/to-http redirected to http://public.test/x, which is not an https address; a redirect is followed to another https address alone". One level down, `collectors.fetch_file` raised `httpx.InvalidURL: For absolute URLs, path must be empty or begin with '/'`, which the run reported as an `httpx.HTTPError`: False and one of the four documented refusals: False. The project held 0 `openferment.flowsheets` rows after each run.
- **Likely cause:** `core/openferment_core/literature/collectors.py:445` catches `httpx.HTTPError` alone; httpx 0.28.1's `_redirect_url` (`core/.venv/lib/python3.13/site-packages/httpx/_client.py:532-533`) calls `url.copy_with(host=request.url.host)` for a Location with a scheme and no host and raises a bare `InvalidURL`, a direct subclass of `Exception`, when `client.stream` at `collectors.py:435` builds the redirect request, and the route at `core/openferment_core/api.py:1031-1036` catches `TooLarge`, `AddressRefused`, `NetworkRefused` and `HostFailed` alone, so FastAPI answers 500. (confidence: high)
- **Fix size:** small: catch `httpx.InvalidURL` beside `httpx.HTTPError` at `collectors.py:445` and raise `HostFailed` in words naming the redirect, with a route test over a stand-in transport.
- **Stood on:** the first refutation.

#### H8-06 · S3 · Contract break · GET /api/literature/search (kit.search over the kit's retriever)

With no model reachable, `GET /api/literature/search?profile=deep` answers `degradedStages: []` after its graph and HyDE layers both fail on their model call. The verdict confirmed this for a direct caller of the route. BioRepo Search never meets it, since the screen always searches with the interactive profile.

- **Contract:** `core/openferment_core/models.py:605-606`, the `SearchResponse` docstring generated into `docs/api/openapi.json:13180`, "GET /api/literature/search: the hits, best first, and the retrieval layers that timed out or failed, so a narrow result says why."
- **Reproduce:** `bash bughunt/repro/H8-06/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** A deep search whose graph and HyDE layers fail on their model call lists `graph` and `hyde` in `degradedStages`, so the narrow result says why.
- **Observed:** In both runs, with health `hasKey: False`, the route answered `profile deep | degradedStages [] | hits 1`. In both runs, during that call the service logged `query_entity_extraction_failed error=ModelUnavailable` and `hyde_generation_failed error=ModelUnavailable`. The same search in process gave the kit's traces `{"vector": "success", "keyword": "success", "graph": "empty", "community": "skipped", "hyde": "empty", "rerank": "disabled"}` with `"degraded_stages": []`.
- **Likely cause:** `core/openferment_core/api.py:2134` passes `result.degraded_stages` through as the kit gives it, and in Sci RAG Kit 0.5.0 (`core/.venv/lib/python3.13/site-packages/sci_rag/`) `extract_query_entities` (`retrieve/stages/graph.py:175-179`) and `generate_hyde_passage` (`retrieve/stages/hyde.py:37-41`) catch every exception, log a warning and return nothing, the retriever marks a stage with no keys `empty` (`retrieve/retriever.py:365`), and `degraded_stages` counts `timeout` and `error` alone (`retrieve/types.py:159-160`). (confidence: high)
- **Fix size:** medium: openFerment's `kit.search` or the route has to learn that a deep layer's model call failed, from the kit's warnings or from a model check ahead of the deep layers, and name those layers in `degradedStages`, with a test of the deep profile with no model.
- **Stood on:** the first refutation.

#### H8-07 · S3 · Wrong number · pnpm lit:report --project (literature/report.py _retrieval)

In `pnpm lit:report --project` the kit-rule column counts a passage of another document as relevant when that document carries the question's document's title, so with two documents titled "Strain report" the kit MRR for the question reads 1.0. The rule the report states gives 0.5.

- **Contract:** `core/openferment_core/literature/report.py:760`, "The kit's rule counts a passage of the question's document, or one holding a quote of its candidates", the words the committed report carries at `docs/reports/literature-retrieval.md:57`.
- **Reproduce:** `bash bughunt/repro/H8-07/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** Document B's passage is of another document and holds no quote of A's candidate, so the kit rule counts it irrelevant: relevant ranks `[2]`, first relevant rank 2 and MRR 0.5, the same as the passage rule.
- **Observed:** In both runs, in `interactive`, `vector_only` and `keyword_only` alike, rank 1 was document B's chunk ("the question's document: False; holds an evidence phrase (the quote): False") and rank 2 was A's chunk (True, True). The kit rule gave relevant ranks `[1, 2]`, first 1, MRR 1.0. The passage rule gave `[2]`, first 2, MRR 0.5. Both documents carried the title 'Strain report' (run 1: A 74615e11..., B 3b8c81f4...; run 2: A 85c1be99..., B fa9bcf24...), and the report spent 0 USD.
- **Likely cause:** `core/openferment_core/literature/report.py:364` builds each question with `reference_titles=[titles[document_id]]`, and `report.py:450` scores the kit column with the kit's `is_relevant` (`sci_rag/evals/retrieval_eval.py:52-56`, installed under `core/.venv`), which counts any item whose normalized title equals a reference title, so every document of that title stands as the question's document. (confidence: high)
- **Fix size:** small: the kit column at `report.py:450` scores by `a.document_id` or a quote match; `Asked` already holds `document_id` (`report.py:366`).
- **Stood on:** the second refutation, by the kind's own standard. The first refutation set it aside because it read the report's sentence at `report.py:760` as a paraphrase of the kit's rule, whose `SeedQuestion.reference_titles` names a reference document by its title.

#### H8-08 · S3 · Contract break · POST /api/literature/answer

With no key, the answer stream's `error` event reads "ModelUnavailable: generation failed (see server logs)". The words that name the missing key reach the service log alone, so neither the stream nor BioRepo Search says that no key is set.

- **Contract:** `core/openferment_core/api.py:2148-2149`, the route's docstring published at `docs/api/openapi.json:23239`, "One model call through llm.py, under the day's cap; with no key the stream says so in an `error`."; and `src/lib/literature.ts:115-116`, "An `error` event throws IntakeDown with the service's words, a missing key among them."
- **Reproduce:** `bash bughunt/repro/H8-08/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** The stream's `error` event says that no key is set, in the service's own words as the extract route gives them ("ANTHROPIC_API_KEY is not set. Put it in core/.env (gitignored) and restart the service."), and BioRepo Search shows those words.
- **Observed:** In both runs, with health `hasKey False`, the stream sent `retrieval_started retrieval_done compression_done generation_started error`, and the error was `{"code": "generation_failed", "message": "ModelUnavailable: generation failed (see server logs)"}`. The service log held `answer_generation_failed detail='ANTHROPIC_API_KEY is not set. Put it in core/.env (gitignored) and restart the service.' error=ModelUnavailable`, and `POST /api/intake/{id}/extract` on the same service answered HTTP 503 `{"detail":"ANTHROPIC_API_KEY is not set. Put it in core/.env (gitignored) and restart the service."}`. BioRepo Search showed "ModelUnavailable: generation failed (see server logs) The service log says why."
- **Likely cause:** `core/openferment_core/literature/kit.py:833-838` passes the kit's `error` event on with its `_` keys dropped, and that event comes from `core/.venv/lib/python3.13/site-packages/sci_rag/answer/generator.py:300-311`, which catches the `ModelUnavailable` from `llm.stream`, logs its words (line 304) and yields `f"{type(exc).__name__}: generation failed (see server logs)"` (line 309) and returns, so `kit.answer`'s own branch at `kit.py:830-831`, which sends `str(item)`, never runs. (confidence: high)
- **Fix size:** small: `kit.answer` (or `llm.kit_client`'s `stream`) keeps the words of the `ModelUnavailable` that stopped the call and puts them in the `error` event's message, with a test of the stream with no key.
- **Severity:** S3, the reading of the refuting agent and of the entry's writer. An independent severity panel read S4: With no key, the answer stream ends in an error as its route intends.
- **Stood on:** the first refutation.

#### H9-02 · S3 · Contract break · tool door gates, intake_write extract

When the day's cap refuses an extraction asked through `intake_write` at the tool door (the `tools.run` path the MCP server and Postdoc's loop take), the call answers an error naming the cap and keeps no proposal, so the spend gate's proposal and its "extract it when the budget allows" button never reach Home.

- **Contract:** `core/openferment_core/tools/gates.py:13-15`, "The spend gate is the one a tool reaches at run time: an extraction is free until the budget refuses it, and then it is proposed for when the budget allows."; and `docs/TOOLS.md:856`, "| `spend` | spend past the ask or the daily budget | `intake extract` | extract it when the budget allows |".
- **Reproduce:** `bash bughunt/repro/H9-02/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** With `OPENFERMENT_DAILY_BUDGET_USD=0.001`, each `intake_write` `extract` call answers `summary.state` "proposed", `gate` "spend" and a `proposalId` with no error, and `GET /api/proposals` lists the spend proposal that Home shows with its button.
- **Observed:** In both runs the call named by `?by=Alice Person` and the call named by `X-OpenFerment-Assistant: bughunt-client/0.1` each answered `summary.state=None gate=None proposalId=None auditIds=[]` with the error "intake_write could not extract <doc>: Today's model spend is $0.00 of the $0.00 daily cap, and this call could pass it. Raise OPENFERMENT_DAILY_BUDGET_USD in core/.env, or wait for the next UTC day." `GET /api/proposals` answered `[]`, and the stand-in model API recorded 0 requests, so the cap refused the call before it was sent.
- **Likely cause:** `core/openferment_core/extract.py:340-342` catches `llm.ModelUnavailable`, of which `llm.BudgetExhausted` is a subclass (`core/openferment_core/llm.py:438`), and re-raises it as `ExtractUnavailable`, so the `except llm.BudgetExhausted` that builds the proposal at `core/openferment_core/tools/writes.py:1171` never runs and the next clause answers the error at `writes.py:1178`; the two tests that hold the gate (`core/tests/test_writes.py:360`, `core/tests/test_proposals_review.py:73`) stub `extract_paper` to raise `BudgetExhausted` directly and so pass over that wrapping. (confidence: high)
- **Fix size:** small: let `extract.call_model` re-raise `llm.BudgetExhausted` unchanged in a clause ahead of its `ModelUnavailable` clause, with a test that reaches the cap through `llm.call`.
- **Stood on:** the first refutation.

#### H9-03 · S3 · Hollow test · tests of the spend gate

The spend gate's two tests, `test_writes.py::test_an_extraction_the_budget_refuses_becomes_a_spend_proposal` and `test_proposals_review.py::test_a_spend_proposals_why_holds_no_number`, replace `extract.extract_paper` with a stub that raises `llm.BudgetExhausted`, an exception the real `extract_paper` wraps in `ExtractUnavailable`, so both pass on a tree where a budget refusal keeps no spend proposal (H9-02).

- **Contract:** `core/tests/test_writes.py:360`, the test's own name, "an extraction the budget refuses becomes a spend proposal"; and `core/openferment_core/tools/gates.py:13-15`, "The spend gate is the one a tool reaches at run time: an extraction is free until the budget refuses it, and then it is proposed for when the budget allows."
- **Reproduce:** `bash bughunt/repro/H9-03/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** A test of the spend gate drives the refusal through the real extraction path, with `llm.call` refused by the daily cap. It fails on any tree where `intake_write extract`, refused by the cap, keeps no proposal with `state: proposed` and `gate: spend`.
- **Observed:** In both runs on 2047f5a, pytest gave "2 failed, 2 passed": the two suite tests passed. On the same tree, under `OPENFERMENT_DAILY_BUDGET_USD=0.001`, the real `extract_paper` raised `ExtractUnavailable` from `BudgetExhausted` ("Today's model spend is $0.00 of the $0.00 daily cap, and this call could pass it. ..."), and `intake_write extract` answered the error "intake_write could not extract X1: ..." with summary `{}` and 0 proposals kept. On a control tree where `call_model` re-raises `BudgetExhausted` (2 lines added), pytest gave "4 passed" and `intake_write extract` answered `state: proposed`, `gate: spend` with 1 proposal kept, so the two suite tests gave the same result on both trees.
- **Likely cause:** `core/tests/test_writes.py:363-366` and `core/tests/test_proposals_review.py:74-77` monkeypatch `extract.extract_paper` with `broke`, which raises `llm.BudgetExhausted` directly. The real `call_model` at `core/openferment_core/extract.py:340-342` catches `llm.ModelUnavailable`, the parent class of `BudgetExhausted` (`core/openferment_core/llm.py:438`), and raises `ExtractUnavailable`, so the tests exercise the `except llm.BudgetExhausted` branch at `core/openferment_core/tools/writes.py:1171`, a branch the real path cannot reach. (confidence: high)
- **Fix size:** small: the two tests drive the refusal through `llm.call` under a tiny daily cap with a client that never sends, and they pass once H9-02's fix lands in `extract.call_model`.
- **Stood on:** the first refutation.

#### H9-04 · S3 · Contract break · validate.find_number, Rule 1 for a claim's words

Postdoc's loop keeps claims whose words state a quantity as "doubled", "halved", "quadrupled", "Table IV", "x10", "pH7" or "pH-4", among them the plan prompt's own example of a discarded claim, "Ethanol titre roughly doubled under anaerobic conditions", and it keeps a gap that says "doubled at pH7". Of the hunt's eight words these seven survived. The eighth, "phase III", is left out because it follows the validator's step-label rule (`core/openferment_core/validate.py:139`).

- **Contract:** `CLAUDE.md:55` (R), "a claim with a number in its words is dropped and counted (ADR-006)"; and `core/openferment_core/postdoc/plan.py:54` and `:59`, "A claim containing a number is discarded whole", with the example `bad:   "Ethanol titre roughly doubled under anaerobic conditions"`.
- **Reproduce:** `bash bughunt/repro/H9-04/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** Each of the seven claims is dropped and counted with a reason that names the word, the way the controls "twofold", "tenfold" and "pH 7" are. The gap that says "doubled at pH7" is dropped, as the gap that says "twofold" is.
- **Observed:** In both runs `postdoc_agent.ask` kept 9 claims and rejected 3, the controls k1 ('twofold'), k2 ('tenfold') and k3 ('7'). All 7 quantity claims were kept with reason null, and the gap "Whether the titre doubled at pH7 is measured nowhere in the project" was kept. The kept d1 came back with `support: "direct"`, `provenance: "unverified"`, the quote "Saccharomyces cerevisiae ferments glucose to ethanol under anaerobic conditions." and `values: []`. `practice.check_text` refused six of the same seven words: "doubled", "halved", "quadrupled", "x10", "pH7" and "pH-4". It accepted "Table IV".
- **Likely cause:** `_WORD_NUMBERS` at `core/openferment_core/validate.py:66-73` holds counts, ordinals and "once twice thrice" and no multiplying verb, and neither it nor `_DIGIT` (`validate.py:60`) covers an ASCII Roman numeral such as "IV"; `_IDENTIFIER` at `validate.py:105` blanks any letters-then-digit span before the digit search, so "pH7", "pH-4" and "x10" read as identifiers; `validate_plan` (`validate.py:416`) and `held_to_rule_one` (`core/openferment_core/postdoc_agent.py:646`) rely on `find_number` alone. The check that catches these words, `PRACTICE_QUANTITY` (`core/openferment_core/practice.py:73-80`), serves practice drafts alone. (confidence: high)
- **Fix size:** medium: the word list and the identifier carve-out in `validate.py`, or `PRACTICE_QUANTITY` folded into `find_number`, held against the false-positive cases the validator is tuned on.
- **Severity:** S3, the reading of the refuting agent and of the entry's writer. An independent severity panel read S1: Postdoc's loop keeps and returns the claim 'Ethanol titre roughly doubled under anaerobic conditions' with support 'direct', values [] and a quote that states no doubling.
- **Stood on:** the first refutation.

#### H9-05 · S3 · Contract break · postdoc_agent's ask budget (_turn_tokens, _out_of_budget)

A Postdoc question whose turns write their whole room spends past `OPENFERMENT_ASK_BUDGET_USD` by one answer turn, 0.9105 USD at the default 0.75 USD and 2.1605 USD at 2.00 USD on Opus. The refuting pass confirmed these two budgets. It set aside the zero-budget case, where any answer turn at all passes the cap.

- **Contract:** `docs/decisions/ADR-008-postdoc-memory-routing.md:101-102`, "the loop stops asking for tools when what it spent and what the answer could cost reach the question's budget, so the answer is paid for within it"; and `core/openferment_core/postdoc_agent.py:545-546`, "so the answer is always paid for within the question's budget".
- **Reproduce:** `bash bughunt/repro/H9-05/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** The question's total cost stays at or under the ask budget whenever each turn costs at most the loop's own worst case for it (`llm.worst_case_usd`). The loop asks its last round at a size that leaves the answer's worst case inside what is left.
- **Observed:** Both runs gave the same figures, with every turn at or under its worst case and every question stopped 'cost'. At 0.75 USD round one got 27,360 tokens, a worst case of 0.7500 USD, the whole budget, and cost 0.6486 USD; the answer turn at 8,000 tokens added 0.2619 USD, 0.9105 USD in all. At 2.00 USD four turns (32,000, 32,000, 15,622 and 8,000 tokens) spent 2.1605 USD.
- **Likely cause:** `_attempt` asks `_out_of_budget` at `core/openferment_core/postdoc_agent.py:597`, after a round has spent, and prices no next round together with the answer; `_turn_tokens` at `postdoc_agent.py:537` (`left = budget_usd - run.spent.costUsd - read`) gives a round every dollar left, and the answer turn then runs at the `MIN_TOKENS` floor (`:540`) on top of it. (confidence: high)
- **Fix size:** small: the stop check in `_attempt` and the round sizing in `_turn_tokens`, so each round is asked at a size that leaves the answer's worst case inside the budget, with a test at the real prices.
- **Stood on:** the first refutation.

#### H9-06 · S3 · Contract break · llm.routes and RoutesInvalid at the answer path

With `OPENFERMENT_ROUTES` set to a table `llm.routes()` refuses (the reproduction used `{"plan": {"models": []}}`), `POST /api/ask` and `POST /api/intake/{id}/extract` each answer 500 Internal Server Error and the `RoutesInvalid` words reach the service log alone. The stream route and the tool door, which the hunt also named, answer in words of their own and are left out of this entry.

- **Contract:** `core/openferment_core/api.py:554`, the docstring of `POST /api/ask`, "Every failure below returns a plan with `declined` set"; and `docs/decisions/ADR-008-postdoc-memory-routing.md:82-83`, "refused in words when it cannot route (`RoutesInvalid`, and `pnpm ready` fails on it)", which carries the extraction route.
- **Reproduce:** `bash bughunt/repro/H9-06/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** `POST /api/ask` answers 200 with a plan whose `declined` holds the `RoutesInvalid` words, "OPENFERMENT_ROUTES.plan.models is a list of model specs", the way the keyless control answers 200 with `declined` set. The extraction route refuses in words, for example a 503 with the words as its detail, as it does for a missing key.
- **Observed:** In both runs, under the table on port 10040, `POST /api/ask` answered `[500] Internal Server Error` and `POST /api/intake/<doc>/extract` answered `[500] Internal Server Error`. On the same port in both runs, `GET /api/health` answered 200. The control on port 10041, with no table, answered `[200]` with `declined` "ANTHROPIC_API_KEY is not set. Put it in core/.env (gitignored) and restart the service." The log on 10040 held 2 unhandled exceptions and 4 lines naming `RoutesInvalid`, one raised through `postdoc_agent.py` line 709 into `llm.routes` with the words "OPENFERMENT_ROUTES.plan.models is a list of model specs", the other through `extract.py` line 328 into `llm.call` at `llm.py` line 804.
- **Likely cause:** `core/openferment_core/postdoc_agent.py:709-710` calls `llm.chain("plan")` and `llm.routes()["plan"]` outside the `try` that turns `ModelRefused` and `ModelUnavailable` into a declined plan, a few lines below the handler that turns `spend.BudgetSettingInvalid` into one (`:701-704`), so the `RoutesInvalid` reaches `_answer` (`core/openferment_core/api.py:537-543`), which marks the turn failed and re-raises; on the extraction route `extract.call_model` (`core/openferment_core/extract.py:328`) calls `llm.call`, whose `routes()[family]` at `core/openferment_core/llm.py:804` raises the same `ValueError` subclass, and no handler in `call_model` or `intake_extract` (`api.py:2018-2034`) maps it to a status in words. (confidence: high)
- **Fix size:** small: a `RoutesInvalid` clause in `postdoc_agent.ask` beside the `BudgetSettingInvalid` one, and one in `extract.call_model` or `intake_extract` that answers a 503 in words.
- **Stood on:** the first refutation.

#### H9-08 · S3 · Contract break · spend._setting, the daily and ask caps

`spend._setting` accepts `nan` and `inf` as budget settings: a daily cap of `nan` holds a 1000 USD call and ready marks its spend row ok, and an ask budget of `nan` or `inf` makes every ask raise, so `POST /api/ask` answers HTTP 500 and keeps the turn failed.

- **Contract:** `core/openferment_core/spend.py:57`, which refuses a setting "which is not a number of dollars" (`BudgetSettingInvalid`); `core/openferment_core/api.py:554`, "Every failure below returns a plan with `declined` set".
- **Reproduce:** `bash bughunt/repro/H9-08/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** A daily cap or an ask budget of `nan` or `inf` is refused as `BudgetSettingInvalid` in words, as `-1` is. No call is held against it, ready's spend row reads fail, and `POST /api/ask` returns HTTP 200 with `declined` set.
- **Observed:** A daily cap of `nan` was read as `nan`, a 1000 USD call was held (`reservedUsd now 1000.000128`), and ready printed `[ok] spend $0.00 of the $nan daily cap spent today (2026-11-10, UTC)`; a cap of `inf` gave the same with `$inf`. An ask budget of `nan` raised `ValueError: cannot convert float NaN to integer` and `inf` raised `OverflowError: cannot convert float infinity to integer`, each with 0 model calls. Through the service, an ask budget of `-1` answered HTTP 200 with `declined` set. Through the service, an ask budget of `inf` answered HTTP 500 `Internal Server Error` with the turn kept `status='failed'`, `error='Postdoc failed while answering: OverflowError.'`.
- **Likely cause:** `core/openferment_core/spend.py:58`: `_setting` tests the parsed float with `value < 0` alone, which is false for `nan` and `inf`, so `spent + reserved + projected_usd > cap` (spend.py:162) never trips on a `nan` cap, and `int(left / per_token)` (postdoc_agent.py:540) raises on a `nan` or infinite budget, which passes the loop's handlers (postdoc_agent.py:719-723) to `api._answer`, where it is re-raised as a 500 (api.py:540-543) (confidence: high).
- **Fix size:** small, a finiteness test (`math.isfinite`) in `spend._setting` and tests for `nan` and `inf`.
- **Stood on:** the first refutation.

#### H9-09 · S3 · Contract break · spend.reserve and spend.settle across midnight

A call reserved before 00:00 UTC is checked against the old day. It settles its cost onto the new day, whose check never counted its hold, so a second call held just after midnight takes the new day to 1.80 USD against a 1.00 USD cap.

- **Contract:** `core/openferment_core/llm.py:37-39`, "a call whose worst case could take the UTC day past `OPENFERMENT_DAILY_BUDGET_USD` is refused before it is sent (`BudgetExhausted`)"; `CLAUDE.md:140` names "Spend above the daily cap." as a stop condition.
- **Reproduce:** `bash bughunt/repro/H9-09/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** With a 1.00 USD cap, two calls whose worst case is 0.90 USD each never both spend on one UTC day. Either the call held at 23:59:30 counts against the new day while it is in flight, so the 0.90 USD call asked at 00:00:10 is refused, or its cost goes to the day that held it.
- **Observed:** The one-day control refused the second 0.90 USD reservation (`today $0.00 spent and $0.90 reserved of the $1.00 cap`). Across midnight, the new day's check at 00:00:10 read `reservedUsd` 0 with A's 0.90 in flight, B's 0.90 reservation was held, and A's settlement at 00:00:40 landed on 2026-11-11. The ledger ended with 2026-11-10 at 0.00 USD and 2026-11-11 at 1.80 USD in 2 calls against the 1.00 USD cap (rows `2026-11-11|settled|0.900000` twice).
- **Likely cause:** `core/openferment_core/spend.py:182`: `_settle` takes `day = today()` at settle time and inserts the cost under that day (spend.py:188-191), and `_day_state` (spend.py:118) reads the rows of the queried day alone, so `_reserve`'s check on the new day (spend.py:160-162) never sees the old day's unexpired hold (confidence: high).
- **Fix size:** small, `_settle` writes the cost on the reservation's own day, or a day's check counts every unexpired hold.
- **Stood on:** the first refutation.

#### H9-10 · S3 · Contract break · postdoc_agent.ask restart, llm routes

Postdoc's loop asks at most two models of the plan route, so with a plan route of `claude-opus-5-5`, `claude-sonnet-5-5`, `claude-haiku-5-5` and the first two unavailable the question declines after sonnet, and haiku receives no request. Under that route, `GET /api/health` lists haiku among the fallbacks.

- **Contract:** `docs/api/postdoc.md:193-195`, `llm.ROUTES` "gives each family its default route: the models tried in order, each after the one before it declines or is unavailable", and the table at line 200 names the `plan` family's calls "Postdoc's loop"; and `core/openferment_core/api.py:485-486`, the health field `fallbackModel` is "The models the route moves to, in order, when its first declines or is unavailable".
- **Reproduce:** `bash bughunt/repro/H9-10/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** The loop asks the plan route's models in order, each after the one before it is unavailable: opus, then sonnet, then haiku. Haiku's plan is the answer, and the trace ends "Answered: ...", as the control's trace ends when sonnet answers.
- **Observed:** In both runs `llm.chain("plan")` read `['claude-opus-5-5', 'claude-sonnet-5-5', 'claude-haiku-5-5']`, and `GET /api/health` gave `fallbackModel` "claude-sonnet-5-5, claude-haiku-5-5". With opus and sonnet unavailable the loop asked `['claude-opus-5-5', 'claude-sonnet-5-5']`, declined with "claude-sonnet-5-5 answered 529: overloaded", and wrote the last trace step "No answer: claude-sonnet-5-5 answered 529: overloaded". The control, with opus unavailable, restarted on sonnet and ended "Answered: 0 claims kept, 0 dropped".
- **Likely cause:** `core/openferment_core/postdoc_agent.py:714` loops `for i, model in enumerate(models[:2]):` and `:728` breaks once `i + 1 >= min(len(models), 2)`, so the loop restarts at most once whatever the plan route holds. The module docstring at `:28` states that cap ("restarts the question once on the next model"). `llm.call` (`core/openferment_core/llm.py:859`) walks every model of a route. (confidence: high)
- **Fix size:** small: walk the whole plan chain at `postdoc_agent.py:714` and `:728`, or state the one-restart cap in `docs/api/postdoc.md`, `llm.py`'s routing notes and the health field's words.
- **Stood on:** the first refutation.

#### H9-11 · S3 · Contract break · mcp_server.ask_postdoc, the conversation store

A question asked through `ask_postdoc` on the `openferment` MCP server in its own process (no `--service`, as `.mcp.json` starts it) leaves the project no conversation, no turn and no tool-call rows. The verdict confirmed those missing rows. This entry leaves out turn events, since the event stream lives in the service's process memory (`core/openferment_core/events.py:18-19`).

- **Contract:** `docs/api/postdoc.md:3`, "Postdoc keeps each question as a turn of a conversation under the project"; and `docs/BASE.md:54-55`, which names Postdoc's doors as "its screen, its ask routes and the `openferment` MCP server's `ask_postdoc`".
- **Reproduce:** `bash bughunt/repro/H9-11/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** After the MCP ask the project holds one conversation and one turn, with any tool calls kept under the turn, as `POST /api/ask` keeps the same question on the same database.
- **Observed:** In both runs the MCP answer carried `conversationId` null and `turnId` null, and the counts after it read conversations=0 turns=0 tool_calls=0. The same question at `POST /api/ask` answered with a `conversationId` and a `turnId` (`lc-8fa43edc7470` and `turn-ebacd3a8f354` in run 1) and left conversations=1 turns=1, with 5 turn events on the stream. Both asks declined in the same words, "ANTHROPIC_API_KEY is not set. Put it in core/.env (gitignored) and restart the service.", so tool_calls read 0 after each door.
- **Likely cause:** `core/openferment_core/mcp_server.py:417` calls `postdoc_agent.ask(question, ctx=tools.ToolContext(project=acting))` with no `on_call` or `on_result` hook and no `conversations.begin` or `finish` around it, and all the keeping sits in `api._answer` (`core/openferment_core/api.py:502-547`: `begin` at 510, the tool-call hooks at 527-535, `finish` at 545), which `mcp_server` does not import. (confidence: high)
- **Fix size:** medium: move the turn keeping in `api._answer` (begin, the tool-call hooks, finish) into a function the in-process `ask_postdoc` branch also calls.
- **Severity:** S3, the reading of the refuting agent and of the entry's writer. An independent severity panel read S2: `.mcp.json` starts the openferment server in its own process, so an ordinary ask_postdoc question in the default setup leaves the project no conversation, no turn and no tool-call rows, and the answer is missing from the record a person later inspects.
- **Stood on:** the first refutation.

#### H9-12 · S3 · Contract break · tools.run / numbers_in

A `study_scenario` call whose `values[].quantity.value` is a 400-digit JSON integer makes `tools.run` raise `OverflowError`, so `POST /api/tools/study_scenario` answers 500 and the MCP server answers `isError` true with the words "Error executing tool study_scenario" and no reason.

- **Contract:** `core/openferment_core/tools/__init__.py:502-503`, `run`: "Every refusal is a result with `error` set; nothing here raises."; and `docs/TOOLS.md:896`, for the MCP door: "A tool's refusal is its ToolResult with `error` set" and "`is_error` stays false".
- **Reproduce:** `bash bughunt/repro/H9-12/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** `tools.run` refuses the value in words, as it refuses the `1e309` control: a ToolResult whose `error` says the value is NaN or infinite, answered 200 at the REST door and as JSON with `isError` false over MCP.
- **Observed:** In both runs `tools.run` raised "OverflowError: int too large to convert to float" at `tools/__init__.py:415` (`numbers_in`, reached from `run` at :516). `POST /api/tools/study_scenario` answered "Internal Server Error" [500] with that traceback in the service log, and the MCP server in its own process answered `isError=True` with the text "Error executing tool study_scenario". The `1e309` control got "study_scenario refused: values[0].quantity.value holds a number that is NaN or infinite, and a number a tool takes is finite; nothing ran" at all three doors, [200] at REST and `isError=False` over MCP.
- **Likely cause:** `core/openferment_core/tools/__init__.py:415` evaluates `math.isfinite(float(v))`, and `float()` raises OverflowError on an int past a float's range; `non_finite_in` (:425) tests float values, so the integer passes it, and `run` calls `numbers_in` at :516, ahead of the `try` at :547 that turns an exception into a ToolResult. (confidence: high)
- **Fix size:** small: treat an int that `models.float_holds` (`core/openferment_core/models.py:846`) rejects as non-finite in `non_finite_in` and `numbers_in`, so it gets the NaN-and-infinity refusal.
- **Stood on:** the first refutation.

### S4: 23 findings here, 24 with the paid debts above

#### H1-10 · S4 · Contract break · GET /api/engines workerStatus: simulator.status

After the Proforma worker process dies, `GET /api/engines` lists `biosteam` and `train` with `workerStatus` `ready` and `GET /api/proforma/status` answers `ready`; the refuting pass holds this against the simulator's docstring and the status route's docstring, and leaves open which state a dead worker should read.

- **Contract:** `core/openferment_core/engine/simulator.py:7-8`, "`status()` says where it is: `cold`, `starting`, `ready` or `failed`, so the screen can say the simulator is starting"; and `core/openferment_core/api.py:919` (`GET /api/proforma/status`), "Where the BioSTEAM worker is (§8.1): cold, starting, ready or failed."
- **Reproduce:** `bash bughunt/repro/H1-10/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** The status says where the worker is, so with no Proforma worker process alive the engine listing and the status route report a state that tells the screen the simulator has to start again. The contract names no state for a worker that died, so the exact value (`cold` or `failed`) stays open.
- **Observed:** In both runs the warm start read `ready` after 15 s, with 1 Proforma worker alive and `biosteam=ready train=ready`. After SIGKILL (pid 26727, then pid 28549) 0 workers were alive, `GET /api/engines` listed `biosteam=ready train=ready`, `GET /api/proforma/status` answered `ready`, and 0 workers were alive after both reads. The `WorkerEngine` control read `before first use=cold after an answer=ready after its worker was killed=cold`.
- **Likely cause:** `core/openferment_core/engine/simulator.py:43-44`: `status()` returns `dict(_STATE)`, which `_warm` sets to `ready` at line 50 and no path sets back, `call` (line 87) hands each request to `SimWorker.call`, which restarts a dead process in silence (`core/openferment_core/workers/__init__.py:186-189`), and `BiosteamEngine.status` (`core/openferment_core/engine/biosteam.py:228-230`) and `TrainEngine.status` (`core/openferment_core/pureos/engine.py:222-224`) read that kept state. (confidence: high)
- **Fix size:** small: `simulator.status()` checks that the worker process is alive once the state reads `ready`, and `call` sets the state back after a crash or a timeout.
- **Severity:** S4, the reading of the refuting agent and of the entry's writer. An independent severity panel read S3: After the Proforma worker process dies, `GET /api/engines` and `GET /api/proforma/status` both read `ready` with no worker alive, and the next call restarts the worker in a silent cold start of about 15 s.
- **Stood on:** the first refutation.

#### H10-03 · S4 · Contract break · literature/kit.py rest_app (the /rag mount)

Four doors under `/rag` (`/rag/health`, `/rag/v1/corpus-manifest`, `/rag/docs` and `/rag/openapi.json`) answer 200 to a request with no key, both with `OPENFERMENT_RAG_KEY` unset and with a key set, and the manifest gives the named project's document and chunk counts. The refuting pass confirmed this part. It left the manifest's endpoint, embedder and feature fields unconfirmed, since no cited contract sentence covers them.

- **Contract:** `docs/decisions/ADR-002-sci-rag-kit.md:107-108`, "with none set a key made in memory and never shown stands in, so `/rag` refuses every request"; and `CLAUDE.md:67`, "its REST serves under `/rag` behind `OPENFERMENT_RAG_KEY`".
- **Reproduce:** `bash bughunt/repro/H10-03/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** With no key set, `/rag` refuses every request. With a key set, every `/rag` request that lacks the key is refused, as `/rag/v1/status` and `/rag/v1/documents` already refuse with 401.
- **Observed:** Both runs gave the same lines once the ports and the random key are masked. With no key set, `/rag/v1/status` and `/rag/v1/documents` answered 401. In the same setting, `/rag/health`, `/rag/v1/corpus-manifest`, `/rag/docs` and `/rag/openapi.json` answered 200 to a request with no key, the manifest giving project r1's stats `{"documents": 1, "chunks": 1, "entities": 0, "communities": 0}`. With a throwaway key set, `/rag/v1/status` answered 401 to no key and to a wrong key. It answered 200 to the key. With that key set, `/rag/v1/corpus-manifest`, `/rag/health` and `/rag/openapi.json` answered 200 to all three, no key, a wrong key and the key.
- **Likely cause:** `core/openferment_core/literature/kit.py:848-849` mounts the kit's `create_app` whole and removes the `/mcp` mount alone, the kit's `sci_rag/server/routers/meta.py:21` (`/health`) and `:41` (`/v1/corpus-manifest`, "deliberately unauthenticated" at lines 3-6) carry no `require_scopes`, FastAPI's `/docs` and `/openapi.json` carry no dependency, and so the key map from `kit.py:188-193` reaches none of the four. (confidence: high)
- **Fix size:** small: a key check over every route `rest_app` keeps, or the four routes dropped from the mount, and the no-key test at `core/tests/test_literature_kit.py:235-242` extended to them.
- **Severity:** S4, the reading of the refuting agent and of the entry's writer. An independent severity panel read S3: A keyless request to /rag/health, /rag/v1/corpus-manifest, /rag/docs or /rag/openapi.json gets 200 and the named project's document and chunk counts, with the key unset and with it set. ADR-002 and pnpm ready's row say /rag refuses every request.
- **Stood on:** the first refutation.

#### H10-05 · S4 · Drift · guard.py docstring

The module docstring of `core/openferment_core/guard.py` lists the hosts the service answers to as an IP address, a name with no dot, a `.local` name, a `.ts.net` name and a name `OPENFERMENT_ALLOWED_HOSTS` lists. It leaves out `.localhost`, which `OWN_SUFFIXES` holds and the guard admits.

- **Contract:** `core/openferment_core/guard.py:22-24`, "A host this service answers to: an IP address, a name with no dot, a `.local` name (Bonjour), a `.ts.net` name (Tailscale's names for the owner's devices), or one listed in OPENFERMENT_ALLOWED_HOSTS."; and `core/tests/test_openapi.py:53`, which holds the OpenAPI description to `guard.OWN_SUFFIXES` as "every name the guard admits, as guard.py lists".
- **Reproduce:** `bash bughunt/repro/H10-05/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** The docstring's list names every suffix in `OWN_SUFFIXES` (`core/openferment_core/guard.py:37`), `.local`, `.localhost` and `.ts.net`, as the OpenAPI description written from `OWN_SUFFIXES` does.
- **Observed:** In both runs `POST /api/biorepo/check` with body `{}` under `Host: evil.localhost:9470` got 422 from the endpoint's body validation, so the guard let it through, and `evil.local:9470` got 422. In both runs the control `evil.example.com:9470` got 403 "this service does not answer to 'evil.example.com'. Add the name to OPENFERMENT_ALLOWED_HOSTS if it is yours". The docstring check read `{'.local': True, '.localhost': False, '.ts.net': True}` against `OWN_SUFFIXES = ('.local', '.localhost', '.ts.net')`. `docs/api/openapi.json` said "a name ending `.local`, `.localhost` or `.ts.net`".
- **Likely cause:** `core/openferment_core/guard.py:22-24` is a list written by hand that names two of the three suffixes at `guard.py:37`. The list and `OWN_SUFFIXES` both arrived in one commit, `4b8d872`, so the gap dates from the first draft. `core/openferment_core/api.py:200` builds the description from `OWN_SUFFIXES`, which keeps it in step with the code. (confidence: high)
- **Fix size:** small: one phrase in the docstring, a `.localhost` name (the loopback names RFC 6761 reserves).
- **Stood on:** the first refutation.

#### H11-07 · S4 · Hollow test · core/tests/test_host.py

`test_the_nightly_dumps_before_the_nights_work_and_counts_a_failed_dump` checks substrings of `scripts/host/nightly.sh`'s text, so a nightly.sh with its dump line commented out keeps all three dump tests green. With that nightly.sh, the night makes no dump.

- **Contract:** `core/tests/test_host.py:5-7`, "lib.sh's reading of core/.env, its database step and the night's dump run against stand-ins for Homebrew and the PostgreSQL tools." The test's name at `core/tests/test_host.py:347`, "test_the_nightly_dumps_before_the_nights_work_and_counts_a_failed_dump", says what it holds.
- **Reproduce:** `bash bughunt/repro/H11-07/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** Commenting out `scripts/host/nightly.sh:33` (`backup_database || status=$?`), which leaves the night making no dump, fails at least one test.
- **Observed:** In both runs the tree as it is gave 53 passed, and its night on stand-ins made 1 pg_dump call, kept 1 dump and exited 0. With line 33 deleted, 1 failed and 52 passed, the failure being `tests/test_host.py::test_the_nightly_dumps_before_the_nights_work_and_counts_a_failed_dump`. With line 33 reading `# backup_database || status=$?`, 53 passed with the three dump tests PASSED PASSED PASSED. With that commented line, the night made 0 pg_dump calls, kept 0 dumps in `~/openferment-backups`, ran extract, nightly_checks, checks propose and checks brief, and logged "done, exit 0".
- **Likely cause:** `core/tests/test_host.py:349` asserts `"backup_database || status=$?" in text` and line 350 asserts that `"backup_database ||"` stands before `"openferment_core.extract"`, both on nightly.sh's raw text, and a commented line carries both substrings. The other two dump tests (`test_host.py:319`, `:339`) call lib.sh's `backup_database` through `_lib`. They never run nightly.sh. (confidence: high)
- **Fix size:** small: the test runs nightly.sh on `_dump_stand_ins`'s stand-ins with a stand-in `core/.venv/bin/python`, then asserts the pg_dump call comes before the extract call and a failed dump gives a non-zero exit.
- **Severity:** S4, the reading of the refuting agent and of the entry's writer. An independent severity panel read S2: The test reads nightly.sh as text, so a nightly.sh with its dump line commented out keeps all three dump tests green. That night makes no pg_dump call, keeps no dump and logs 'done, exit 0', with no pnpm ready row for backups.
- **Stood on:** the second refutation, by the kind's own standard. The first set it aside because it read the docstring at `core/tests/test_host.py:3-8` as met by the two tests that run lib.sh's `backup_database` on stand-ins, with nightly.sh itself held to a syntax check and its full run placed on macOS.

#### H11-08 · S4 · Inconsistency · host scripts: `has_key` in scripts/host/lib.sh against pnpm ready and /api/health

On a core/.env with two `ANTHROPIC_API_KEY` lines, install.sh's key message gives the opposite answer to `pnpm ready`'s key row and `GET /api/health`'s `hasKey`. `has_key` greps every key line of the file. The service and ready take the file's last key line through python-dotenv. Those two rules make the split.

- **Contract:** `scripts/host/lib.sh:88`, "True when core/.env holds something shaped like a real key. Never prints it." The two doors answer the one question in the same words: `scripts/host/install.sh:52` prints "core/.env holds a key." and `core/openferment_core/ready.py:88` reports "core/.env holds a key", from the value `load_dotenv(CORE / ".env", override=False)` sets at `ready.py:638`, as `core/openferment_core/api.py:178` sets it for the service.
- **Reproduce:** `bash bughunt/repro/H11-08/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** For one core/.env, install.sh says a key is held exactly when `pnpm ready`'s key row and `/api/health`'s `hasKey` say so.
- **Observed:** In both runs, file B (the example's placeholder line `ANTHROPIC_API_KEY=sk-ant-...`, then a key line) gave install.sh's "core/.env holds no key yet. The app runs; Postdoc and extraction wait for one." In both runs, file B gave ready's "✓ key core/.env holds a key" and `hasKey True`. File C (a key line, then `ANTHROPIC_API_KEY=`) gave install.sh's "core/.env holds a key." File C gave ready's "✗ key core/.env holds no key" and `hasKey False`. The one-line control A agreed at all three doors.
- **Likely cause:** `scripts/host/lib.sh:90-92`: two `grep -qE` calls run over every line of core/.env, one asking for any `^ANTHROPIC_API_KEY=sk-ant-` line and one refusing when any line is the placeholder, so the answer comes from all the file's key lines. `env_setting` at `lib.sh:111` keeps each other name's last line (`tail -1`), which is python-dotenv's rule. (confidence: high)
- **Fix size:** small: `has_key` tests the file's last `ANTHROPIC_API_KEY` line alone, as `env_setting` does at `lib.sh:111`; the change alters how a key is read, a stop condition, so it goes to the owner with question 13 (`docs/PROGRESS.md:669`).
- **Severity:** S4, the reading of the refuting agent and of the entry's writer. An independent severity panel read S3: On a core/.env with two ANTHROPIC_API_KEY lines, install.sh's has_key message gives the opposite answer to pnpm ready's key row and the service's hasKey (placeholder then key: install says no key.
- **Stood on:** the second refutation, by the kind's own standard. The first set it aside because it read `scripts/host/lib.sh:95-105` as keeping the last-line rule to the names other than the key and found no written text that asks `has_key` to agree with python-dotenv.

#### H12-08 · S4 · Hollow test · guard.key_refusal, llm.request_key (test_key_override.py)

No test holds `guard.key_refusal`'s Funnel rule, since the one Funnel case in `core/tests/test_key_override.py` is a POST that `guard.refusal` refuses first; the refuting pass confirmed this half. It read the second half, no test of `llm.request_key`'s blank-key rule, as a missing unit test on a helper whose one caller answers a blank header 422 first.

- **Contract:** `core/openferment_core/guard.py:98-99` (`key_refusal`), "never one through Tailscale Funnel from the public internet. Read or change alike, since a key spends."; and `core/openferment_core/llm.py:698` (`request_key`), "An empty key is none, and core/.env's serves."
- **Reproduce:** `bash bughunt/repro/H12-08/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** Each rule has a test that fails once the rule is dropped: with the Funnel rule dropped, a test sees a GET through Funnel naming a key answered 200, and with the blank-key rule dropped, a test sees `request_key('  ')` set `key_named()` True.
- **Observed:** In both runs the tree answered the Funnel `GET /api/audit` naming a key with 403 "a request through Tailscale Funnel comes from the public internet and may not name a key", and `request_key('  ')` gave `key_named()=False`. With M31 (`if FUNNEL in headers:` made `if False:`) the same GET got 200 with `key_held=True` and a `key_override` audit row for `GET /api/audit`, and `test_key_override.py`, `test_request_guard.py` and `test_llm.py` gave 130 passed (5.10 s, then 6.51 s); with M28 (`_REQUEST_KEY.set(key)`) `request_key('  ')` and `request_key('')` each gave `key_named()=True` and whose='the key this request named', and the same tests gave 130 passed (5.43 s, then 5.44 s). The control, `guard.refusal`'s Funnel rule dropped, gave 1 failed, 129 passed in both runs.
- **Likely cause:** `core/tests/test_key_override.py:128` sends the one Funnel case as `POST /api/ask`, the guard middleware registered at `core/openferment_core/api.py:457` runs ahead of the key middleware at `api.py:349`, and so `guard.refusal` (`core/openferment_core/guard.py:113-114`) answers 403 with a detail that also holds "Funnel" before `key_refusal` (`guard.py:100-101`) runs; the blank-key rule at `core/openferment_core/llm.py:699` sits behind `api.py:364-365`, which answers a blank header 422 first. (confidence: high)
- **Fix size:** small: a Funnel GET naming a key in `test_key_override.py`, and a unit test that calls `request_key` with a blank key and an empty key.
- **Severity:** S4, the reading of the refuting agent and of the entry's writer. An independent severity panel read S3: Judged by what the gap lets through: with M31 a GET through Tailscale Funnel naming a key answered 200, held the key for the request and kept a `key_override` row, a request guard.py:98-99 and the runbook at :148 refuse, and 130 tests passed.
- **Stood on:** the first refutation.

#### H12-09 · S4 · Hollow test · request guard tests: the suffix check in guard.answers_to (core/tests/test_request_guard.py)

The six hostile Hosts the tests in core/tests send end in `.com`, `.org` and `.example`. None of them ends in `.net`, so a guard that answers to every `.net` name (mutation M32 at `core/openferment_core/guard.py:78`) passes the guard's three test files and lets a rebound name such as `rebind.evil.example.net` write a project.

- **Contract:** `core/openferment_core/guard.py:22-26`, "A host this service answers to: an IP address, a name with no dot, a `.local` name (Bonjour), a `.ts.net` name (Tailscale's names for the owner's devices), or one listed in OPENFERMENT_ALLOWED_HOSTS. Each of these is answered by the owner's own network or by Tailscale; a rebinding attack needs a public domain whose DNS the attacker answers, and none of these is one." `CLAUDE.md:52` makes the guard the service's protection: "the loopback bind and `core/openferment_core/guard.py` are the access control until accounts exist".
- **Reproduce:** `bash bughunt/repro/H12-09/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** A guard test sends a public name ending in `.net` outside `.ts.net`, such as `rebind.evil.example.net`, and asserts a 403, so a guard that answers to every `.net` name fails a test, as the control's `.com` guard does.
- **Observed:** Both runs found six refused Hosts in core/tests (`rebind.evil.example.com` at `test_request_guard.py:38, 73, 115, 165`, `openferment.example.org` at `:120`, `evil.example` at `test_key_override.py:131`), 0 of them ending in `.net`, and on the head `POST /api/projects` with Host and Origin `rebind.evil.example.net:8000` answered 403 and the database held `[]`. The control guard that answers every `.com` name failed 2 tests with 37 passed (exit 1). With M32 (`host.endswith((*OWN_SUFFIXES, ".net"))`), `test_request_guard.py`, `test_key_override.py` and `test_projects.py` gave "58 passed" with exit 0 (4.63 s and 3.93 s), and the same POST answered 201 and left the project `made-through-a-rebound-name` in the database.
- **Likely cause:** `core/tests/test_request_guard.py:36-41` and `:70-77` send one hostile public domain, `rebind.evil.example.com`, and `:119-123` refuses `openferment.example.org` before listing it; with no refused `.net` Host, the suffix check at `core/openferment_core/guard.py:78` (`host.endswith(OWN_SUFFIXES)`, with `OWN_SUFFIXES = (".local", ".localhost", ".ts.net")` at `:37`) can widen past `.ts.net` and every guard test stays green. (confidence: high)
- **Fix size:** small: one parametrized refusal beside `test_request_guard.py:38` for `rebind.evil.example.net` and for `evilts.net` (a name ending in `ts.net` without its dot), each expecting 403.
- **Severity:** S4, the reading of the refuting agent and of the entry's writer. An independent severity panel read S3: Judged by what the gap lets through: with the suffix check widened to every `.net` name, a POST with Host and Origin `rebind.evil.example.net:8000` answered 201 and left the project `made-through-a-rebound-name`, and 58 tests passed.
- **Stood on:** the second refutation, by the kind's own standard. The first set it aside because it read `guard.py:22-26` as a description of the guard's behaviour, which the head keeps, and found that text silent on which hostile names a test sends.

#### H12-12 · S4 · Hollow test · deposition readings: measurements.corrected_by (core/tests/test_measurements.py)

No test in core/tests asks which entry corrects a reading corrected twice, so a `corrected_by` that names the first correction (mutation M37 at `core/openferment_core/measurements.py:104`) passes `test_measurements.py`, `test_basis.py` and `test_finite_inputs.py`, and under it a run's refusal names the first correction and calls it the reading that stands.

- **Contract:** `core/openferment_core/measurements.py:91-94`, "The id of the entry that corrects `entry` in its deposition, or None when `entry` is the reading that stands for its measure: the latest entry on the same measure that shares its sample time, or that has none when `entry` has none". The module's `standing` rule at `measurements.py:19-26` adds "a later entry still waiting to be read back corrects it too, and the refusal says the newer number waits".
- **Reproduce:** `bash bughunt/repro/H12-12/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** For a reading de-1 corrected by de-3 (read back) and again by de-10 (waiting), `corrected_by` names de-10 and the refusal says de-10 waits; a test of such a reading fails when the first correction is named.
- **Observed:** On the tree both runs gave `corrected_by(de-1) = de-10` and the refusal "reading dep-asis/de-1 was corrected by dep-asis/de-10, which waits for a person to confirm its number at the bench". With M37 (`later[-1]` becomes `later[0]`) they gave `corrected_by(de-1) = de-3` and "reading dep-m37/de-1 was corrected by dep-m37/de-3, the reading that stands for its measure now", and de-3 is itself corrected by de-10. The three test files gave "139 passed" with exit 0 (8.22 s and 8.05 s), and the count of tests asking about a reading corrected twice was 0.
- **Likely cause:** `core/tests/test_measurements.py:161-165` deposits de-1, de-3 and de-10 on one measure and asks about de-3 alone, and `:125-126` and `:201-206` give each reading they ask about a single later entry, so the index at `core/openferment_core/measurements.py:104` (`return str(later[-1].get("id")) if later else None`) decides no test's answer. (confidence: high)
- **Fix size:** small: one assertion in `core/tests/test_measurements.py` that `corrected_by` names de-10 for de-1 in the deposition of `:161-165`, with the refusal's words for de-1.
- **Stood on:** the second refutation, by the kind's own standard. The first set it aside because it read `measurements.py:19-26` and `:91-95` as behaviour the tree keeps and found no written rule that asks for a test of a reading corrected twice.

#### H12-13 · S4 · Hollow test · basis.is_measurement

No test in `core/tests/` builds a deposition source whose id is reading-shaped and whose note differs from `measured on <at>`, so dropping the note clause of `basis.is_measurement` (mutation M05) passes the tests that reach it and lets a fermOS fit kept through `POST /api/fermos/fit` for `depositionId` `dep-b1/de-1` be labelled `measured`.

- **Contract:** `core/openferment_core/basis.py:197-200`, "a deposition naming one reading, `<deposition id>/<entry id>`, its note saying when the reading was taken. A deposition naming a whole series (the readings a kinetic fit is made on, fermos.py) is the bench's record the fit rests on." `docs/decisions/ADR-006-quantities-and-estimates.md:190-192` adds "A deposition source naming a whole series (the readings a kinetic fit is made on) reads back as the bench's record, as it did, and the fit's provenance stays what it was."
- **Reproduce:** `bash bughunt/repro/H12-13/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** A test builds a deposition source with a reading-shaped id and fermOS's series note, holds it to the bench's record (`is_measurement` False, origin `record`), and holds a fit resting on it to `computed`. With the note clause dropped, that test fails.
- **Observed:** Both runs scanned 36 deposition sources and fits built in `core/tests/` and found 0 with a reading-shaped id and a note other than `measured on`; with M05 and a counter applied, the hunt's eight test files and the two `test_engines.py` tests that build a reading gave "225 passed" with exit 0 (51.39 s and 55.71 s), and the counter recorded 0 calls the note clause decided. On the probe database the tree read `dep-b1/de-1` with fermOS's series note as `is_measurement=False`, origin `record`, `basis_provenance=computed`, and kept `fermos.fit('dep-b1/de-1')` as `computed`. With M05 the same source read `is_measurement=True` and `basis_provenance=measured`, `origin_of` raised a ValidationError, the fit was kept as `measured`, and the counter recorded 6 calls the note clause decided.
- **Likely cause:** `core/tests/test_basis.py:211`: the test's one series source has id `d-1`, which the id clause at `core/openferment_core/basis.py:201` already rejects, so the note clause at `basis.py:202` (`and bool(_MEASURED.match(source.note or ""))`) decides no test's answer; `fermos._inputs` (`core/openferment_core/fermos.py:367-368`) writes the series note on whatever `depositionId` the request names, a plain `str` at `models.py:1730`. (confidence: high)
- **Fix size:** small: one more series case in `core/tests/test_basis.py:203-212` with id `dep-b1/de-1` and fermOS's note, and one `test_fermos.py` fit on that id that asserts the kept fit is `computed`.
- **Severity:** S4, the reading of the refuting agent and of the entry's writer. An independent severity panel read S1: With the note clause dropped, 225 tests pass, and `fermos.fit` for depositionId `dep-b1/de-1` (a plain string that POST /api/fermos/fit takes as sent) keeps the fit as `measured`.
- **Stood on:** the first refutation.

#### H13-02 · S4 · Drift · the literature retrieval report: docs/reports/literature-retrieval.md and literature/report.py

`docs/reports/literature-retrieval.md` names itself the output of `pnpm lit:report` and holds 37 lines its generator never writes, a hand's comment and the sections "What this run measured" and "What waits on the account", and the file's own command, run offline and keyless, deletes all 37, as a project render of the committed JSON's own part does.

- **Contract:** `docs/reports/literature-retrieval.md:1`, "Written by `pnpm lit:report` (core/openferment_core/literature/report.py); regenerate, do not edit." `docs/reports/literature-retrieval.md:91` adds "the next `pnpm lit:report --project ethanol ... --render` writes this project's part whole from its own run, these two sections with it."
- **Reproduce:** `bash bughunt/repro/H13-02/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** Regenerating the file moves the stamps its generator owns (the date, the commit, the ingest time) and keeps every section, and a project render writes the two sections, as line 91 says.
- **Observed:** In both runs the committed file had 126 lines. In both runs `report.write()` of the committed `ethanol` part gave 89 lines, the one diff hunk `90,126d89` (37 lines gone, 0 added) and an unchanged JSON, with 0 lines of `report.py` naming either section. `pnpm lit:report` exited 0 (9 s in run 1, 6 s in run 2) with "2 files changed, 4 insertions(+), 41 deletions(-)", left 89 lines, moved `generated_at`, `git_commit` and `latest_ingested_at` in the JSON, and deleted the comment and both sections. The deleted lines carry the graph dry run's 814 passages, 92 batches, 1,758,899 characters, 0.2199 USD and 2.3239 USD, and the commands for the lanes that wait on the account.
- **Likely cause:** `core/openferment_core/literature/report.py:195-202`: `_save` writes the whole Markdown from the demo text, `PROJECTS_MARK` and `render()` of each part the JSON keeps, and `render()` at `report.py:732-816` writes seven sections (The corpus, The ground truth, Retrieval, The judge's relevance, Answers, Routes, Cost), so the hand's 37 lines have no source on either path into `_save`, `main` (`:149-170`) and `write` (`:205-212`). (confidence: high)
- **Fix size:** small: `render()` writes the two sections from fields the part's JSON keeps, or the hand text moves to a file the generator leaves alone and line 91 goes.
- **Stood on:** the second refutation, by the kind's own standard. The first set it aside because it read line 1's "regenerate, do not edit" as the warning that regeneration drops hand text, and read line 91 with `docs/PROGRESS.md:3385-3387` as the author's note that the next render rewrites the part whole.

#### H13-06 · S4 · Drift · .github/workflows/verify.yml

The header comment of `.github/workflows/verify.yml` names `smoke.mjs` as the browser script that honours `CHROMIUM_PATH`, a file that commit 20bd36d deleted. At 2047f5a the scripts that read `CHROMIUM_PATH` are `scripts/smoke.ts` and `scripts/walk.ts`.

- **Contract:** `.github/workflows/verify.yml:14-16`, "The browser scripts try the pre-installed one first (smoke.mjs also honours CHROMIUM_PATH) and fall back to Playwright's own cache, which is empty on a fresh runner." `package.json:41` names the smoke verify runs: `"smoke": "tsx scripts/smoke.ts"`.
- **Reproduce:** `bash bughunt/repro/H13-06/run.sh`, run twice; it is a static check of commit 2047f5a's objects and needs no database; both runs RESULT: DEFECT, byte for byte the same.
- **Expected:** The comment names the scripts in the tree that read `CHROMIUM_PATH`: `scripts/smoke.ts`, the script `pnpm smoke` runs, and `scripts/walk.ts`.
- **Observed:** Both runs printed `2047f5a:.github/workflows/verify.yml:15:#     one first (smoke.mjs also honours CHROMIUM_PATH) and fall back to Playwright's` and found one file named `smoke.*` in the commit's tree, `scripts/smoke.ts` ("smoke.mjs: 0"). `scripts/smoke.ts:167` and `scripts/walk.ts:170` both read `const executablePath = process.env.CHROMIUM_PATH ?? '/opt/pw-browsers/chromium';`, and 0 lines outside `docs/history/` and `bughunt/` name `smoke.mjs`.
- **Likely cause:** `.github/workflows/verify.yml:15`: commit 22a4eea wrote the comment for alpha 1.0's `scripts/smoke.mjs`, and the comment kept that name when 20bd36d (alpha2 1.1) deleted the file and d4c7ea6 (alpha2 1.6) added `scripts/smoke.ts`. (confidence: high)
- **Fix size:** small: one comment line in `.github/workflows/verify.yml`, naming `scripts/smoke.ts` and `scripts/walk.ts`.
- **Stood on:** the first refutation.

#### H14-05 · S4 · Inconsistency · Home

Home's BioRepo destination line carries the fixed words "gold set not yet annotated", and it keeps them after a record is flagged gold, beside a Gold set tile on the same page that counts 1.

- **Contract:** `src/screens/Home.tsx:235-237`, "What each destination actually has, right now (§7). Counted from the store's lists where there is something to count". The destinations band at `src/screens/Home.tsx:781-782` adds "the whole navigation, laid out once with an honest current state per entry."
- **Reproduce:** `bash bughunt/repro/H14-05/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** With one gold value counted on the Gold set tile, the BioRepo destination line counts the gold values (for example "1 paper · 1 gold value") or leaves the gold set out of its words.
- **Observed:** In both runs one hand-written candidate was promoted through `POST /api/biorepo/decisions` with provenance `gold` and gold `{'value': 41.7, 'unit': 'g/L'}`, and `GET /api/biorepo/overlay` held 1 record with a gold value. Home of the built app in Chromium then read the Gold set tile as "GOLD SET", "1", "across 1 paper · the evaluation baseline" and the BioRepo destination as "BioRepo", "records, artifacts, provenance", "1 paper · gold set not yet annotated".
- **Likely cause:** `src/screens/Home.tsx:284`: `stateOf` writes "gold set not yet annotated" into the BioRepo line for every count, `Counted` (`Home.tsx:244-256`) carries no gold count, and `goldRecords` (`Home.tsx:402`) feeds the Gold set tile alone. (confidence: high)
- **Fix size:** small: a gold count in `Counted`, filled in the `stateOf` call at `src/screens/Home.tsx:366-379`, and the BioRepo line at `Home.tsx:284` worded from it.
- **Stood on:** the first refutation.

#### H14-06 · S4 · Inconsistency · Home, Postdoc

On a keyless service, Home's destinations band says Postdoc is "live through openferment-core, on the model it is configured with". On the same service `GET /api/health` answers `hasKey: false` and Postdoc's own screen says "Postdoc is running without an API key".

- **Contract:** `src/screens/Home.tsx:781-782`, the destinations band, "the whole navigation, laid out once with an honest current state per entry". The other door on the same question, `src/screens/Postdoc.tsx:146`, shown when `health.hasKey` is false: "Postdoc is running without an API key".
- **Reproduce:** `bash bughunt/repro/H14-06/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** With `hasKey: false`, Home's Postdoc line gives the state Postdoc's own screen gives, that Postdoc waits for a key. Once the service holds a key, the line names the configured model.
- **Observed:** Both runs served on 127.0.0.1:10081 over a fresh `bh_r_h14_06_home`, and `GET /api/health` answered `{"ok":true,"service":"openferment-core","model":"claude-opus-5-5","fallbackModel":"claude-sonnet-5-5","hasKey":false}`. Home's Postdoc card read "Postdoc | ask, plan, answer from records | live through openferment-core, on the model it is configured with". Postdoc's screen showed the callout "Postdoc is running without an API key" and left out its "The Postdoc service answers on" line.
- **Likely cause:** `src/screens/Home.tsx:285`: `stateOf` writes the Postdoc line as the fixed string 'live through openferment-core, on the model it is configured with' for every state of the service, and no line of `Home.tsx` names `health` or `hasKey`, so the line has no health answer to follow. (confidence: high)
- **Fix size:** small: Home reads the health answer Postdoc already reads and words the Postdoc line from `hasKey`.
- **Stood on:** the second refutation, by the kind's own standard. The first set it aside because it read the comments at `src/screens/Home.tsx:235-238` and `:781-782` as a method for counting the store's lists, found each clause of the Postdoc line true by the health answer, and found no document that sets Home's wording for a keyless service.

#### H14-08 · S4 · Drift · Home, pureOS

Home's pureOS destination line says "45 unit operations · no process model" in fixed text, and those words misstate pureOS. pureOS builds trains from BioSTEAM's units and runs them through the registered `train` engine, as its own page says.

- **Contract:** `src/screens/Home.tsx:235`, "What each destination actually has, right now (§7)." `src/screens/PureOS.tsx:409` states what pureOS has: "pureOS builds a train unit by unit from a catalogue of BioSTEAM's units and runs it".
- **Reproduce:** `bash bughunt/repro/H14-08/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** Home's pureOS line says what pureOS holds now: trains built in the Builder and run on BioSTEAM through the `train` engine, as the pureOS page's subtitle and footer say.
- **Observed:** In both runs `GET /api/engines` named "biosteam, kinetics, train", with `train` from `openferment_core.pureos.engine:ENGINE` on biosteam 2.54.0. Home of the built app read "pureOS | harvest, capture, recovery | 45 unit operations · no process model". The pureOS page read "pureOS builds a train unit by unit from a catalogue of BioSTEAM's units and runs it" and "Produced by pureOS · 45 operations; trains built here and read from runs".
- **Likely cause:** `src/screens/Home.tsx:291` hardcodes ``pureOS: { now: `${UNIT_OPERATIONS.length} unit operations · no process model`, built: true }``; the words came in at 0100041 in alpha 1.0 and stayed as written through pureOS's Builder, already at tag alpha-1.0, and through alpha 2.2 C.3's `train` engine (a4a739f). (confidence: high)
- **Fix size:** small: the one pureOS line in `stateOf` at `src/screens/Home.tsx:291`, worded for the trains pureOS builds and runs.
- **Stood on:** the first refutation.

#### H5-06 · S4 · Contract break · requests naming no project: the catalogue and protocol readers

With no `X-OpenFerment-Project` header, `GET /api/protparam` and `POST /api/pureos/propose` answer 404 saying the products catalogue holds no `product-a`, and `POST /api/guild/check` answers 200 with "'SK-A' is not a skill Guild holds", because the catalogue and protocol readers read a request with no project as an empty catalogue. The verdict confirmed these three rows and Guild evidence's 422 about the skill. It set aside the two tool-door rows, which follow that door's own documented refusal shape.

- **Contract:** `docs/decisions/ADR-005-projects.md:28-29`, "a store call in a request that names none is a 422 that says which header to send"; and the service description in the OpenAPI document, `core/openferment_core/api.py:203-204`, "a request naming none is a 422 in words at its first store call".
- **Reproduce:** `bash bughunt/repro/H5-06/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** Each request naming no project answers 422 at its first store read, with the words "This names no project. A request sends the X-OpenFerment-Project header (or ?project= on an event stream); a command sets OPENFERMENT_PROJECT.", as `GET /api/audit` and `GET /api/catalogues/product` answer.
- **Observed:** In both runs, with no project named, `GET /api/audit` and `GET /api/catalogues/product` answered 422 with those words. With no project named, `GET /api/protparam?product=product-a` answered 404 "there is no product 'product-a' in the products catalogue, so it carries no sequence to compute from", and `POST /api/pureos/propose` answered 404 "there is no product 'product-a' in the products catalogue or among the chemicals thermosteam's library is asked about here (ethanol)". Naming `bh-a`, which holds the product, the same two calls answered 200. `POST /api/guild/check` answered 200 "'SK-A' is not a skill Guild holds (none ship with alpha 2.0)". `POST /api/guild/evidence` answered 422 "skill: 'SK-A' is not a skill Guild holds (none ship with alpha 2.0)". `bh-a` held the skill `SK-A` during both Guild calls.
- **Likely cause:** `core/openferment_core/catalogues.py:585-590`: `_entries` catches the `projects.ProjectRequired` its store read raises and returns `[]`, so `as_products`, `as_hosts` and `as_skills` hand protparam (`protparam.py:253`), the proposer (`pureos/proposer.py:206`) and Guild (`guild.py:151`) an empty catalogue, and `protocols.held` (`core/openferment_core/protocols.py:291-296`) does the same for Guild's protocols (`guild.py:153`); the exception never reaches the 422 handler at `api.py:414-416`. (confidence: high)
- **Fix size:** small: `_entries` and `held` let `ProjectRequired` reach the handler, and their docstrings ("or none where no project is open") and `core/tests/test_protocols.py:224`, which asserts `held() == []` with no project open, change with them.
- **Severity:** S4, the reading of the refuting agent and of the entry's writer. An independent severity panel read S3: A request sent without the X-OpenFerment-Project header gets a 404 saying a held product is absent from the products catalogue, or a 200 saying a held skill is unknown.
- **Stood on:** the first refutation.

#### H5-07 · S4 · Drift · Guild evidence and check, Practice drafts: refusal words

Guild's evidence and check routes and Practice's draft route refuse a skill the project's skill catalogue lacks as "'X' is not a skill Guild holds (none ship with alpha 2.0)", a reason written when Guild held no skills. The `CheckCriterion` docstring carries the same alpha 2.0 words into `docs/api/openapi.json` and `src/api/types.gen.ts`. On this tree Guild's skills are the project's skill catalogue, kept at `/catalogues`.

- **Contract:** `CLAUDE.md:15`, "A project's catalogues (strains with their aliases, products, Guild's skills, Primer's lessons) have a screen at `/catalogues`, Primer's lessons come from the lesson catalogue, and Guild's protocol steps name skills from the skill catalogue".
- **Reproduce:** `bash bughunt/repro/H5-07/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** A skill the catalogue lacks is refused in words that give the present reason: the project's skill catalogue holds no such skill, and a skill is kept at `/catalogues`, as the protocol keep's refusal already words it (`core/openferment_core/protocols.py:97-100`).
- **Observed:** In both runs, over a fresh `bh_r_h5_07_skillwords` with project `bh-a` keeping `SK-A`, `POST /api/guild/evidence` and `POST /api/practice/draft` naming `SK-NONE` answered 422 `{"detail": "skill: 'SK-NONE' is not a skill Guild holds (none ship with alpha 2.0)"}`. `POST /api/guild/check` answered 200 with `"ok": false, "rule": "skill"` and the same words. The control `SK-A` passed the skill rule (the check stopped later, at `source`), and the protocol keep refused `SK-NONE` with 422 in words naming "the project's skill catalogue" and "(/catalogues)". The phrase "none ship with alpha 2.0" stood on 5 lines: `guild.py:395`, `practice.py:487`, `models.py:1426`, `src/api/types.gen.ts:3528` and `docs/api/openapi.json:2053`.
- **Likely cause:** `core/openferment_core/guild.py:395` (`_precheck`) and `core/openferment_core/practice.py:487` (`_skill`) keep the refusal words of alpha 2 stage 8.5, when `guild.projection()` held no skills. Alpha 2.1 and 2.2 moved `projection()` to `catalogues.as_skills()` (`core/openferment_core/guild.py:142-160`). Those releases left these two strings and the docstring at `core/openferment_core/models.py:1425-1426` as they stood. (confidence: high)
- **Fix size:** small: two refusal strings and one docstring, then `pnpm gen:api` regenerates `docs/api/openapi.json` and `src/api/types.gen.ts`.
- **Stood on:** the second refutation, by the kind's own standard. The first set it aside because it read `CLAUDE.md:15` and `CLAUDE.md:87` as met by the refusal's behaviour, found "none ship with alpha 2.0" still literally true, and found no ADR, API document or test that sets these refusal words.

#### H6-05 · S4 · Drift · the records of the table shape: ADR-001 and CLAUDE.md

ADR-001's implementation note and CLAUDE.md's architecture line say each row keeps the Pydantic model as a JSONB `body`. The migrations make all 34 content columns of schema `openferment`, the 29 `body` columns among them, PostgreSQL `json`, the type `core/openferment_core/db/models.py:7-9` says the tree chose so that key order and a negative zero survive.

- **Contract:** `docs/decisions/ADR-001-postgresql.md:62`, "the rest of the row is `body`, the Pydantic model of `models.py` dumped as JSONB"; and `CLAUDE.md:66`, "a row keeps its lookup keys as columns and the Pydantic model as JSONB `body` (ADR-001)".
- **Reproduce:** `bash bughunt/repro/H6-05/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** The content columns of a database migrated to head have the type the two lines name, JSONB; the other passing outcome is that the two lines say `json`, as `core/openferment_core/db/models.py:7-9` and `docs/PROGRESS.md:796-797` do.
- **Observed:** In both runs, whose logs are byte for byte the same, a database migrated from empty to head `0010` held "json: 34 columns (body,input,record,result,selection,settings)" and "body columns: 29, of type json: 29; columns of type jsonb anywhere in schema openferment: 0". ADR-001:62 and CLAUDE.md:66 both read JSONB. A cast kept `'{"b":1,"a":-0}'::json` as `{"b":1,"a":-0}`, with the key order and negative zero models.py names as its reason. For `::jsonb` the cast gave `{"a": 0, "b": 1}`.
- **Likely cause:** `core/openferment_core/db/models.py:36`, `from sqlalchemy.dialects.postgresql import JSON, TIMESTAMP`: commit `fa16892` (stage 2.3) moved this import and the content columns from JSONB to JSON, with `core/openferment_core/db/alembic/versions/0001_initial.py` (line 42, for example) and migrations 0006, 0007, 0009 and 0010 making `postgresql.JSON` columns, and it left ADR-001:62 and CLAUDE.md:66, written at stage 2.1 (`96fd138`), with that stage's word. (confidence: high)
- **Fix size:** small: JSONB becomes `json` in ADR-001:62, in CLAUDE.md:66 (a line `core/tests/test_guidance.py` holds) and in the departures row at `docs/PROGRESS.md:541`. Stage 2.1's log line at `docs/PROGRESS.md:763` records that stage's JSONB columns accurately and stays as it is.
- **Stood on:** the first refutation.

#### H7-09 · S4 · Inconsistency · Settings, durable.ts, the bench run

Settings > About's Storage row says a deposition at hour 14 with timers running cannot be lost to a page reload. One reload ends a deposition's run at the bench and drops its running timer and its deviation note, as the bench itself says it will. The deposition record stays on the service.

- **Contract:** `src/screens/Settings.tsx:1254-1256`, "This browser keeps its preferences and the writes the service has not yet acknowledged, in IndexedDB, because a deposition at hour 14 with timers running cannot be lost to a page reload". The other door on the same question, `src/screens/Deposition.tsx:298`, "A run at the bench lives in this page's memory, so a reload ends it".
- **Reproduce:** `bash bughunt/repro/H7-09/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** One account of a reload across the tree: either a deposition's run comes back after one reload with its running timer and its deviation note, or the Storage row says what `src/screens/Deposition.tsx:298` and `src/screens/ProtocolDetail.tsx:1264` say, that a run at the bench lives for the session.
- **Observed:** In both runs the built app's Storage row read "... because a deposition at hour 14 with timers running cannot be lost to a page reload; ...". Before the reload the bench at `#/p/h7-09/runbooks/protocols/h7-09-protocol/run/run-2` showed the deviation note and the timer "placeholder wait" with 1 Pause button. At that moment the IndexedDB snapshot held the keys `guild`, `outbox`, `reviewDecisions`, `reviewerName`, `savedAt` and `version`, with no run, note or timer among them. After one reload with the `beforeunload` prompt accepted, the same address read "This run is no longer active" and "A run at the bench lives in this page's memory, so a reload ends it", the note and the timer had left the screen with 0 Pause buttons, and the service kept 1 deposition holding neither the note nor the timer label.
- **Likely cause:** `src/store.ts:3504`: `snapshotOf` writes no `runs` and no `activeRunId` into the Durable snapshot, and the save subscription at `src/store.ts:3655-3670` watches no `s.runs`, so the run that `startRun`, `addDeviation` and `addTimer` write (`src/store.ts:1506`, `:1575`, `:1582`) stays in page memory. The Storage row and the header at `src/lib/durable.ts:6-8` carry OF-BLD-006 §4.6's reason for the Durable tier. No saved run backs it. (confidence: high)
- **Fix size:** small: the Storage row in `Settings.tsx` and the header of `durable.ts`, worded as the bench words a run. Saving runs through `snapshotOf` is the larger change.
- **Stood on:** the second refutation, by the kind's own standard. The first set it aside because it read "deposition" in the Storage row as the record that `src/store.ts:366-370` keeps through the outbox, which survived the reload on the service, and read the run's timers and notes as outside what the row lists as kept.

#### H8-11 · S4 · Drift · POST /api/intake/catalogue (catalogues.intake): an entry's source

`POST /api/intake/catalogue` keeps a file's row that carries its own `source` with the row's words as the entry's source, so that entry names the file it came in by nowhere. The file appears in the `keep_catalogue` audit row's detail alone.

- **Contract:** `docs/api/intake.md:104`, "Every row that is an entry is kept with the file as its source and audited as `keep_catalogue`, its detail naming the file"; and the catalogues screen, `src/screens/Catalogues.tsx:426-427`, "Every row that is an entry is kept in your name with the file as its source".
- **Reproduce:** `bash bughunt/repro/H8-11/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** Both entries taken in from `rows.json`, S6 (a row with `"source": "a row's own words"`) and S7 (a row with no source), carry a source that names the file `rows.json`; S6 may keep its own words beside the file.
- **Observed:** In both runs the post answered HTTP 200 with `{"kind": "strain", "kept": ["S6", "S7"], "refused": []}`. `GET /api/catalogues/strain/S6` gave source "a row's own words". `GET /api/catalogues/strain/S7` gave source "the file rows.json". Both `keep_catalogue` audit rows held the detail `[{'kind': 'strain', 'file': 'rows.json'}]`.
- **Likely cause:** `core/openferment_core/catalogues.py:571`, `"source": r.get("source") or f"the file {filename}"`, keeps a row's own source and names the file when the row leaves `source` out. The same call writes `by`, `agent`, `via` and `at` over the row's values. The one test of a file's source, `core/tests/test_catalogues.py:87`, posts rows with no `source`, so it never reaches this branch. The CSV path reaches the same line. (confidence: high)
- **Fix size:** small: line 571 names the file beside a row's own words, or the three texts (`docs/api/intake.md:104`, the docstring at `catalogues.py:554-556` and `Catalogues.tsx:426-427`) say a row's own source stands; either way a test posts a row that carries a source.
- **Stood on:** the first refutation.

#### H9-13 · S4 · Contract break · the REST tool door: POST /api/tools/{name} answer encoding

A JSON body holding the escape `\ud800` in a string a tool echoes (search_records' `query`, `field` or `organism`, search_passages' `query`, yield_ceiling's `product`, selling_price's or run_flowsheet's `scenarioId`) makes `POST /api/tools/{name}` answer 500 with the bare body "Internal Server Error", because the ToolResult the door returns carries the lone surrogate and FastAPI's response serialization cannot encode it as UTF-8.

- **Contract:** `core/openferment_core/api.py:2924-2925`, the tool door's docstring: "A refusal is a result with `error` set; an unknown tool is a 404."; and the service description, `core/openferment_core/api.py:208`: "A refusal is a status with its reason in `detail`, in words."
- **Reproduce:** `bash bughunt/repro/H9-13/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** Each call with `"a\ud800b"` answers as its `"ab"` twin does: a 200 ToolResult whose `error` says in words why nothing matched or ran, or the result with the surrogate dropped, as `tools.caller_name` (`core/openferment_core/tools/__init__.py:176-181`) already drops one from a caller's name.
- **Observed:** In both runs, 7 of 7 calls with "ab" answered 200 with a ToolResult (yield_ceiling's, for example, with error "yield_ceiling refused: there is no product ab; the shelf knows ethanol"). In both runs, 7 of 7 calls with "a\ud800b" answered 500 with the body "Internal Server Error", no `detail` and no `error`. The service log read "PydanticSerializationError: Error serializing to JSON: UnicodeEncodeError: 'utf-8' codec can't encode character '\ud800' in position 1: surrogates not allowed" and named UnicodeEncodeError 15 times in each run.
- **Likely cause:** `core/openferment_core/api.py:2960`, `return tools.run(name, body, ctx)`, hands FastAPI a ToolResult whose summary or error echoes the lone surrogate Starlette's `json.loads` let into the body, and the response serialization raises after `tools.run` has returned. The door drops surrogates from the caller's name alone (`tools.caller_name`). `tools.run` keeps its own docstring's word at `core/openferment_core/tools/__init__.py:502-503`, "nothing here raises". (confidence: high)
- **Fix size:** small: the tool door drops or refuses lone surrogates in the body before `tools.run`, or in the result before it is encoded, with a test of one surrogate call.
- **Severity:** S4, the reading of the refuting agent and of the entry's writer. An independent severity panel read S3: A JSON body holding a lone surrogate escape, in a string any of seven tools echoes, makes the REST tool door answer a bare 500 with no words.
- **Stood on:** the first refutation.

#### H9-15 · S4 · Drift · openferment MCP server: ask_postdoc and get_artifact

Over the openferment MCP server, `ask_postdoc` with its `question` missing, 7 or null, and `get_artifact` with its `id` missing, 7 or null, answer `isError: true` with the SDK's non-JSON text "Error executing tool <name>: 1 validation error for <name>Arguments ..." and an errors.pydantic.dev link. `docs/TOOLS.md`, generated from `core/openferment_core/tools/reference.py:254-261`, says each tool answers one JSON text block and a refusal keeps `is_error` false. The registry tools on the same server answer the same inputs the way `docs/TOOLS.md` says.

- **Contract:** `docs/TOOLS.md:896`, "Over MCP each tool answers one text block holding its result as JSON" and "A tool's refusal is its ToolResult with `error` set, and `ask_postdoc`'s an `AnswerPlan` whose `declined` holds the words. A refusal the server writes itself (... an artifact id of no artifact's shape) is `{"error": <words>}` alone for a tool and for `get_artifact` ... `is_error` stays false, and no `structured_content` is sent."
- **Reproduce:** `bash bughunt/repro/H9-15/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** Each of the six calls answers one JSON text block with `isError` false: an `AnswerPlan` whose `declined` holds words for `ask_postdoc`, and `{"error": <words>}` for `get_artifact`, in the shape `literature_document` gives `{}`, `{"document": 7}` and `{"document": null}` and `get_artifact` gives `"zz"`.
- **Observed:** In both runs the controls kept the page's shape: `literature_document` refused in words with `isError` false in 3 of 3 cases, and `get_artifact` with `"zz"` answered `{"error": "no readable artifact 'zz': an artifact's id is sixteen hex digits, ..."}` with `isError` false. All 6 probes answered `isError: true` with no JSON, for example "Error executing tool ask_postdoc: 1 validation error for ask_postdocArguments \n question \n Field required [type=missing, input_value={}, input_type=dict] \n For further information visit https://errors.pydantic.dev/2.13/v/missing" and "Error executing tool get_artifact: 1 validation error for get_artifactArguments \n id \n Input should be a valid string [type=string_type, input_value=7, input_type=int] ...". An `AnswerPlan` with `declined` came back in 0 of 3 `ask_postdoc` probes, and `{"error": <words>}` in 0 of 3 `get_artifact` probes.
- **Likely cause:** `core/openferment_core/mcp_server.py:405` and `:422` register `ask_postdoc` and `get_artifact` through `@server.tool` with typed signatures (`question: Annotated[str, ...]`, `id: Annotated[str, ...]`), so mcp 2.3.0 validates the arguments before the body runs and raises `ToolError(f"Error executing tool {self.name}: {exc}")` (`core/.venv/lib/python3.13/site-packages/mcp/server/mcpserver/tools/base.py:156`), which the SDK's `server.py:456` answers with `is_error=True`. The registry tools take `_Raw` (`mcp_server.py:104-110`, set at `:367`) and reach the registry's own validation. The refusal paths at `mcp_server.py:410` and `:426` go unreached for these inputs. (confidence: high)
- **Fix size:** small: the two tool signatures in `mcp_server.py` take their argument as sent (a `_Raw`-style model or `Any`) and answer a missing or non-string one in words through `refusal()` or `artifact_refusal()`.
- **Stood on:** the second refutation, by the kind's own standard. The first set it aside because it read the server-written refusals listed in `docs/TOOLS.md:896` as a closed list for string ids, read the published input schemas (`question` and `id`, string, required) as covering a call outside them, and found `POST /api/ask` over HTTP answering the same inputs with a 422 field list.

#### R1-01 · S4 · Drift · docs/PROGRESS.md, Departures row alpha 2.2 D8 (C.6)

The alpha 2.2 D8 departure row at `docs/PROGRESS.md:483` names `GET /api/artifacts` as the route the reference screen reads the project's kept reference runs from. The service answers 404 at that path. The screen reads `GET /api/biorepo/artifacts?tool=`.

- **Contract:** `docs/PROGRESS.md:483`, "the reference screen reads the library plant's runs (`GET /api/runs?engine=biosteam`) and the project's kept reference runs (`GET /api/artifacts`)"; the schema the row answers to is the generated one, `CLAUDE.md:87`, "REST: FastAPI routes in `core/openferment_core/api.py`; `docs/api/openapi.json` is generated".
- **Reproduce:** `bash bughunt/repro/R1-01/run.sh`, run twice from a clean database, both runs RESULT: DEFECT.
- **Expected:** The row names the route the screen reads kept reference runs from, `GET /api/biorepo/artifacts?tool=`, which `keptReferenceRuns` (`src/lib/proforma.ts:169-171`) asks when `src/screens/ProformaReference.tsx:283` calls it, and which the screen's header comment names at `src/screens/ProformaReference.tsx:20`.
- **Observed:** Both runs printed the row at `docs/PROGRESS.md:483` naming `GET /api/runs?engine=biosteam` and `GET /api/artifacts`, and found the same five artifacts paths in `docs/api/openapi.json` and in the app's 129 routes: `/api/biorepo/artifacts` and its sub-paths `/{artifact_id}`, `/checks`, `/replay` and `/tables`. For `/api/artifacts` they printed "in openapi.json: False; in the app's routes: False", 0 `api.py` decorators and 0 client files. On a fresh database, `GET /api/artifacts` answered 404. On the same database, the screen's `GET /api/biorepo/artifacts?tool=proforma.reference&tool=proforma_benchmark` answered 200.
- **Likely cause:** `docs/PROGRESS.md:483`: commit `f5405f8` (C.6) wrote the row with the route's path shortened to `/api/artifacts`, at a commit whose `docs/api/openapi.json` held `/api/biorepo/artifacts` with its `/{artifact_id}` and `/replay` sub-paths, and no check holds the route names in `docs/PROGRESS.md` to the schema. (confidence: high)
- **Fix size:** small: one path in the row, `GET /api/biorepo/artifacts?tool=`.
- **Stood on:** the first refutation.

#### R1-05 · S4 · Wrong number · docs/reports/handoff-2026-11.md, Round 1, the agent builder

The handoff report gives the `docs/TOOLS.md` the agent builder read at `CORE=6f85338` as 838 lines. The file at that commit holds 837 lines (84,382 bytes, its last byte a newline), and it held 837 at `37e6bd0`, the commit that wrote the count.

- **Contract:** `docs/reports/handoff-2026-11.md:82`, "**What it read.** `.mcp.json`, `docs/TOOLS.md` whole (838 lines) and `docs/api/openapi.json`"; the read is tied to one commit by `docs/reports/handoff-2026-11.md:11`, "`CORE=6f85338` (the D.0 commit, green on CI run 41865693107)", and by lines 85-86, "all in the worktree at `CORE`".
- **Reproduce:** `bash bughunt/repro/R1-05/run.sh`, run twice; it reads git objects alone and needs no database; both runs RESULT: DEFECT, the two logs byte for byte the same.
- **Expected:** The report's count equals the lines of `docs/TOOLS.md` at `CORE=6f85338`, the file the builder read in the worktree at `CORE`.
- **Observed:** Both runs read the report's count as 838. They found `docs/TOOLS.md` at `6f85338` with `wc -l` 837, `awk` NR 837 and Python `splitlines()` 837, 84382 bytes, the last byte `\n`, and the same 837 at `37e6bd0`, the commit that wrote line 82. Python `split('\n')` over the file at `6f85338` gives 838 pieces, and the first `TOOLS.md` of 838 lines is at `50a4f96` (E.8), a commit after `37e6bd0`.
- **Likely cause:** `docs/reports/handoff-2026-11.md:82`, written at `37e6bd0` (D.2 to D.4), carries 838, which matches two counts of a file that ends in a newline: the pieces `split('\n')` gives, and the rows a viewer shows when it numbers the empty position after the last newline; each is one more than the file's 837 lines. (confidence: medium)
- **Fix size:** small: the one number on line 82, 837.
- **Stood on:** the first refutation.

## Paid debts tested again

Task P tested every row of the Paid table again on the head, keyless, on services and databases of its own, with
Chromium for the screens (`bughunt/notes/P/`). Where another hunt tried the same claim from another door, its
result is named on the row. In table order:

1. The agent builder's interface points (one record rule, audit ids on writes, the audit's filters, null fields left out, the typed partial, the recipe): holds. `test_agent_interface.py` passed, and a catalogue keep through the tool door as a person and as an assistant answered its audit id, which `GET /api/audit` found by action, target and who.
2. The per-request key override and the local-model route: fails in part, with H9-01 and P-01. On `/api/ask` and `/api/ask/stream` the named key reached a stub as `x-api-key`, and it appeared in no log line, response, event or row. `POST /api/literature/answer` makes its call on `core/.env`'s key (H9-01). A route of local models alone stops for want of an Anthropic key (P-01).
3. A retrieval report over a project's own corpus, as far as it asks no model: holds. `lit:graph --dry-run` and `lit:report` over a project filled from the kit's demo corpus made 0 calls. H13 found that the report's command rewrites the committed report's hand-written sections (H13-02), a defect beside the row's claim.
4. The kit's graph tools read the project's graph alone: holds. Over stdio, each project saw its own entities and quotes. Neither project saw any of the other's. H5 found the same on the graph reads over rows written by hand.
5. The catalogues are project stores, with their screen and the store's reads: holds as the row is written. A skill kept in one project is absent from another, and a protocol naming another project's skill is refused. H14 found that a strain's aliases reach no anchoring (H14-02), which `docs/api/intake.md` promises.
6. competence.ts reads a skill kept with no policy as unrated: holds. `export-competence-fixtures.ts` gave both fixtures byte for byte, and the skill's page said Guild rates nobody on it.
7. The protocols page begins a protocol and its editor adds skills as version 1.1: holds, in Chromium.
8. `stream_table` on a scenario's kept run has its test again: holds. In the run's project the tool answered 45 rows. In another project it refused.
9. The module reads list depositions and readings, and `PARTIAL` holds no runbooks line: holds.
10. Proforma reads every scenario as the project's, and a broken composite is listed with its refusal in words: holds, with HTTP 200 and the words.
11. The geneOS enumeration module and the research funnel are deleted: holds.
12. `src/data/types.ts` is deleted and the screens read the generated types: holds; nothing imports it, `gen:api --check` and `tsc --noEmit` pass. H7 held 49 answers of a full project to the OpenAPI document and found no required field absent; of the 200 `as` casts and 60 non-null marks left under `src/`, the `!` sites on a Map or a find are each guarded, and the casts of artifact output rendered every kept artifact of a full project with no error (`bughunt/notes/H7/notes.md`).
13. Readers of `Override.origin`, `Runbook.note` and `Runbook.progressPct` read a field left out: holds, in `check:state` and in Chromium.
14. `store.adoptRunbookDraft` takes the generated draft with no assertion: holds.
15. A promoted or superseded runbook takes an id that holds across reloads: holds in `check:state`.
16. The project state's three routes answer models: holds. H5 found that a write under one kind can replace a row of another kind (H5-03). That defect lies in what the routes accept. It stands beside the row's claim, which is about what they answer. H2 and H5 also found that the state door takes back a locked runbook and leaves its lock behind (H5-04, under Suspected: both refutations read the lock row as the record that stays).
17. `openferment.records` is written by each decision and an undo: holds; versions 1, 2 and 3 of the row.
18. fermOS's, pureOS's and Proforma's requests take typed quantities and their runs are rows of the three engines: holds.
19. The train engine's `rests_on` names the project's depositions, and the completeness test fails without them: holds. A plugin that dropped them made the test fail.
20. pureOS reads a library run as a train: holds. In its project the read gave 68 units. In another project it answered a 404 in words.
21. Studies' run card titles a kinetics configuration: holds.
22. The screens' words put a project's rows with the service: holds in `check:state` and on Postdoc's empty list.
23. The shelf's hand-written reference entries retired, and kept runs replay through `kept_references.py`: holds offline. The sim replay was left to `test:sim`, which the baseline ran green.
24. Small handler mismatches the worker op reference found: holds.
25. Proforma's panel takes a reading in its own value and unit: holds. The same reading in another unit or another project is refused in words.
26. A review decision's provenance is computed by `biorepo.provenance_of`: fails, with P-02. A verified decision with no gold value is kept gold when its label says gold.
27. The evidence pool applies the standing decisions: holds.
28. The dead service paths the deletions left: holds.
29. `nav.ts` exports `DESTINATIONS`: holds.
30. `selling_price`, `run_flowsheet`, the params scope and pureOS's naming read the project's scenarios: holds.
31. The client's review path lost alpha 1.0's curated-record machinery and its identifier rule: holds in the code. The words drift, with P-03.
32. The walk goes through a project on the real service: holds by reading `scripts/walk.ts`; the baseline's `pnpm prove` ran it green (step 9).
33. Both MCP servers connect at a session's start and answer over stdio: holds when measured (2.2 to 2.4 s by `.mcp.json`'s own command). This session's own start reported both as timed out after 30 s, and that went on the Suspected list.

Task P read the Open and Left by decision tables against the tree and found no row that behaves worse than it says.
Two hunts that read the code cold reached two Left rows and claimed more than the rows' words: H4-01 on the library
run's cost card and H7-03 on two devices writing one deposition. Each reproduction was built for the part beyond the
row. Both refutations set that part aside, so both stand under Suspected and no known debt is reported worse than
its row. One Open row carries a figure the records hunt found wrong: the concept graph's cost "at most 2.3239 USD" is
five times the build's per-request cost (R1-03).

## Suspected

This section holds the 49 candidates that fell at stage 3 and the suspicions the hunts recorded without proof. Each
refuted candidate reproduced. Two fresh refuters set it aside: the first read it against the written contract,
and the second against the brief's own definition of its kind of defect. Each not-reproduced candidate was run twice
by its reproducer and once more by the second refuter, and gave the documented behaviour. A grade in brackets at the end of an outcome is the refuters' own reading of the severity had the item
stood. Where a bullet says the behaviour reproduces and the written contract makes no promise about it, the owner can
decide whether the contract should change.

### Reproduced, refuted twice

- **H1-02** (S3 as claimed) An engine set aside for its name or for a failed import leaves cobra in the service process. Tried: loaded by itself, the stand-in entry module that imports cobra (h1z) is set aside with cobra named, and cobra leaves `sys.modules`. Loaded after an engine set aside for its name (h1a) or for an import that raises after importing cobra (h1b), cobra and 67 modules below it stay in `sys.modules`, and h1z loads with error None. Outcome: `docs/api/engines.md:144-146` says discovery "counts the modules an entry module's import adds to those the service had already imported; conformance check 6, in a process of its own, holds every one out", and check 6 names cobra for h1z in the same layout. No line promises that cobra's keys leave `sys.modules`, and in the control the stand-in module keeps a live reference to cobra. The remnant the refuters kept is h1a's words, which name its first fault and leave cobra unnamed (S4).
- **H1-07** (S4 as claimed) A worker that lists two things under one id has both listed, and every run of that id takes the last one's precision. Tried: `GET /api/engines` lists both `dup` things, at precision (0, 0) and (1, 1), with no error; a run of `dup` answers 200 and keeps `precision.rtol` 1.0 and `precision.atol` 1.0 in its basis. Outcome: the breaking answers listed at `docs/api/workers.md:62-68` include two outputs of one name. They name no rule for two things of one id, and the `things` result and the `EngineThing` schema carry no uniqueness rule. The run card shows no precision, so the screen and the service gave the same answer in the run. The behaviour reproduces and the written contract makes no promise about it; the refuters read it as a missing check on a malformed third-party worker (S4).
- **H1-09** (S4 as claimed) An output carrying an extra key with a number is accepted and kept in the run's artifact. Tried: the output `{"name": "x", "value": 1.0, "unit": "u", "stray": 42}` is kept done, and the artifact and its hash hold the extra key. The typed `outputs.values` hold name, value, unit and origin. A replay where the stand-in answers 43 differs at `values[0].stray`. An output with no unit is refused 503. Outcome: `docs/api/engines.md:484-487` and `docs/api/workers.md:62-68` name "an output that is no name, value and unit" as a break, and an output with a fourth key is a name, value and unit. ADR-015's E.18 note keeps worker answers open (Pydantic drops an undeclared field), `engines.md:549` holds for the typed outputs, and the replay difference comes from a stand-in that breaks the determinism rule at `engines.md:466-468`. The behaviour reproduces and the written contract makes no promise about extra keys (S4).
- **H11-04** (S3 as claimed) The night's dump reads a database named `openferment`. The service and the night's other steps read the database `OPENFERMENT_DATABASE_URL` names. Tried: with `core/.env` naming `bh_r_h11_04_live`, the four python steps get that address. With the same `core/.env`, `pg_dump` dumps `openferment`. With a leftover `openferment` on the server the night exits 0 and keeps a dump of the leftover. With none it exits 1 every night. Outcome: `scripts/host/lib.sh:168-169`, `docs/runbooks/live-host-install.md:260`, `docs/PROGRESS.md:557` and `:3591`, and `core/tests/test_host.py:319-327` all name `pg_dump openferment`, and every install writes `.../openferment` into `core/.env`. The mismatch needs a hand edit of `core/.env` that no runbook step asks for; the second refuter graded it a Broken use at S3 had it stood, with the workaround of keeping the live database named `openferment`.
- **H11-10** (S4 as claimed) A night's dump stopped half way leaves its `.part` file in the backups folder, and no later night removes it. Tried: a SIGTERM to the night's process group as the real `pg_dump` waited ended the night with exit 143 and left `openferment-2026-11-10.dump.part` at 0 bytes. Three ordinary nights each made a whole dump and rotated out the oldest, and the `.part` stayed through all three. Outcome: `scripts/host/lib.sh:172-173` promises that "a failed night keeps the seven as they were" and the runbook (`live-host-install.md:260`) says "the newest seven are kept"; both hold, and `core/tests/test_host.py:344` covers `pg_dump`'s own failure return, which removes the `.part`. The behaviour reproduces and the written contract makes no promise about a job whose shell is signalled; a trap, or a sweep of stale `.part` files at the start of a night, would close it (S4).
- **H11-11** (S4 as claimed) A clock set back makes the rotation remove the dump it just made, and the night exits 0. Tried: with nights kept up to 2027-01-13 and the date reading 2026-01-14, `backup_database` wrote a real dump, removed that same file as the oldest by name, logged "openferment-2026-01-14.dump removed: the newest 7 are kept" and returned 0; the next night did the same. Outcome: `scripts/host/lib.sh:168-170` keeps "one file a day named by its date, the newest seven kept", and `lib.sh:195` states the premise that the names sort as the days do, so a file named 2026-01-14 is the oldest by that rule. A clock one to seven days back lands on a kept name and keeps tonight's data. The loss needs eight days or more, and the log names the removal. The behaviour reproduces and the written contract makes no promise about a wrong clock; the second refuter graded it S3 had it stood.
- **H12-07** (S3 as claimed) CI holds no check on `core/uv.lock`, so a stale lock is rewritten in CI and passes. Tried: after a hand edit to `pyproject.toml` that excludes the locked alembic 1.20.1, `uv lock --check` and `uv sync --locked` exit 1. After the same edit, the `uv run --all-extras` form of test:core rewrites the lock to 1.19.1 and passes 24 of 24; `verify.yml` names the lock on 0 lines. Outcome: the committed lock matches `pyproject.toml` (`uv lock --check --offline` exits 0 at `2047f5a`) and CLAUDE.md:40's pins hold. CLAUDE.md:24 and ADR-011 say CI runs `pnpm verify` with a pgvector service and then `pnpm prove`, which `verify.yml` does, and `deploy.sh:80-82`'s `UV_FROZEN=1` describes deploy's own gate. The behaviour reproduces on a planted commit and the written contract makes no promise about it; a `uv lock --check` step before verify would add the guard (S4).
- **H12-10** (S4 as claimed) `keep_run`'s rewrite of a held row that has neither a file nor words is untested. Tried: mutations M21 and M24 of that branch pass the five test files (208 passed, 1 deselected). The hunt's probe passes on the head. It fails under each mutation. Outcome: the head does what `core/openferment_core/engine/runs.py:435-446` and `docs/api/runs.md:167` say, and no writer in the tree can make such a row: `keep_run` refuses it at `runs.py:455-457`, no route writes runs rows, no migration rewrites run bodies, and `RunStatus` holds two states. The refuters read it as an untested defensive branch for a state the tree cannot produce (S4).
- **H12-14** (S4 as claimed) The rank of `user` against `industry-estimate` is held by the agreement of its two copies, and no test pins it. Tried: G4 swaps the two classes in `PROVENANCE_ORDER` and `PROVENANCE_RANK` together; `check:plan` passes, 185 tests pass, and the weakest class of a user artifact beside an industry-estimate record becomes `user`. Each copy swapped by itself fails `check:plan`. Outcome: `scripts/check-plan.mjs:10-14` and ADR-011's E.15 note list what `check:plan` holds (the same classes in both, `measured` first and above `gold`, `industry-estimate` at or below `unverified`, the rank in the order's order), and G4 meets each one. ADR-006:198 names these classes without ranking them against each other, `src/components/Provenance.tsx:119` lists `industry-estimate` ahead of `user`, and no service path writes both classes. The behaviour reproduces and the written contract makes no promise about this pair's order (S4).
- **H13-03** (S3 as claimed) `pnpm ready`'s model rows check the plan and index routes. Explain, extract and judge routes moved to other models pass unchecked. Tried: with explain and extract moved to `claude-haiku-4-5-20251001` and judge to `claude-opus-4-8`, both rows read ✓ and the Models API is asked about the plan and index models. `llm.call` on extract and on judge then raises ModelUnavailable (404). With plan moved, the rows read ✗. Outcome: `docs/api/postdoc.md:214` and ADR-008's Implementation 17 (lines 441-444) say the model row names the plan route's models and effort and the roles row speaks of the index route, which is what the rows do; ADR-008 sets this reach, and CLAUDE.md:29 is a C line. The runbook's summary at `docs/runbooks/live-host-install.md:170-171` ("the routes' models through the Models API") reads wider, which the refuters graded wording drift (S4).
- **H13-04** (S4 as claimed) `pnpm eval` answers a missing or unknown project with tracebacks or an empty summary. `lit:graph` and `conform` refuse the same name in words. Tried: with no project, `eval seed` and `eval summary` exit 1 with a ProjectRequired traceback. With project `nope`, `eval seed` exits 1 with three chained foreign-key tracebacks and keeps 0 rows. With `nope`, `eval summary` exits 0 with the same empty summary a held project with no runs gives. Outcome: `core/openferment_core/projects/__init__.py:10-12` says "A store call that names none is refused in words", and the traceback's last line carries those words; ADR-005 gives the unknown-project refusal to the service and the MCP server, and `evaluation.py:38-39` keeps exit 2 for questions the suite cannot ask. The CLI is the evaluation set's one door, so no second door answers the same question; the behaviour reproduces and the written contract makes no promise about a command checking that the project exists (S4).
- **H13-05** (S4 as claimed) The example READMEs leave a stranger stuck: the mirror's check line fails from the directory its previous line names, and neither page names the database, the service or the project. Tried: line 10's `cd core && uv run ... conform mirror` exits 1 with "cd: core: No such file or directory" from the package's directory and from `core/`. From the repository root with no database named, conform refuses in words naming `OPENFERMENT_DATABASE_URL`. From the root with a migrated database, all eight checks hold. Outcome: the mirror page is a bulleted list with no line that orders its items, and line 10's `cd core` starts from the repository root, the form `CLAUDE.md:20` and `docs/api/engines.md:802` use; conform's refusal names the setting, and the page's line 3 names `engines.md`. The refuters graded it wording (S4); a prefix such as "From the repository root:" would close the reading.
- **H2-03** (S3 as claimed) A locked runbook's row can carry a `lockedAt` and `lockHash` that differ from its lock's, and the runbook then reads as a broken lock. Tried: a PUT to `/api/state/runbooks/{id}` with the frozen predictions and measures and a rewritten moment and digest answers 200. `GET /api/studies/runbooks/{id}` and the export then show the row's pair. `runbookLocks` keeps the true lock, the page reads "lock broken" (digest rewritten) or "locked" in 2020 (moment moved), and no audit row is written. Outcome: `docs/api/studies.md:170-175` refuses a runbook row whose predictions or measures differ from the frozen ones, and these match; `studies.md:184` lays the kept lock on a row that carries none, and `runbook_locks` stays insert-only with its audit row. `src/engine/lock.ts` says the digest "proves nothing about *when* the content existed", and the path needs a hand-built PUT that no screen or tool sends; the behaviour reproduces and the written contract makes no promise about the row's own lock fields (S4).
- **H2-05** (S3 as claimed) The export package leaves out the kinetic fits its forecast runs rest on. Tried: after a fit and a forecast, `study.json` holds the forecast run and its `growth_forecast` artifact, whose basis names fit `e79f2b2f29fbaba2` by id. The fit's artifact is absent, and none of its nine parameters appears in the package. Outcome: `docs/api/studies.md:240` says `study.json` holds "the artifacts that computed the runs and the comparisons", each run's inputs with their origins, and each deposition a reading rests on; `exports.py:97-102` gathers exactly that, `core/tests/test_exports.py:125` pins it, and `studies.md:234`'s "opens with nothing of openFerment's" concerns which software reads the package. The behaviour reproduces and the written contract makes no promise about following artifact sources; the second refuter graded it S3 had it stood.
- **H2-07** (S4 as claimed) One run of a plant's default configuration is kept as two study scenarios. Tried: scenario A (cane, no configuration) and scenario B (cane, S1) with the same values get two ids. Both run as the one runs row `882cd0100f8b6ea0` in S1, whose `scenarioId` names A, and both list that run. Outcome: `docs/api/studies.md:14` defines a scenario's id as "the sha256 of the plant, the configuration and the values", and `studies.md:30-32` keeps the configuration "as made", which for A is none; `scenarios.py:148` hashes that, and `docs/PROGRESS.md:465` records the C.4 choice. A asks for whatever the default is when it runs. B asks for S1. `runs.md:28` names the first asker in `scenarioId` (S4).
- **H2-08** (S4 as claimed) A comparison asked again with a title of spaces loses the title it was kept with. Tried: a second ask over the same runs with the title "   " answers 200, and the title becomes `''` in the answer, the list and the row; a first ask with a title of spaces is kept as `''` too. Outcome: `ComparisonCreate.title` carries `min_length=1` (`minLength: 1` in `openapi.json`), which three spaces meet before the strip, and the refusals at `docs/api/studies.md:149` name no blank title; a second ask taking the new title is the design `core/tests/test_comparisons.py:104-110` pins. The Studies screen trims the title and disables Compare as long as it is blank (`ProformaStudies.tsx:492`, `:582`), so the path runs through REST or the tool door; the behaviour reproduces and the written contract makes no promise about a title blank after the strip (S4).
- **H3-03** (S1 as claimed) A released measured value can be rewritten by any later write, with no audit row, and the service serves the new value as measured. Tried: measured evidence `me1` released at 40 g/L and then written again at 400 g/L under another name answers 200. `GET /api/state`, `runbooks_read` and the deposition screen serve 400 g/L as measured. The deposition's reading stays at 40.0, the audit holds the first keep, and DELETE is refused 422. Outcome: the `openapi.json` DELETE description ("a deposition, a measurement, a lock and a conversation stay as they were made") speaks of removal, which the service refuses. The PUT description reads "One row kept whole". The rule "a correction is a new reading" is written for depositions (ADR-006's C.5 note, `docs/api/studies.md`), and the one writer of measured evidence, the page's reconcile action, writes each row once; the behaviour reproduces through a hand-written PUT and the written contract makes no promise about rewriting measured evidence (the refuters graded it S4 and S3).
- **H3-04** (S2 as claimed) Measured evidence takes its measured mark from the page's own fields, for a deposition the project does not hold. Tried: a PUT of `measuredEvidence/me2` naming deposition `nope` at 999 g/L, confirmed, answers 200; `runbooks_read` marks it measured and `validate_plan` grades a claim citing it measured. Outcome: ADR-006's C.5 note (lines 242-243) describes the kind as "marked `unverified` where nobody read its number back", and `module_stores._measured_row` computes the mark from the row's `confirmed` field; `docs/api/studies.md` and the `openapi.json` 422 list the state door's refusals, and a check against a held deposition is absent from them. A control showed that a first write of a deposition naming a runbook the project lacks also stands as measured, so the check the hunt asked for would change nothing for a hand-written caller; the behaviour reproduces and the written contract makes no promise about it (S4).
- **H3-10** (S3 as claimed) A claim's estimate carries numbers in its unit, a field no rule reads. Tried: a stand-in model's claim with the unit "USD/gal, about 40 cents above the 2011 design" is kept as assumed and stored so in `openferment.turns`. A claim with a number in its basis is dropped. Outcome: ADR-006's Implementation 6.2 (lines 117-119) lists what drops a claim's value (no single source, an id no tool returned, a label or a basis holding a number, an estimate outside its range) and asks an estimate for "a unit", and `validate.claim_values` checks exactly these; `docs/api/postdoc.md:46-47` holds the claim's text to the number rule. Units carry digits ("g L-1", "1/h"), so a number rule on the unit would be a new rule; the behaviour reproduces and the written contract makes no promise about numbers in a unit (S4).
- **H3-11** (S3 as claimed) The claim door drops a model's estimate whose basis words hold a number. The tool door keeps the same words as the estimate's note. Tried: in one ask, claim `c1` with the basis "about 30% above the 2011 design report" is dropped. In the same ask, `study_scenario` keeps the same words as the model-estimate origin's note, the run's input note and the artifact's basis note. Outcome: ADR-006's Implementation 6.2 sets each door's rule. Bullet 1 (lines 117-119) drops a claim whose label or basis holds a number. Bullet 2 (lines 120-128) refuses JSON numbers outside a quantity and "keeps the note the caller wrote", and `docs/TOOLS.md:18-21` says "digits inside a string, an id or a name among them, are words". ADR-006 chooses both behaviours, the value stays marked as the model's estimate, and the run is assumed (S4).
- **H3-13** (S3 as claimed) `catalogue_write` keeps measured values written in words. Its description says "Names and words only, never a measured value". Tried: a write with the name "Strain making 45 g/L", the summary "reaches a titre of 45 g/L at 30 °C in 48 h" and the note "read from a paper: 0.45 g/g yield" answers 200 and is kept in the model's lane. The same door refuses the JSON number 45 in `summary`. Outcome: `docs/api/intake.md:83-86` says the numbers an entry holds are a person's own writing (a skill's policy, a lesson's minutes and checkpoint), and `intake.md:110-112` glosses "takes no number" as a model's skill holding no policy and a model's lesson holding no body; the tool's description lists its refusals, and a number in words is absent from them. ADR-006's 6.2 keeps words that state a number as words at a tool's door, and `find_number` flags real strain names and citations ("Zymomonas mobilis 8b", "ATCC 31821"); the behaviour reproduces and the written contract makes no promise about numbers in an entry's words (S4).
- **H3-15** (S4 as claimed) A deposition write may append a second entry under an id an earlier entry holds, and no ref can name the second reading. Tried: a second write appends a reading under `d1` at 99 g/L and answers 200. The readings list offers `depD/d1` at 10 g/L. On one measure each entry finds the other as its correction and the measure offers no reading, and a first write with two entries under one id is kept. Outcome: ADR-006:231 and `docs/api/studies.md:100-101` give the uniqueness of ids to the page's `timeId`, with the reason at `docs/PROGRESS.md:470`; the state door's permitted writes include an appended reading, and its refusals (held by `core/tests/test_project_state.py:233-267`) name no repeated id. `depD/d1` keeps naming its first entry and the path needs a hand-made HTTP body; the behaviour reproduces and the written contract makes no promise that every kept entry has a reachable ref, and the second refuter graded it S3 had it stood. H12 suspected the same; its bullet is below.
- **H3-17** (S4 as claimed) The catalogue route keeps an entry and drops a field no kind takes, with a 200. Tried: a strain carrying `titre` is kept with 200, and neither the answer nor the read-back holds `titre`. A species on a product is refused 422. Outcome: `docs/api/intake.md:89` reads in full "each kind's own fields are these, and a field of another kind is refused in words", and `titre` belongs to no kind; the `openapi.json` `CatalogueEntry` and `CatalogueKeep` schemas carry no `additionalProperties: false`, like 267 of its 286 schemas. Where the project refuses unknown keys it says so in words (the forecast request); the behaviour reproduces and the written contract makes no promise about undeclared keys (S4).
- **H4-01** (S2 as claimed) A library run's cost card closes on the package's set price, so its capital recovery line takes the whole NPV gap. Tried: cornstover and `cellulosic_ethanol_v0` agree in 118 streams, 68 units, every TEA total and the solved price 0.6588 USD/kg. The composed plant's card closes on its package price 0.7199 with Capital recovery 0.286 USD/kg against cornstover's 0.2249, the whole 0.061 gap. Outcome: `docs/PROGRESS.md:631`, a row of the Known debts "Left by decision" table, reads "A library run's TEA breakdown is read at the product's set price (`workers/library_plants.py` `_Module.parts` passes no price)", and records the card drawing the lines' own price with the solved price beside it. The recipe's "unit for unit" holds, and the card labels each price (S4).
- **H4-03** (S3 as claimed) A library run that sets any value simulates the plant again unsettled, so a value equal to the default moves the price in the fifth digit. Tried: setting `stream.cornstover.price` to its exact default moves the solved price from 0.658813642 to 0.6588285541 USD/kg (2.26e-5 relative) and the NPV to -20,477.5 USD, with both bases stating 10 significant digits; the result repeats to every digit across three services. Outcome: `docs/api/engines.md:249-251` defines precision as how near a replay comes to the run, and `engines.md:615-616`, `:52` and `:467` tie it to the same request; the two runs are different requests (`engines.md:33`), and run B replays to every digit. ADR-004:120-125 records 0.6588285541 as the price of "simulating the same plant again without settling it", within 1.5e-4 relative between simulation histories; the behaviour reproduces and the written contract makes no promise that a run setting a default equals the run that leaves it unset (S4, worth a debt line).
- **H4-05** (S3 as claimed) A batch with μmax zero is refused as one whose sugar never runs out. In such a batch, β or maintenance use the sugar up. Tried: `batch_v1` with μmax 0 and β 0.1 or m 0.1, asked to run until the sugar runs out, answers 422 "μmax is zero, so the cells never grow and the sugar never runs out: name a run length". Given a run length it answers 200, with the sugar out at 49.95 h and 99.9 h, as the hand calculation gives. Outcome: the texts quoted (`kinetics.py:59-61` and `:597-599`) are code docstrings, and they define the run by "horizons doubling from 1/μmax", which needs μmax above zero; `docs/api/runs.md:69` allows a kinetics refusal in fermOS's words for the integration. The refuters graded the refusal's phrase "the sugar never runs out" wording, with the workaround printed in the message (S4).
- **H4-06** (S3 as claimed) `cellulosic_ethanol_v0` reports its denatured product stream's mass as the ethanol made and as the ethanol per kg of dry feed. Tried: `ethanolKgPerH` is 21,978.38 kg/hr, the product stream's whole mass (ethanol 21,314.59, denaturant 473.10, water 177.23, NH3 13.45), and `ethanolKgPerKgDryFeed` is 0.2643; both stand 3.11 % above the ethanol by itself. Outcome: the package defines both quantities on the same denatured stream (`biorefineries/cornstover/model.py:27`'s "Ethanol production" is `ethanol.F_mass`, and `webapp_model.py:40-43` computes the yield the same way), CLAUDE.md says "a library plant carries its package's own numbers", and the TEA prices the same stream. The refuters graded it wording: the Comparison screen's labels could name the denatured product (S4).
- **H5-02** (S1 as claimed) A document two projects hold reads in B with A's title, private url, source and licence class. Tried: the same text pasted into A and B with different titles and classes gives B's documents, overlay and search reads A's title, A's url, the source `project:h502-a:paste` and A's licence class. B's link keeps B's own selection, and B's paste answer reported B's title and class. Outcome: ADR-002:78-80 chooses "A document is stored once (the kit's content hash) with source `project:<id>:<collector>`", with each project's selection on its link, ADR-002:82-85 makes a shared document visible to each project that linked it, and `docs/api/intake.md:31-37` lists title, licence class, source and source ref among the stored fields; the Intake card says the text is already in the instance. The residue is that B's chosen class is dropped and the overlay falls back to A's url and licence words, which the second refuter graded S3 as a design question for ADR-002. H8-02 joined this candidate.
- **H5-04** (S2 as claimed) DELETE `/api/state/runbooks` takes back a locked runbook and leaves its lock behind. Tried: DELETE of the lock is refused 422. DELETE of the locked runbook answers 200 `removed: true`, GET answers 404, the lock row stays, and a PUT with a moved prediction is refused 422. Making the runbook again answers `lockedAt` null. GET and the listing then answer it locked. Outcome: the `openapi.json` DELETE contract reads "One row taken back, a person's own undo; a deposition, a measurement, a lock and a conversation stay as they were made", and the lock stays; the refusal at `docs/api/studies.md:170-175` holds after the DELETE, and the stronger lines the hunt cited are code docstrings. No screen or tool removes a runbook, so the path is a raw REST call; the behaviour reproduces and the written contract makes no promise about taking back a locked runbook, and the second refuter graded it S3 had it stood. H2-04 joined this candidate.
- **H6-01** (S2 as claimed) A product alpha 2.1 kept with a category in its own words drops out of every head door after the upgrade. Tried: on an alpha 2.1 database with the products "biofuel" and "sugar alcohol", the head's migrations leave all three rows in `openferment.catalogue`. `GET /api/catalogues/product` lists cellulase, the two others answer 404, `catalogue_read` matches 1, and the service log carries a WARNING on each read. Outcome: `docs/api/intake.md:98` makes a product's category one of twelve classes, and `docs/PROGRESS.md:2826-2829` (E.gate) records the choice "a row of an older shape is left out and logged with why ... a person's keep writes it afresh", which `core/tests/test_catalogues.py:557-575` tests; ADR-007's `refused` list covers `GET /api/state`. No stored database holds such a row. The second refuter graded it S3 for a real alpha 2.1 install that upgrades.
- **H6-03** (S3 as claimed) `db:import-alpha1` answers a traceback with no `refused:` line for a duplicated paper, a missing database and a dead server. Tried: each case exits 1 with a Python traceback and writes nothing (0 projects, 0 candidate rows). `db:migrate` on the same two addresses answers "refused: ..." with exit 2. Outcome: `docs/runbooks/live-host-install.md:218-219` ("A line beginning `refused:` says why, and the import has written nothing") says what such a line means, and the import wrote nothing in each case; `import_alpha1.py:13-15` and ADR-001's "whole or not at all" hold, and `migrations.py:16-18` speaks of that module's own commands. Alpha 1.0 writes one candidates file a paper and each traceback's last line names the cause; the behaviour reproduces and the written contract makes no promise about the form of these failures (S4).
- **H6-04** (S4 as claimed) `db:import-alpha1` prints and audits a count of rows its upsert did not keep. Tried: a `guild.json` naming `p-ben` twice and an artifact copy file import with exit 0, and print and audit 3 people and 2 artifacts. The import keeps 2 and 1. Outcome: `docs/runbooks/live-host-install.md:217-218` gives a count the meaning "the number of decisions in the file", and the counts match the files; no line says a count equals the rows kept or that a repeated id is refused. Alpha 1.0 never writes an id twice, the person kept is the one alpha 1.0's own lookup returned, and the copy holds the same bytes; the behaviour reproduces and the written contract makes no promise about it (S4).
- **H7-03** (S2 as claimed) Two tabs on one deposition: the second tab's reading is refused and dropped. That tab keeps listing it as recorded. Tried: tab B's two writes are refused 422 and the service holds 7.7 USD/kg. Twenty seconds later the queue is empty and no toast shows. Tab B's bench, close dialog and record page then list 8.8 USD/kg as recorded and standing until a reload shows 7.7. Outcome: `docs/PROGRESS.md:641`, a row of the Known debts "Left by decision" table, records "Two devices writing one deposition: ... the page's own new entries go with the refused write, said in words", returned when accounts give pending writes a home on the service; `projectState.ts:159-160`'s "the row is dropped" speaks of the outbox entry. The debt row leaves open whether the refused page keeps showing those entries; both refuters graded that S3, and the doubt went to refuted.
- **H8-10** (S3 as claimed) A catalogue file with an id twice answers it kept twice. The first row is replaced with no word said. Tried: a file with two rows under `S5` answers 200 `"kept": ["S5", "S5"]` with two `keep_catalogue` audit rows. The catalogue holds the second row; the screen draws "Kept 2: S5, S5". Outcome: `docs/api/intake.md:104` keeps every row that is an entry with the file as its source and audits it, which both rows were; `intake.md:103` ("an entry under the same id replaced") and `docs/PROGRESS.md:497` ("A person's keep (the route, a file, `?by=`) replaces whatever the id holds") make the last row win. The behaviour reproduces and the written contract makes no promise about an id repeated within one file (S4).
- **H9-07** (S3 as claimed) `pnpm ready --offline` says Ready with a routing table that cannot route. Tried: for five tables that cannot route, `llm.routes()` raises RoutesInvalid and `check_model(have_key=False)` answers ✗. On the same tables, `ready --offline --no-workers` prints the model and roles rows as skips, then "Ready.", exit 0. Outcome: ADR-008:81-83 ("`pnpm ready` fails on it") names the plain command, which exits 1 on such a table (`core/tests/test_ready.py:158-161`); CLAUDE.md:29 is a C line, and `ready.py:5-6` defines `--offline` as "no network, and no key, because it makes no model call", with the skips pinned by `test_ready.py:475-484`. The host scripts call plain `pnpm ready`, and the second refuter graded it S3 had it stood; that refuter also saw plain `ready --no-workers` on a broken table end in an uncaught RoutesInvalid traceback from `check_roles` (`ready.py:499`), a matter of its own.
- **H9-14** (S4 as claimed) A NUL in an id answers with the database driver's error, its SQL statement and its parameters, in the tool's words. Tried: the id `a\u0000b` at `engine_report`, `flowsheet_read` and sci-rag's `get_document` answers "<tool> failed: DBAPIError ... [SQL: SELECT ...] [parameters: ('h914', 'a\x00b')]". An unknown id at the same doors is refused in the platform's words. Outcome: `docs/TOOLS.md:30-31` ("a refusal is `error`, in words") and `:907` ("said in words") hold, `tools/__init__.py:551-558` passes the exception's own message on purpose, and `core/tests/test_literature_mcp.py:194-201` pins the exception's message as the words. The message shows the caller's own project id and input and table names from the open code, and `docs/api/engines.md:419`'s "no traceback" covers worker refusals; the behaviour reproduces and the written contract makes no promise about what a failure's words leave out (S4).
- **H9-16** (S4 as claimed) At the tool door every caller from outside an ask shares one scope, so a second person's or assistant's proposal of the same action on the same target is refused as "already proposed in this ask". Tried: after Alice's lock proposal on `rb-same` (askId null), Bob's call (`?by=`) and the assistant `other/1`'s call are each refused with that sentence, naming Alice's card, and nothing of theirs is kept. Outcome: `proposals.py:20-21` and `:132-133` state the rule for an ask, and `models.py:248-249` leaves `askId` out for a write from outside an ask, which the tree keeps; the HTTP and MCP doors carry an empty ask id and apply one rule. The refusal names the waiting card, and the refuters graded the words "in this ask", said to a caller outside any ask, as wording (S4).
- **R1-02** (S4 as claimed) A Departures row says no store holds a protocol. E.12a made the protocols table and routes. Tried: `docs/PROGRESS.md:467` (row "alpha 2.2 D7, C.5") reads "No store holds a protocol in this build". On a fresh database `openferment.protocols` exists and `POST /api/protocols` answers 200. Outcome: CLAUDE.md:149 makes `PROGRESS.md` "the log of every stage, the departures, the debts and the blockers", each Departures row names its step in its Where column (here C.5), and the sentence was true at C.5; ADR-016:17 and ADR-017's Context keep it in their dated C.5 text, and line 503 and the ADR-016 Decisions row record the store since E.12a. No written rule asks for a departure's Why to be rewritten (S4).
- **R1-04** (S4 as claimed) Two Departures rows disagree on whether the browser keeps the lessons finished. Tried: line 543 (stage 2) says the browser keeps "the lessons finished here". Line 502 (E.12) says "The Durable snapshot keeps no lesson", and `snapshotOf` writes no key naming a lesson. Outcome: each row is true of the stage its Where column names (at stage 2's `fa16892`, `durable.ts:139` holds `learnProgress`), the E.12 row records the later change, and ADR-014:14 reads "until alpha 2.2 E.12 the lessons finished here". Every account of the current state agrees with the tree, and an "until E.12" pointer on the stage 2 row would be an editorial choice (S4).
- **R2-03** (S4 as claimed) No test holds the MCP `--service` relay's "no proxy" rule: `trust_env=True` leaves the suite green. Tried: mutation M16 (`trust_env=True` at `mcp_server.py:239`) passes all 51 tests of `test_mcp_service.py`. Under `HTTP_PROXY` with `NO_PROXY` unset, M16 sends the relayed calls with their project and assistant headers to the proxy. The code as it stands sends none there. Outcome: the texts cited (commit `6f85338`, the Service docstring, ADR-005:61, `docs/TOOLS.md:886`) describe the relay's behaviour, which the code keeps, and no test in the tree names the no-proxy rule (the file's docstring and `PROGRESS.md`'s D.0 test list leave it out). The refuters read it as a missing regression test for correct code (S4); running the served test under `HTTP_PROXY` with `NO_PROXY` unset would add one.

### Not reproduced

- **H11-02** (S3 as claimed) `OPENFERMENT_HOST` in the installing shell installs a server on every interface, and `guard.py` admits writes from any machine on the network. Tried: an install with the variable unset writes `127.0.0.1`. An install with `OPENFERMENT_HOST=0.0.0.0` writes `0.0.0.0` after one line of notice. A reinstall with it unset returns to loopback and says so. The guard answers 201 to a POST whose Host is a LAN address or a `.local` name. It answers 403 to a public domain. Outcome: the wide bind needs the person installing to set the variable for that install, and `docs/PROGRESS.md:3432-3435` ("Left for the owner") keeps it as "an install's explicit choice, default loopback", tested by `core/tests/test_host.py:160`; CLAUDE.md:137 is a stop condition on the builder, and the guard's Host rule is the one `guard.py:22-26` documents. The residue is wording (S4): `docs/runbooks/live-host-install.md:146` ("binds `127.0.0.1` and nothing else") and CLAUDE.md:52 leave the opt-in unnamed.
- **H12-15** (S4 as claimed) On Python 3.13 no test holds the IPv4-mapped address rule of the import-url check. Tried: dropping the normalisation (M57, `seen = address` at `collectors.py:287`) fails 4 tests on Python 3.12.3. On 3.13.17 it passes all 130. Over 231,072 mapped addresses, 0 answers move on 3.13.17. Over the same addresses on 3.12.3, 216,708 answers move. No address is let through on either version. Outcome: on 3.13 every `ipaddress` property `refused_class` reads defers to `ipv4_mapped`, so M57 changes no answer there and no 3.13 test could fail on it. On 3.12.3, the Python CI runs (CLAUDE.md:20), the four tests catch it. The worst case named is a developer in this container deleting the line as dead code and CI going red on the next push (S4).
- **H14-01** (S1 as claimed) A second comparison of the same runs rewrites the first comparison's title and keeps it in the first maker's name. Tried: Ada's ask and Ben's ask over the same runs answer one id. The title becomes Ben's. `by`, `at` and `created_by` stay Ada's, and no audit row names a comparison. Outcome: `docs/api/studies.md:127` ("the same runs in the same order are one comparison") and CLAUDE.md:56 hold, and `core/tests/test_comparisons.py:106-111` pins this behaviour, a second person retitling Ada Moreno's comparison with `by` kept as Ada Moreno; `scenarios.py:141-143` states the same for scenarios, and no document asks for an audit row when a comparison is kept. The residue is drift (S4): the Comparisons section of `studies.md` leaves unsaid that a later ask retitles the comparison and keeps its maker and time.
- **H14-09** (S4 as claimed) Studies says "Ran cornstover" for a run another person made days before. Tried: Person One runs cornstover through the API, and Person Two presses Run it on Studies; the card answers in 0.1 to 0.2 s with "Ran cornstover. Run bfda026530692adc ..." and names no keeper or time. The store keeps one row with Person One's `by` and `at`, and the runs table below the card shows Person One and the time. Outcome: `docs/api/runs.md:186-189` answers a held run as first kept, with the first asker's `by` and `at`, which the service does, and "Ran" reports the status of the run the card links to; no document asks the card to name a held run's keeper. Naming the keeper and the time on the card would improve the wording (S4).
- **H3-06** (S3 as claimed) A kept run stays measured after the reading it rests on is corrected. Tried: a kinetics run on nine readings reads measured on `GET /api/runs/{id}` and in the runs list before and after one reading is corrected. Asked again it is refused 422 naming the correction, the Proforma door refuses the reading, and the readings list offers the correction. Outcome: `docs/api/runs.md:22` moves a held row's label when a record is reviewed or demoted, `runs.md:21` counts a reading as a measurement, and ADR-006:237-238 promises the refusal "each time it runs", which the repeat ask gets; a plain GET of a run on a record reads its stored label too. No line gives a label for a kept run whose reading was corrected later, so a mark for that case would be a new rule in ADR-006 for the owner to choose (S4 drift; the second refuter read S3 had it stood).
- **H3-12** (S3 as claimed) A candidate keeps a method and an organism that carry numbers the cited section lacks. It drops a carbon source that carries one. Tried: the candidate anchors with 45 g/L inside its quote; the method "HPLC; a repeat at 30 °C reached 85 g/L in 48 h" and the organism "a strain that made 85 g/L in fed-batch" are kept as written. The carbon source "glucose at 120 g/L" is dropped with its reason counted. Outcome: CLAUDE.md:54 covers the record's value, which stands inside its quote. The Candidate comment holds the carbon source to the section and the number rule. It keeps the organism "the wording otherwise" (`models.py:962-964`, `validate.py:1165-1168`, `core/tests/test_validate.py:200-202`), and `FIELD_DROP_REASONS` names the carbon source as the one field a kept candidate can lose; `find_number` flags real paper wording ("Saccharomyces cerevisiae 424A(LNH-ST)", "HPLC (Aminex HPX-87H, 65 °C)"), so a number rule on these fields would need a decision record (S4).
- **H4-07** (S3 as claimed) `ethanol_glucose_v0` takes a titre at harvest that its beer never reaches. Tried: titre 70 g/L, feed 150 g/L and yield 0.45 give beer at 61.83 g/L on a 35 h batch (titre over productivity), priced at 1.0537 USD/kg with no refusal. Outcome: the line cited (`ethanol_glucose_v0.py:54`) is the input's label. The input's note (`shelf.py:85-87`), served on the shelf and as the panel's gloss, says the titre "with the productivity, sets the batch time; the beer's own ethanol follows from the feed's glucose and the yield, and the run reads it back"; the run reads back `beerEthanolGPerL` and `batchTimeH`. The residue is wording (S4): the label "ethanol titre at harvest", and `custom_train_v1`'s titre note (`shelf.py:156-159`), which leaves the beer's concentration unsaid.
- **H8-12** (S4 as claimed) An SFF file saved with a UTF-8 byte-order mark is refused as "not JSON" at line 1, column 1. Tried: the import door answers 422 "marked.json is not JSON: its text stops reading as JSON at line 1, column 1". The catalogue door keeps a CSV that carries the mark, and the worker's own toolkit check raises "Unexpected UTF-8 BOM" on the marked file. Outcome: `docs/api/sff.md:43-45` names "not JSON" as a ground for refusal, RFC 8259 §8.1 lets a parser treat the mark as an error, no reader in the tree reads a graph from those bytes, and stripping the mark would break the "kept byte for byte" row of `sff.md`. The residue is wording (S4): the refusal leaves out json's own reason, which passing `e.msg` through at `engine/sff.py:385` would name.
- **R2-02** (S4 as claimed) `conform` against a database the server lacks runs every check and exits 0. `migrations` refuses the same address in words with exit 2. Tried: `migrations migrate` exits 2 naming the missing database and `pnpm db:reset`. `conform biosteam` makes its eight checks on a scratch database, prints "the verdict could not be kept ... does not exist" and then "every check holds", and exits 0. `conform train --project p` exits 2 in words. Outcome: `docs/api/engines.md:801-808` says conform keeps its verdict "once that database is migrated; a verdict it cannot keep is printed with the words why", with exit 2 for no address or a server that does not answer, and `docs/PROGRESS.md` D0.7 (lines 1887-1889) and R4 (lines 2060-2061) give the missing-database refusal to migrations. The residue is wording (S4): under `--project`, the advice "Start it (pnpm db:up)" appears for a server that answers.

### Suspicions the hunts could not prove

- **H1** and **H3**: An origin's `at` is any non-empty text, and two requests whose `at` and note differ can share one run id. Tried: H1 read `basis.assumption_source` (`core/openferment_core/basis.py:78-84`): the basis note is `typed on <at>: <note>`, so `at` "2026-11-10: x" with no note and `at` "2026-11-10" with the note "x" write one note and one id. Not run; `at` accepts any words (a value at "whenever" ran, run `1d6e388bfc6027ab`). H3 read `EngineInput._names_who_set_it` and `Override`: nothing parses `at` as a time for a person's or a model's value. Not run through a door.
- **H1**: The Proforma worker, the worker the biosteam and train engines name, keeps the service's secrets in its environment. Tried: `simulator.worker()` builds `SimWorker` with `withhold_secrets` False (`engine/simulator.py:35-40`), and a crash's stderr tail reaches the 503 detail. `engines.md`'s worker rule is written for contract engines; no leak was produced.
- **H1**: Output strings have no length bound. Tried: a 10,000,000-character output string was kept done; the runs row held it (115 kB compressed) and `GET /api/runs` answered 10 MB. The contract states no bound, so it stays a note.
- **H1**: The path dependence of H1-04 may reach `custom_train_v1` and other cached shelf flowsheets. Tried: `ethanol_glucose_v0` was the one flowsheet run; `custom_train_v1` needs a kept vessel design and a kept train run, and H1 made neither.
- **H2**: A run's provenance on GET stays as kept after a record its basis rests on is reviewed or demoted, until the run is asked for again. Tried: read `compute_kept` and `artifacts.compute`: the row and the artifact follow a demoted record at the moment the same request is asked again (`runs.md:22` and `:173-176` say so). Proving a stale label on `GET /api/runs/{id}` needs a record in the evidence pool bound to a Proforma input, which needs an extracted candidate (a live model or a long intake chain); not built. H3-06 above, on a corrected reading, rests on the same rule.
- **H2**: A fermOS fit takes a `depositionId` the project does not hold, and its forecast reads as computed from bench readings. Tried: `POST /api/fermos/fit` with `depositionId` `dep-h2-g`, which no deposition row holds, was kept; `runs.md:81-82` names the series arriving as the browser sends them a known debt, so not filed.
- **H2**: `batch_v1` simulates to done with a product yield on substrate far above what mass allows. Tried: `POST /api/fermos/simulate` with `yps` 5.0 g g-1 kept a done run with no flag; the kinetics science is H4's to judge, so not filed.
- **H3** and **P**: A reading appended to a deposition by a second person names the deposition's first keeper as its depositor. Tried: H3 read `rows.put` (it keeps `created_by` on update) and `measurements.reading` (the maker is the row's `created_by`); with no accounts the hunt could not show two real people, and ADR-006 defines the depositor as the row's maker. P sent a PUT of `dep-p9` by Grace Hopper adding reading `de-p9b`, which was kept. `/api/depositions/readings` names the reading's `by` as Ada Moreno, the row's maker. `docs/api/studies.md:79` defines a reading's `by` as the deposition row's maker, so this follows the contract; whether a second person may write another person's deposition is left open in the pages read.
- **H3**: `units.convert(x, A, A)` is not the identity (201 mg dL⁻¹ gives 201.00000000000003). Tried: the Hypothesis test `test_self_is_identity_exactly` fails on the last digit. `measurements` skips conversion when the strings match. An alias spelling (mg/dL beside mg dL⁻¹) passes through `convert` and shifts the last digit, below any tolerance the doors hold.
- **H3**: `convert` answers inf for a finite value past a float's range and NaN for NaN, with no UnitError. Tried: 1e308 kg gives inf mg; every caller the hunt found guards it (`measurements` refuses a non-finite result, anchoring compares and fails, `Origin` and the doors refuse NaN). No path showed a stored infinity.
- **H3**: `quotes.is_whole_sentence`'s run-of-sentences rule might accept a fragment whose two ends equal whole sentences elsewhere. Tried: read `quote_units` and the startswith and endswith test; the hunt could not build a natural passage where a fragment starts and ends on a sentence that stands elsewhere and lifts a number out of its negation.
- **H4**: A train whose inlet is a vessel design carries about 1 % more product than the plant scale the vessel was designed at. Tried: vessel `9d857dedd0c2cb93` (plant scale 1000 t/yr, titre 2.854 g/L): plant scale over hours over titre is 44.24 m3/h. `train_spec._vessel_flow` reads working volume times vessels over cycle time, 360.213 × 2 / 16.127 = 44.67 m3/h (BioSTEAM sizes on the effluent's volume). The hunt built no train on a vessel inlet to read its product flow.
- **H4**: A simulation's productivity counts the product the batch started with. Tried: productivity is `finalTitre / harvestH` (`fermos.py:2298`); decay by itself with p0 1 g/L and no product made reports 0.0333 g/L/h, and fed-batch dilution with nothing made reports 0.075. Proforma uses titre over productivity as a batch time, so its price stands. The fermOS screen's figure is in doubt.
- **H4**: Thermo properties refuse every stream of the cornstover plant. Tried: `POST /api/thermo/props` on run `bfda026530692adc`, streams `ethanol` and `s24`, was refused (no chemical named Denaturant; DAP, Extract, Galactan, Z_mobilis; Lignin, Mannan cannot be built). `thermo.STREAM_RUNS` lists `library.run`, and the corn plant's ethanol stream answers. The refusal is the documented one, so the hunt left it as a doubt about use.
- **H4**: A train read from a cornstover run cannot run. Tried: `POST /api/pureos/train/from-run` on `bfda026530692adc` answers refusals [] and 12 units. `/train/check` and `/train/run` refuse it (the inlet carries 28 chemicals the yeast set lacks). `from_run.py`'s docstring names the one chemical set; the Builder is shown a train with no refusal that cannot run.
- **H5**: Audit ids and event ids count across projects, so B learns how much A does. Tried: `GET /api/audit` from A and B: the ids interleave (B 32-34, A 37-39), and SSE ids likewise (`events.py` says ids count up in this process). B can count A's rows between two of its own. Not filed: no contract names the id space.
- **H5**: Two `X-OpenFerment-Project` headers are accepted, and the first acts. Tried: `http.client` with two headers: bh-b then bh-a acts in bh-b, and the reverse acts in bh-a. "bh-b, bh-a" in one header is a 422. No contract line speaks of duplicates; not filed.
- **H5**: DELETE `/api/state/scenarios/{id}` of a study scenario says `removed: true`. The study scenario stays. Tried: before H5-03's overwrite, DELETE of a study scenario's id is a no-op answered `{removed: true}`; `StateTakenBack` reads "removed says the project holds no such row now", which is true of the Proforma kind. Folded into H5-03's area and left unfiled.
- **H6**: Alpha 2.1's Proforma runs replay at the head with a difference of 1 ulp. `runs.md:143` says they replay as they were. Tried: `replay_all.py` replayed every alpha 2.1 artifact at the head; every artifact other than the three `proforma.run` artifacts replayed identically. Those three differed (`tea.FCI` 31220166.41394996 against 31220166.413949955; `withinTolerance` false, since a Proforma run registers no tolerance). The same three replayed on a cold alpha 2.1 service also differ, and a Proforma run the head made over the upgraded database replays identically twice, so this reads as BioSTEAM's worker-state dependence (the known A-B-A drift); nothing here ties it to the upgrade.
- **H6**: A model's write to an id held by an unreadable catalogue row is refused with words pointing at the catalogues screen, which does not show the row. Tried: read `catalogues.py` `_keep` (the refusal names "a person keeps it afresh on the catalogues screen"); the head's `/api/tools` door is a person's, and no Postdoc or MCP model door was driven, keyless.
- **H6**: The head's service answers a bare 500 for a route whose table a skipped migration left out. Tried: the head's service over an alpha 2.1 database left at 0007 answers `GET /api/protocols` with 500 Internal Server Error and a ProgrammingError in the log; `pnpm ready` names the database "at revision 0007 of 0010. Run: pnpm db:migrate", and `deploy.sh` migrates before it restarts, so this needs a person to skip both.
- **H7**: One row the service answers with a 500 holds every later write in the queue behind it, retried every 15 s without end. Tried: read `src/lib/projectState.ts` `flush`: a ServiceDown stops the flush and keeps everything from that row on, and a 500 with health up becomes ServiceDown (`src/lib/http.ts:86`). The hunt found no way to make the service answer 500 on a row without editing the service.
- **H7**: A protocol run's id restarts at `run-1` on each page load, so an address of a run from before a reload opens a run started after it. Tried: observed `run-1` and `run-2` ids from `nextId('run')` (`src/store.ts:205`) across loads; the hunt did not start two runs of different protocols across a reload to show a mismatched version.
- **H7**: Two tabs that both load the same queue send each queued row twice. Tried: read `applyDurable` (`src/store.ts:2544`): every tab takes the stored outbox at load and flushes it; a deposition PUT twice with the same value is accepted, so no harm was shown.
- **H8**: An `http://` or redirecting yeastgenome.org address fails with a bare status in live mode. Tried: read `collectors.sgd` and `fetch_sgd`: http is taken and no redirect is followed, so SGD's own http-to-https redirect would answer "returned 301". Not run: it needs the live network, which the hunt's rules keep closed.
- **H8** and **H10**: The service reads a request body of any size before a limit applies: the upload doors spool the whole part to disk before their 50 MB, 16 MB and 4 MB checks, and a JSON body has no limit and a refused one comes back once per field error. Tried: H8 read `api.py:2084`, `:985` and `:1198`: `file.file.read(limit + 1)` runs after Starlette has spooled the whole part, and the answer is the 413 the contract names (51 MB and 17 MB files tried); a multi-gigabyte body was not sent on a shared machine. H10 sent a 64 MB JSON body to `POST /api/biorepo/check`, which was read whole (RSS from 465 MB to 813 MB) and answered with a 201 MB 422, the input echoed in each of three missing-field errors; a million-key body took 8 s and answered 67 MB, a 16 MB header and 20,000 headers were accepted, a 70 KB URL answered 400, and 100,000-deep JSON answered 400 in words. The guard refuses a cross-site write before the body is read, so the caller who reaches this is a local one; no contract names a limit.
- **H8**: A pasted or uploaded title holding a blank line splits into the passage text. Tried: read `kit.body_of` and the kit's chunker (content is the breadcrumb, a blank line, then the body): a title with a blank line moves its second part into the body `body_of` returns. Not run.
- **H9**: A call the API names by a served id the price table lacks (a dated snapshot of an alias) is charged 0 USD to the day. Tried: `served_id_price.py` ran `llm.call` with a stand-in client answering 100,000 input and 20,000 output tokens; served as `claude-opus-5-5` it charges 0.80 USD. Served as `claude-opus-5-5-20261101` it charges 0.0 (`usage_of` in `llm.py` prices by the response's model field). Whether the API ever serves another id for these routes needs a live call.
- **H9**: A stream that drops after the model has written output settles 0 USD on the day's spend. Tried: read `llm._call` and `converse`: on a TransportError or APIError after the stream opened, the cost stays 0.0 and `spend.settle(held, role, 0.0)` runs; whether Anthropic bills such a call needs a live model.
- **H9**: A count field takes `true` as 1. Tried: `fuzz_rest.py`: `search_records`, `search_passages`, `study_read`, `literature_sources` and `flowsheet_library` with `limit` or `k` set to `true` answered as a count of one (`numbers_in` skips booleans, and Pydantic reads `true` as 1). No contract names it; left as a note.
- **H10**: A websocket upgrade to any path outside `/rag` answers 500 with a traceback in the log. Tried: upgrade requests to `/api/health` and `/` answered 500 (StaticFiles asserts the scope type http). `/rag` paths answered 403. The http middlewares (guard, project) do not see websocket scopes, and no websocket route exists, so nothing is reachable through it.
- **H10**: The `/rag` key is looked up in a dict, with no rate limit on wrong keys. Tried: sci_rag's `StaticKeyBackend.authenticate` does `keys.get(token)`; its timing depends on a salted hash the caller cannot steer, so no timing probe was meaningful. `check_rate` runs after a key is found, so wrong keys are unlimited; a short `OPENFERMENT_RAG_KEY` would be open to guessing without limit, and `ready.py` checks that the key is present.
- **H10**: LIKE wildcards in `/rag/v1/documents?search=` are unescaped. Tried: `kit.py:467` `ilike(f"%{search}%")` binds the value. `%` and `_` act as wildcards inside the project's own documents. The reach stays within one project, so no cross-project read.
- **H11**: BSD grep's reading of `\s` in `has_key`'s placeholder pattern. Tried: read `scripts/host/lib.sh:92`. GNU grep reads `\s` as whitespace. If macOS's grep reads it as a literal s, the placeholder with trailing blanks or a carriage return counts as a key in `install.sh`'s message. No BSD grep in the container to run it.
- **H11**: `${changed//$'\n'/ }` inside double quotes on /bin/bash 3.2 (`deploy.sh:33`). Tried: it runs on bash 5.2 here (two dirty files named on one line). Building bash 3.2.57 from source to run it was refused by the sandbox; the line shapes a refusal message.
- **H11**: `install.sh`'s `tailscale serve status | grep -q ":$PORT"` under pipefail can read as not serving. Tried: `pipefail-grep-q.sh` shows the mechanism: a writer that prints more after the matching line dies of SIGPIPE (status 141), and the `if` takes the not-serving branch. Whether tailscale writes after its matching line, and late enough, needs the real CLI.
- **H11**: The checkout-location check misses a Documents path typed in lower case or reached through a symlink. Tried: read `install.sh:44-47`: the case compares the logical path, so `~/documents/openferment` on a case-insensitive volume, or `~/openferment` as a symlink into `~/Documents`, passes the check, and the jobs then meet macOS privacy protection. Needs macOS to run.
- **H11**: A deploy that stops at verify or the build leaves the pulled code and the synced venv under the running service. Tried: read `deploy.sh:41-92` and ran it on stand-ins: the pull, `pnpm install`, `uv sync` and the engines run before verify, so after a failed verify a KeepAlive restart (a crash, a power cut) starts the new code on the schema the migration never reached. The comment's claim about the schema holds. The pulled code and the synced venv change under the running service before verify runs.
- **H11**: `launchctl bootstrap` straight after `bootout` can fail with error 5 on macOS. Tried: read `install.sh:83-87` (one second's sleep after a bootout that succeeded). Under `set -e` a failed bootstrap stops `install.sh` with the server booted out. Needs macOS.
- **H11**: `wait_for_health` can answer from another process already on the port. Tried: read `install.sh:91` and `lib.sh:52-62`: any process answering `/api/health` on 127.0.0.1:PORT (a service started by hand) satisfies the wait, and meanwhile the job's server fails to bind and KeepAlive restarts it. Not run.
- **H12**: A request that names a key and no project leaves no audit row. Tried: `api.py:366-372` writes the `key_override` audit row inside a branch that needs `projects.current()` to name a project; the routes outside a project (`UNSCOPED`: `/api/health`, `/api/projects`) make no model call H12 found, and `/rag` and `/api/ask` were not traced to a model call with no project. Not proved.
- **H12**: A deposition write can append a second entry under an id it already holds. Tried: `project_state._appended` (`project_state.py:271-289`) checks that each held id stays in order and unchanged, and checks no new entry's id against the held ones; `measurements.reading` takes the first entry of an id. Read, with no write made to see what the readers then show. H3-15 above reproduced this. The refuters set it aside against the written contract.
- **H12**: A deposition entry confirmed as 1 or "true" is taken by the model. The lookup refuses it. Tried: `DepositionEntry.confirmed` is a lax Pydantic bool (`models.py:4886`), `project_state` keeps the raw value, and `measurements._held_to_rules` requires `is True`; a later write can then flip it to false, since `deposition_refusal` also reads `is True`. The hunt read the code and made no write; the browser sends booleans.
- **H13**: `pnpm eval run --suite ethanol` offline asks nothing and says nothing. Tried: ran `pnpm eval run --suite ethanol --only eq-eth-01` offline: `{"runs": [], ...}`, exit 0, with no words. `postdoc/evaluate.py:911` says that offline a question with no stand-in script is passed over. `evaluation.py`'s usage text and `docs/api/postdoc.md` leave this unsaid. Left as suspected, since the code's docstring states the behaviour.
- **H13**: `/api/health` reports ok with no database configured, so `prototype:up`'s, `install.sh`'s and `deploy.sh`'s health waits pass on a service that serves no project. Tried: observed in H13-01's run (health `{"ok":true}`, and `/api/projects` answered 503 in the same run). The health docstring says "Liveness, and what the service can actually do right now"; no contract names the database there, so it stays a suspicion folded into H13-01's evidence.
- **H13**: `GET /api/audit?limit=0` answers one row. Tried: `docs/TOOLS.md` says the newest `limit` rows (200 unless asked, at most 500); `limit=0` returned 1 row and `limit=600` every row of an 11-row project, so the upper clamp could not be seen at this size.
- **H13**: CLAUDE.md's first line says an R line names its source. Eight R lines name none. Tried: awk over CLAUDE.md: lines 50, 57, 58, 113, 114, 136, 137 and 140 name no source in the line (the stop conditions inherit their heading's §11.1), and `test_guidance` checks each line's label and reads no source. A wording matter.
- **H13**: verify's time is stated two ways. Tried: CLAUDE.md says nine to eighteen minutes, 12 min 11 s at the close. The runbook's `deploy --verify` row says about twenty minutes in this build's container. Not measured (the hunt does not run verify whole).
- **H13**: A restore of the nightly dump by a role that is no superuser exits 1. Tried: `pg_dump --format=custom` of `bh_h13_svc`, then the runbook's `createdb` and `pg_restore` into `bh_h13_restored` as the role `openferment`: the data and both schemas were restored. `pg_restore` exited 1 on `COMMENT ON EXTENSION vector` (must be owner). On the Mini the restoring user owns the cluster, so the runbook's line should hold there. This container cannot prove it.
- **H14**: A composed cellulosic plant reports 0.6 to 0.8 s a run. Cornstover reports 22 s. The two durations may mean the worker reuses a built system. ADR-004 says each plant is built fresh. Tried: read the durations on the run and reference pages (`b0d811fe46589558` in 0.6 s, `e7efa2505b4633de` in 0.8 s, `bfda026530692adc` in 22.1 s), `artifacts._run`'s timing (`core/openferment_core/artifacts.py:267-273`) and the worker's cache handling (`workers/library_plants.py:335-410`); the hunt found no reuse it could show.
- **H14**: Review decisions and comparisons leave no row in the audit log. Tried: `GET /api/audit?limit=500` after accepting, rejecting and flagging gold in Guild and after two comparisons: no row of either action. No contract line the hunt found requires an audit row for these writes, so it was left here; H14-01 above reads the same for comparisons.
- **H14**: A runbook made from a computed run wears "Assumed · rests on an assumption", and every prediction "low confidence". Tried: read `core/openferment_core/studies/runbooks.py:1-12` and `:130`: the service writes confidence low by its own rule, and the Assumed tick follows the same reading. A design choice, recorded here for the owner.
- **P**: The MCP servers can miss Claude Code's 30 s connect window at a session's start. Tried: this session's start reported `openferment` and `sci-rag` CONNECT_TIMEOUT after 30,000 ms. Started by `.mcp.json`'s exact command (`uv run --project core --all-extras python -m ...`), warm, each answered `initialize` and `tools/list` in 2.2 to 2.4 s over two rounds, and `uv sync --dry-run` said it would make no changes. A cold start under the load of many hunts starting at once is the likely cause; not reproduced.
- **R1**: Departures row 536 says `search_passages`' seam answers "no literature index exists yet". Tried: `git grep` finds no such words at `2047f5a`, and in `tools/passages.py` search runs Sci RAG Kit's retrieval. The row's own Why says stage 3 fills the seam, so a reader learns it was filled; left as a historical stage 1 departure, as R1-02 above reasons.
- **R1**: Departures row 546 says nothing reads `core/data/biorepo.json`. Tried: hunt P found `import_alpha1` reads it by default; the same row says `db:import-alpha1` carries it, so the words "nothing reads it" mean the service. Not reported.
- **R2**: The stage D strangers' transcripts (what each read and where each stalled) are absent from the tree. Tried: searched the tree for transcripts or logs of the two rounds; the report's "What it read" and "Where it stalled" paragraphs rest on transcripts outside git, so they stand as claims with no record in the tree.
- **R2**: The routing report's per-question scores and the judge's self-disagreement floor (0.023, 0.041, 0.032, 0.045). Tried: checked the report's internal arithmetic (differences, means, costs: all consistent); the per-run rows live in `openferment_dev`, which this hunt may not read, so the source numbers stay unchecked.

Merged before stage 3, each into the candidate named: H10-04 into H6-05, H12-01 into H9-08, H14-03 into H8-08, H2-04 into H5-04 (above), H8-02 into H5-02 (above), H8-09 into H10-03, R2-01 into R1-03, and R2-04 into R1-05.

## Needs a live model

These checks need a model's answer, so the hunts left them for a run with a key. The account refuses every model
call until 1 December 2026 at 00:00 UTC ("You will regain access on 2026-12-01 at 00:00 UTC", `docs/PROGRESS.md`,
Blockers). Every run on this list waits on that date, or on the owner raising the limit in the Anthropic console
(Settings, Limits). Each run goes from the repository's root with the owner's key in `core/.env` and spends under
the day's cap; Resume item 5 in `docs/PROGRESS.md` gives the order and the settings for the runs it names.
`pnpm ready --probe` goes first, since its probe row says whether the account answers. Each bullet says what to run,
what the run would show, and the hunt that raised it, with the finding it bears on. An id marked Suspected fell at
stage 3 and stands in the Suspected section.

### The key override on real calls

- **A named key on each route that calls a model.** Run: `POST /api/ask`, `POST /api/ask/stream`,
  `POST /rag/v1/answer`, `POST /api/literature/answer` and `POST /api/intake/{paper_id}/extract`, each with
  `X-OpenFerment-Key` holding a second key of the account and `core/.env` holding the first. Shows: the console's
  usage by API key, which names the key each call ran on, and the named key's text in zero lines of the service log,
  the stream's events, the turn rows and `GET /api/audit`, whose row for each call says `{"override": true}`.
  H9-01 shows `POST /api/literature/answer` running on `core/.env`'s key at a stand-in, so
  this run also checks its fix once the fix lands. Raised by H10 and H12; H12's stand-in client and tally show the
  request's context reaching the kit's calls (its mutations N01 and N02 were caught), and the console shows the key
  the API saw.
- **A named key the API rejects.** Run: `POST /api/ask` and `POST /api/literature/answer` with `X-OpenFerment-Key`
  holding a key the API rejects and a good key in `core/.env`. Shows: the words the answer carries, which `llm.py`
  writes as "The Anthropic API rejected the key this request named."; P tested this path with a local stub that took
  any key. Until H9-01 is fixed, `POST /api/literature/answer` answers here on `core/.env`'s key. A rejected key
  spends nothing. Raised by P.
- **The example's placeholder key in `core/.env`.** Run: a service over the `core/.env` that the live-host runbook's
  step 1 makes, whose key line is the example's placeholder; a question on the Postdoc screen, and the extraction and
  brief steps of `scripts/host/nightly.sh`. Shows: what the Postdoc screen and the nightly say when Anthropic rejects
  that key ("The Anthropic API rejected the key in core/.env." in `llm.py`'s words), on a service whose
  `GET /api/health` answers `hasKey: true` (H11-01). A rejected key spends nothing. Raised by H11.

### Postdoc's answers and the claim rules

- **The fourteen Ethanol questions, and Ask the agent.** Run: F.3 in Resume item 5's order, the fourteen of
  `--suite ethanol` asked on the Postdoc screen in the Ethanol project on the final routes, and one question through
  the command palette's "Ask the agent". Shows: each answer's claims with their typed values and origins, its
  citations and its trace cards, with the record going to `docs/reports/live-questions-2026-11.md`. Raised by H14
  and R1 (F.3).
- **Quantities in words inside claims and gaps.** Run: read the claims and gaps of every turn the fourteen and the
  evaluation runs keep (`GET /api/conversations`). Shows: how often a plan turn writes a quantity in words that
  `validate.find_number` passes ("two dollars per gallon", "ten per cent", "two thirds", "the high-90s", "doubled",
  "halved", "Table IV", "pH7"), and the provenance class each such claim keeps from its record. H3-02 and
  H9-04 show the validator keeping such claims and gaps over written plans. Raised by H3 and H9.
- **Numbers in an estimate's unit and a scenario's note.** Run: the same turns, with any `study_scenario` call they
  make. Shows: how often Postdoc writes numbers into a model estimate's unit or into the note of a scenario's
  model-estimate origin (H3-10 and H3-11, Suspected). Raised by H3.
- **A comparison's change in a claim.** Run: a Postdoc question that calls `study_compare` over two runs reporting
  one name in different units, such as a titre in g L-1 and in mg L-1. Shows: the typed value and the words a claim
  writes from the comparison's change, which H2-01 reckons across the units (+998.9998, printed in `study.md` as
  +99899.98%). H2 read the evidence ids and their values through `study_compare` at the HTTP tool door. Raised by H2.
- **A claim citing another project's passage.** Run: the two projects of `bughunt/repro/H5-01/run.sh`, with a Postdoc
  question in B during A's ingestion, `search_passages` in the loop. Shows: whether a claim in B cites A's passage, and
  what B's later reads of that claim give. Bears on H5-01. Raised by H5.
- **`ask_postdoc` over the MCP server.** Run: `ask_postdoc` on the `openferment` server as `.mcp.json` starts it,
  with `--project ethanol`. Shows: the answer, and the conversation, turn and tool-call rows the project keeps after
  it; H9-11 found zero such rows after a keyless decline. Raised by H13.
- **A product kept again by the model after the upgrade.** Run: on a database migrated from alpha 2.1 that holds a
  product a model kept with a category in its own words, Postdoc's loop, or `catalogue_write` at the MCP door, asked
  to keep that product again. Shows: the refusal's words the model meets, and what it tells the person, over a row the
  Products tab hides (H6-01, Suspected). Raised by H6.
- **Two tabs on one streaming turn.** Run: the Postdoc screen of one project open in two tabs, with a question asked
  in one. Shows: the turn's `tool.call`, `tool.result` and `turn.*` events from `GET /api/events` reaching both tabs'
  trace cards, and a tab that reconnects resuming from the last id it saw. H7 saw the stream reconnecting as the
  service refused. Raised by H7.
- **A conversation written through the queue.** Run: a question answered on the Postdoc screen, the service stopped
  as the answer lands so the page's Live conversation row waits in the browser's outbox, then the service started
  again; once with one tab and once with two. Shows: the row reaching the service and the conversation reading whole
  after a reload. H7-01 shows two tabs' queued rows erasing each other in the outbox. Raised by H7.
- **The grammar limit's fallback.** Run: Postdoc turns on the live routes with the service log open. Shows: whether
  the API answers "compiled grammar is too large" for the plan schema beside the strict tools, and when it does, the
  log's line that `llm.converse` sends the tools loose and the turn's answer on its second request. `llm.py` records
  the limit as measured on 30 October 2026 with seven strict tools. Raised by H9.

### Extraction and anchoring

- **Extraction over a held document.** Run: `POST /api/intake/{paper_id}/extract` (Intake's Extract) on a document
  the project holds, again on the same document, and once with `force=true`. Shows: the candidates with their
  anchoring, and the cached row the second call answers from. Keyless, the route answers 503 in words. Raised by H8.
- **A kept strain's alias in an extracted organism.** Run: a strain kept in the catalogue with an alias, a pasted
  document naming the organism by that alias, and Extract on it. Shows: whether the candidates' organisms carry the
  strain's id. H14-02 shows the anchoring vocabulary's strain map empty in the service, so the organism keeps its
  raw words and the strain page counts zero records. Raised by H14.
- **Cross-unit candidates from the live extractor.** Run: extraction over documents that give a minimum selling price
  in USD/gal and an ethanol concentration in % (v/v). Shows: whether the extractor files the price under
  `minimum_selling_price` in USD/kg, or the concentration under a titre in g/L; anchoring accepts both and labels the
  match converted (H3-01). Raised by H3.
- **Numbers in a candidate's method or organism.** Run: the same extraction. Shows: how often the extractor writes
  numbers into a candidate's method or organism (H3-12, Suspected). Raised by H3.
- **F.1's extraction counts.** Run: the Ethanol project's extraction over its 22 held documents with `force=true`; F.1
  spent 5.377950 USD over 31 calls on the `extract` route. Shows: counts to set beside the record's 457 candidates
  kept, 54 refused by the unit rule and nine Opus declines answered by Sonnet. Those figures come from live calls, and
  R2 read them as written. Raised by R2.

### Retrieval lanes and the concept graph

- **The concept graph build and its reads.** Run: `pnpm lit:graph --project ethanol --by <name>` (F.5), on the
  `index` route, then the `sci-rag` server's `search_entities` and `get_entity_relationships` with
  `--project ethanol`. Shows: the entities and relationships the build keeps over the project's passages (the dry run
  counts 92 batches over 814 passages), and the graph reads over real rows. H5 and H8 checked the reads over rows
  written by hand. Raised by H8, H13, P and R1 (F.5).
- **A graph build over a shared document.** Run: two projects that link one document, the graph built for one of
  them, then the other project's graph reads. Shows: whether a name one project's build kept as an alias, which the
  kit matches against every entity's aliases across the store at build time (`literature/graph.py`), reaches the other
  project's graph reads. Raised by H5.
- **The retrieval report's model lanes.** Run: `pnpm lit:report --project ethanol --by <name> --judge` (Resume item 5
  adds `--render`). Shows: the `full_deep`, `no_graph` and `no_hyde` lanes, the judge's relevance and the answers'
  grading over the project's 130 questions. Keyless, these lanes stop in words. H13-02 (Suspected) saw `--render`
  rewrite the committed report's hand-written sections. Raised by H8, H13, P and R1 (F.5).
- **A deep search with a key.** Run: `GET /api/literature/search?profile=deep` in the Ethanol project. Shows: the
  graph and HyDE layers' traces and hits, and `degradedStages` when one of their model calls fails (H8-06 shows a
  keyless deep search answering `degradedStages: []`). The same run shows whether the graph stage's entity extraction
  call matches entities over the project's eligible documents alone. Raised by H5 and H8.
- **A cited answer.** Run: `POST /api/literature/answer` (BioRepo Search's Answer), and `answer_question` on the
  `sci-rag` server with `--project ethanol`. Shows: the streamed answer, its citations, and each citation's passage id
  among the project's passages. Raised by H8 and H14.
- **An answer during another project's ingestion.** Run: the race of `bughunt/repro/H5-01/run.sh` with
  `POST /api/literature/answer` and `answer_question` in B during A's ingestion. Shows: whether the answer's citations name
  A's passage, as B's search did in H5-01. Keyless, the service refuses before it generates, so H5 raced the
  search alone. Raised by H5.

### Spend and billing

- **The probe.** Run: `pnpm ready --probe`, the first command of Resume item 5. Shows: the probe row green once the
  account answers, or the account's limit in words with the date the API gives. It makes one call on the `index`
  route, recorded at 0.000004 USD in commits `6a7ae97` and `7f813cd`. Raised by R1 and R2, with H13.
- **The graph build's real spend.** Run: `pnpm lit:graph --project ethanol --by <name>`, the same run as the graph
  build above, with its tally. Shows: the per-call charges on Haiku, to set beside the dry run's 0.2199 USD of input
  and 2.3239 USD at most, and beside the per-call figures of 0.0440 and 0.4648 USD in R1-03 (R2-01 joined it).
  Raised by R1 and R2.
- **A served id outside the price table.** Run: live calls on each route, with the model id each response carries as
  `llm.usage_of` reads it. Shows: whether the API names a served model by an id outside `llm.PRICES`, such as a dated
  snapshot of an alias. `usage_of` prices such a call at 0 USD: for 100,000 input and 20,000 output tokens, H9's
  `served_id_price.py` charged 0.80 USD as `claude-opus-5-5`. As `claude-opus-5-5-20261101` it charged 0.0 for the
  same tokens. Raised by H9 (Suspected).
- **A stream cut after output began.** Run: a streamed answer (`POST /api/ask/stream` or
  `POST /api/literature/answer`) cut at the network after its first text arrives. Shows: the day's spend settling
  0 USD for the call (`spend.settle(held, role, 0.0)` in `llm.py`), and the console's usage for that minute, which
  shows what Anthropic billed. The same run serves the error-stream check under Other. Raised by H9 (Suspected).
- **Refusals and their billing.** Run: the console's billing set beside the spend table for each refusal the live runs
  meet. Shows: whether each category bills as `BILLED_REFUSALS` in `llm.py` assumes when nothing came out (`bio`,
  `frontier_llm` and `reasoning_extraction` billed, every other category free, per the documentation read on
  8 October 2026). The spend table charged F.1's nine Opus declines in `bio` 1.216816 USD. Raised by H9.

### The evaluation and the judge

- **The routing report's open steps.** Run: in Resume item 5's order, the larger room's measure
  (`OPENFERMENT_PROJECT=ethanol OPENFERMENT_ROUTES="$OPENFERMENT_MAX" pnpm eval run --live --suite ethanol --tag
  opus-max-room --judge --only eq-eth-01,eq-eth-02,eq-eth-03,eq-eth-04`), the opus-max table's other ten on the same
  table and tag (`--only eq-eth-05` to `eq-eth-14`), the second judge
  (`OPENFERMENT_PROJECT=ethanol OPENFERMENT_ROUTES='{"judge":{"models":["claude-sonnet-5-5"],"effort":"max"}}' pnpm
  eval judge --suite ethanol`) and `OPENFERMENT_PROJECT=ethanol pnpm eval summary --suite ethanol --rows`. Shows:
  whether the plan's answers arrive whole at a room of 128,000, the table's fourteen at one room, and the Sonnet
  judge's reading, on which `docs/reports/model-routing-2026-11.md`'s rule and the `plan` default rest. Raised by R1.
- **The comparison's kept record.** Run: the first-pass judgements and the answers kept in `openferment_dev`'s
  `eval_runs`, read through `pnpm eval summary --suite ethanol --rows` beside the routing report's alpha 2.2 tables;
  the summary itself makes no call. Shows: the floor table's 11 pairs recomputed (mean absolute differences: answers
  0.023, grounded 0.041, labelled 0.032, coverage 0.045), each recorded answer and judgement as its run kept it, and, after the Sonnet pass, whether
  two judges disagree at least as much as one judge with itself, as the report assumes. Raised by R1 and R2.
- **The judge route's pass-overs and refusals.** Run: `pnpm eval run --live --suite ethanol --judge` and
  `pnpm eval judge --suite ethanol`. Shows: how the judge route passes over a model or meets a refusal on real
  judgements, and the summary's `judgesDisagree` over them. Raised by H9 and H13.

### Other

- **`pnpm ready`'s model and roles rows.** Run: `pnpm ready` with a key, once on the default routes and once with
  `OPENFERMENT_ROUTES` moving `explain`, `extract` or `judge` to a model the key lacks. Shows: the two rows against
  the Models API's own answers. H13-03 (Suspected) saw the rows ask about `claude-haiku-5-5`, `claude-opus-5-5` and
  `claude-sonnet-5-5` alone with those routes moved. Raised by H13.
- **The proof with the key and the network.** Run: `pnpm build && pnpm prove --live` (F.4). Shows: step 3 collecting
  the sources of `docs/corpus/ethanol-sources.txt` with the routed model extracting a paper, step 6 asking the routed
  models, and the proof's spend table holding each call. Raised by H13, R1 (F.4) and R2.
- **Primer Practice's drafting and tutor turns.** Run: Practice on a lesson in Primer, through
  `POST /api/practice/draft` and then `POST /api/practice/turn` with a trainee's answer. Shows: a drafted scenario
  whose values `practice.py` copies from the source it cites, or a refusal by rule with its spend, and the tutor's
  reply kept together with the trainee's answer. Raised by H14.
- **An error after the stream opens.** Run: `POST /api/literature/answer` and `POST /api/ask/stream` with the model
  call failing mid-answer, for example the network cut after the first text, as in the stream-cut check above.
  Shows: the `error` event's message, and whether it carries an exception's text with a file path. H8-08 shows the
  keyless answer stream ending in "ModelUnavailable: generation failed (see server logs)". Raised by H10.

## Coverage

The ledger is `bughunt/coverage.csv`: one row for every file alpha 2.2 changed (`git diff --name-only
112eb8b..2047f5a`), every operation in `docs/api/openapi.json`, every tool in `docs/TOOLS.md`, every rail entry and
screen, and every registered engine. Each row names the readers that examined it (the hunts H1 to H14, the paid-debt retest P and the records readers R1 and R2), how, and the candidates it gave. A row
can carry several methods; "read" counts rows examined by reading alone or with other methods.

| Kind | Rows | Examined | Executed | Fuzzed | In a browser | Read | Left, with the reason |
|---|---|---|---|---|---|---|---|
| Files changed since `112eb8b` | 456 | 454 | 217 | 55 | 153 | 153 | 2 |
| Operations in `openapi.json` | 133 | 133 | 111 | 133 | 1 | 0 | 0 |
| Tools in `docs/TOOLS.md` | 58 | 58 | 25 | 58 | 0 | 1 | 0 |
| Rail entries | 12 | 12 | 0 | 0 | 12 | 0 | 0 |
| Screens (`src/screens/`) | 55 | 55 | 0 | 0 | 55 | 3 | 0 |
| Registered engines | 4 | 4 | 4 | 1 | 0 | 0 | 0 |
| **All** | **718** | **716** | | | | | **2** |

716 of 718 rows were examined, 99.7 per cent. The two rows left are the files alpha 2.2 deleted,
`core/openferment_core/flowsheets/cornstover_benchmark.py` and `corn_drygrind.py`: they hold no code at the head, and
H4 compared the library plants that replaced them with a direct route through the package. 451 rows were examined by
two readers or more, 385 of them by two or more of the hunts H1 to H14. 281 rows name a candidate.

Each hunt left parts of its area unexamined and said why. Grouped:

- **Whole suites and the proof inside the hunts.** The hunts ran targeted tests on a machine they shared. The
  baseline ran `pnpm verify`, `pnpm test:sim`, `pnpm test:lit` and `pnpm prove` whole (Baseline, above). `pnpm smoke`,
  the walk and `pnpm prove` choose their own ports and database names, so the hunts ran their parts.
- **macOS.** This container is Linux. The host scripts were read against macOS's bash 3.2 and the BSD tools, run on
  stand-ins under bash 5.2, and held to ShellCheck 0.11.0; launchd, Homebrew's services, `pmset`, `fdesetup` and
  Tailscale were stood in for. Nothing ran on a Mac.
- **Docker.** `pnpm db:up` needs a Docker daemon, which this container lacks. `compose.yaml` was read.
- **A live model.** Every path that asks a model stops in words here; the section "Needs a live model" lists what waits.
- **Network collectors.** Europe PMC, OSTI and a library flowsheet fetched from GitHub need the network. The fixture
  collectors and the import-url door's refusals were run.
- **Engine paths that need a full worker run.** Valid runs of every library plant beyond cornstover, corn and the
  composed flowsheet; aerobic vessel designs; pureOS's in-house unit classes; and `kept_references.py`'s replays of the
  retired entries (the baseline's `test:sim` ran those replays green).
- **Screens that need state the hunts did not build.** BenchCheck (a Guild ledger with an assessor), the protocol
  editor's save path, and review decisions made while the service is away.
- **Records.** The Spend tables against the development databases (the hunts read no development database), CI run
  identifiers and timings on GitHub, and the per-commit test counts of intermediate commits.

## Fix order

The 92 findings fall into 63 groups, one for each cause a single change removes; a finding stands alone when no other
finding shares its cause, and the last group batches small drift and words. The groups run in the order a fixing run
should take them. Groups 1 to 17 are the S1 and S2 findings: project isolation (1), lost data (2 to 4), wrong
provenance labels (5 to 9), corrupted intake (10 and 11), wrong numbers (12 to 15), then the two S2 groups (16 and
17). Groups 18 to 23 make a later fix simpler or give it a test that holds: a shared `core/.env` reader, the model
layer's exception map, and the tests under the spend lock, the conformance checks and the request guard. Groups 24 to
62 follow by severity and size (S3 small from 24, S3 medium from 50, S4 from 55), each beside the groups of its area,
and group 63 is the batch of words. Groups 16 and 19 touch a stop condition of `CLAUDE.md`, and each says so: the
fixing run asks the owner before that change lands.

1. **The kit's project scope is read before its retrieval runs (`kit._narrowed`).** Closes H5-01 (S1). Files:
   `core/openferment_core/literature/kit.py` (`_narrowed`, `visible`). Size: small. The narrowing becomes a condition
   the retrieval statement evaluates itself, for example `Document.id IN` the documents the searching project holds,
   so a document another project commits during the search stays outside it. Extend
   `core/tests/test_literature_kit.py` with a search in project B during which project A commits a private document
   under the shared source, and assert B's passages hold none of A's.
2. **Each tab writes its own pending-writes queue whole under the one browser-wide Durable key (`snapshotOf`,
   `durable.ts`'s `KEY`).** Closes H7-01 (S1). Files: `src/store.ts`, `src/lib/durable.ts`. Size: medium. The save
   path merges the stored outbox with the tab's own before each write, or the tabs coordinate their saves; review
   decisions and Guild writes ride in the same snapshot and gain the same hold. Extend the outbox section of
   `scripts/check-state.ts` with two tabs saving in turn during an outage, and assert both tabs' queued writes reach
   the service.
3. **A scope's overrides travel as one list, and the service replaces the list whole (`rowsOf`, the overrides branch
   of `project_state._put`).** Closes H7-04 (S1). Files: `src/lib/projectState.ts`, `src/store.ts`,
   `core/openferment_core/project_state.py`. Size: medium. Each override is written by its own key, or a write names
   the rows it read and the service refuses it in words when the scope changed since, with those words on the page.
   Extend `core/tests/test_project_state.py` with two writes to one scope from two lists, each holding one key, and
   assert the first key stays kept or the second write is refused in words; `scripts/check-state.ts` holds the rows
   the client sends.
4. **`project_state._held` reads the written kind's rows alone, and `rows.put` upserts across kinds.** Closes H5-03
   (S1). Files: `core/openferment_core/project_state.py` (`_held`, `_put`). Size: small. `_put` refuses an id its
   table holds under another kind, in words naming that row; group 3 changes the same function on the service, so the
   two land together. Extend `core/tests/test_project_state.py` with a study scenario and a kept train, each written
   to through the other kind's id, and assert a 422 in words with both rows as they were.
5. **`biorepo._is_gold` reads a decision's provenance label.** Closes P-02 (S1). Files:
   `core/openferment_core/biorepo.py`; the tests that build a gold record from the label
   (`core/tests/test_agent_interface.py:53`, `core/tests/test_biorepo.py:458` and `:469`). Size: small. `_is_gold`
   reads the gold value alone, and its uses at `biorepo.py:279`, `:321`, `:367` and `:411`, `evidence_pool.py:97` and
   `import_alpha1.py:176` follow it. Extend `core/tests/test_biorepo.py` with a verified decision labelled gold with
   no gold value, and assert the record is stored and served verified.
6. **`import_alpha1._write` inserts decisions past the estimate rule.** Closes H6-02 (S1). Files:
   `core/openferment_core/import_alpha1.py`. Size: small. `_write` runs `basis.refuse_estimates` on each decision
   before any insert and refuses the whole import in words naming the file and the record, and the docstring at
   `import_alpha1.py:16-18` names that rule among the ones the import runs. Extend `core/tests/test_import_alpha1.py`
   with an alpha 1.0 file whose gold value carries a model-estimate origin, and assert the import is refused with no
   decision kept.
7. **Anchoring compares a quote's number bare when its unit does not convert, and labels the match converted
   (`_as_candidate_unit`, `value_basis`).** Closes H3-01 (S1). Files: `core/openferment_core/validate.py`. Size:
   small. Rule 3 refuses on rule `value` when the quote's unit fails to convert into a candidate unit rule 4 accepted,
   and `value_basis` sets `converted` from whether `convert` ran. This group goes ahead of group 8: a spelling that
   group stops misreading then fails to convert, and today's path would compare it bare. Extend
   `core/tests/test_anchor.py` with "$2.15/gal" against a USD kg⁻¹ candidate and "45% (v/v)" against a g L⁻¹
   candidate, each refused at anchoring and again at `biorepo.write`'s re-anchoring.
8. **`units.normalize` reads a spelling loosely, in Python and in its browser twin.** Closes H3-08 (S1), H3-07 (S3),
   H3-16 (S3). Files: `core/openferment_core/units.py`, `src/engine/units.ts`, `scripts/export-unit-fixtures.ts`.
   Size: small. `LABELLED_MASS_RATIO` keeps a joined label from completing a unit word (`gal`, `gallon`, `gmol`,
   `gpm`), the case-blind steps stop folding an upper-case SI prefix or symbol onto a lower-case key (`Mg`, `ML`,
   `Mm`, `S`, `G`), and `_STRIP_STEPS` and the browser's `strip` fold U+03BC onto U+00B5. Each spelling gets a fixture
   pair in `scripts/export-unit-fixtures.ts`, which `core/tests/test_units.py` reads, so the two twins are held to one
   answer.
9. **`validate.find_number` misses number forms Rule 1 forbids in a claim's words.** Closes H3-02 (S1), H9-04 (S3).
   Files: `core/openferment_core/validate.py`; `PRACTICE_QUANTITY` in `core/openferment_core/practice.py` as the
   record of forms already caught. Size: medium. The patterns take the six forms of H3-02 (one to ten before a unit
   word `_is_unit_word` misses, plural number words, U+00B2, U+00B3 and U+00B9) and the forms of H9-04 (multiplying
   verbs, ASCII Roman numerals, letters then a digit as in pH7 and x10), held against the false positives the comment
   at `validate.py:62-65` guards. Extend `core/tests/test_validate.py` with a fixture for each form, and keep the
   `core/tests/test_number_rule_*.py` files green as the hold on false positives.
10. **The kit's dedupe hash folds letter case, and `kit._store` links any duplicate as the same text.** Closes H8-01
    (S1). Files: `core/openferment_core/literature/kit.py` (`_store`). Size: medium. `_store` compares the held
    chunks' text with the entry's own before it links a `skipped_duplicate`, and says in words when a case variant is
    held; the kit's unique `content_hash` (`sci_rag/db/models.py:92`) stays the key. Extend
    `core/tests/test_intake.py` with two pastes that differ in letter case alone ("2000 mg" and "2000 Mg"), and assert
    the second keeps its own text or is answered in words.
11. **`collectors.uploaded` decodes an XML upload as UTF-8 with replacement before the parser reads its declaration.**
    Closes H8-04 (S1). Files: `core/openferment_core/literature/collectors.py`. Size: small. `uploaded` hands
    `split_jats` and `jats_citation` the file's bytes, so expat reads the declared encoding, or decodes strictly and
    refuses in words. Extend `core/tests/test_collectors.py` with a Latin-1 JATS file holding "5 µg/L" and a degree
    sign, and assert the stored text keeps both.
12. **A comparison row takes the first run's unit for every value (`comparisons._rows`, `_change`).** Closes H2-01
    (S1). Files: `core/openferment_core/studies/comparisons.py`. Size: small. `_rows` gives each unit of a key its own
    row, a form that needs no unit conversion. A form that converts each value through `units.convert` reads the table
    groups 8 and 38 correct, so it lands after them. Extend `core/tests/test_comparisons.py` with two runs stating one
    titre in g L⁻¹ and in mg L⁻¹, and assert each row reckons its change within one unit.
13. **`ethanol_glucose_v0.simulate` keeps BioSTEAM's default recycle tolerances on the one plant the worker holds.**
    Closes H1-04 (S1). Files: `core/openferment_core/flowsheets/ethanol_glucose_v0.py` (with
    `workers/proforma_worker.py`'s `_BUILT` as the plant it runs on). Size: medium. `simulate` sets recycle tolerances
    on the system and its subsystems tight enough that the sieve recycle `s9`, about 1 kmol/h at 1000 t/yr, keeps the
    loop iterating to convergence, so the base case and every fixed sample give one price. Extend
    `test_a_run_replays_within_the_precision_its_basis_states` in `core/tests/test_runs_sim.py` with a run near 1000
    t/yr whose fixed samples equal its base case; group 53 extends the same test.
14. **`custom_train_v1.parts` pairs a per-stream price with a per-kg-contained basis.** Closes H4-02 (S1). Files:
    `core/openferment_core/flowsheets/custom_train_v1.py`. Size: small. `parts` hands the cost card a price and a
    basis flow on one basis, the stream's mass or the price per kg contained, so the card's lines close on the price
    its label names. Extend `core/tests/test_custom_train.py` with an assertion that the lines sum to `productPrice`
    on that basis.
15. **`graph_command` prices the dry run's summed prompts as one request.** Closes R1-03 (S1). Files:
    `core/openferment_core/literature_live.py`; the record lines at `docs/reports/literature-retrieval.md:116-117` and
    `docs/PROGRESS.md:609` and `:3372`. Size: small. `graph_command` prices each batch's prompt with `llm.cost_usd`
    and sums the results, so the long-prompt rate applies per request, and the record lines take the per-request
    figures. Extend the test at `core/tests/test_literature_live.py:97`, which asserts `0 < inputUsd < mostUsd` alone,
    with batches each under the long-prompt threshold whose sum passes it.
16. **The kit-answer thread starts with an empty context and drops the request's key (`kit.answer`).** Closes H9-01
    (S2). Files: `core/openferment_core/literature/kit.py:825`. Size: small. The thread runs on
    `contextvars.copy_context().run`, as the ask stream's thread does at `api.py:614`, so a key named in
    `X-OpenFerment-Key` serves the kit's answer call. The change sits on the per-request key override's path, a stop
    condition in `CLAUDE.md`, so the fixing run shows it to the owner before it lands, as the change that brings the
    route to what question 10 authorized. Extend `test_the_kits_calls_and_the_requests_threads_reach_the_named_key` in
    `core/tests/test_key_override.py` with a `POST /api/literature/answer` carrying the header, and assert the model
    call ran on the named key.
17. **`validate.vocabulary()` hands anchoring an empty strain map, and the catalogue's aliases never reach
    `strain_id`.** Closes H14-02 (S2). Files: `core/openferment_core/validate.py`,
    `core/openferment_core/catalogues.py` (`as_strain_aliases`); the two tests that monkeypatch `validate.vocabulary`
    (`core/tests/test_validate.py:160-169`, `core/tests/test_fermos_bind.py:142`). Size: medium. `strain_id` reads the
    open project's strain catalogue, with the vocabulary cache keyed by project and cleared on a keep; it reads
    through `catalogues._entries`, the reader group 57 changes, so the fixing run settles once what that reader
    answers with no project open. Extend `core/tests/test_validate.py` with a strain kept with an alias and a record
    naming the alias, and assert anchoring resolves it to the strain's id.
18. **Each script decides by hand whether `core/.env` names a setting and how a line joins the file.** Closes H11-03
    (S3), H11-05 (S3), H11-06 (S3), H13-01 (S3). Files: `scripts/host/lib.sh`, `scripts/session-start.sh`. Size:
    small. Two helpers in `lib.sh` read the file's own last line for a name in python-dotenv's forms (the pattern at
    `lib.sh:111`) and append a setting on a line of its own (as `lib.sh:163` does) to a `core/.env` they make at mode
    600 when it is absent, and `ensure_database` and the two append steps of `session-start.sh` (`:47-48`, `:62-63`)
    call them. The key-line half of H13-01's proposal changes how a key is stored and goes to the owner with group 19.
    Extend `core/tests/test_host.py` with a shell that exports the database address, a file in the `export` and spaced
    forms, a last line with no newline, and no file at all, and assert each run leaves one database line the service
    reads.
19. **The key check is written four times, under two rules.** Closes H11-01 (S3), H11-08 (S4). Files:
    `core/openferment_core/api.py:488`, `core/openferment_core/checks.py:664`, `core/openferment_core/ready.py`
    (`check_key`, `PLACEHOLDER_KEY`), `scripts/host/lib.sh` (`has_key`). Size: small. `/api/health`'s `hasKey` and the
    nightly brief's missing-key test use the rule of `ready.check_key`, which refuses the example's placeholder, and
    `has_key` reads the file's last key line through the reader of group 18, as python-dotenv does; each part changes
    how a key is read, a stop condition, so it goes to the owner with question 13 (`docs/PROGRESS.md:669`) first.
    Extend `core/tests/test_ready.py` and `core/tests/test_host.py` with the placeholder key and with a `core/.env`
    holding two key lines, and assert the four checks give one answer.
20. **`extract.call_model` and `postdoc_agent.ask` map the model layer's exceptions by the wrong class.** Closes H9-02
    (S3), H9-03 (S3), H9-06 (S3). Files: `core/openferment_core/extract.py` (`call_model`),
    `core/openferment_core/postdoc_agent.py:709-710`, `core/tests/test_writes.py:363-366`,
    `core/tests/test_proposals_review.py:74-77`. Size: small. `call_model` re-raises `llm.BudgetExhausted` in a clause
    ahead of its `ModelUnavailable` clause and answers `RoutesInvalid` in words, and `ask` reads `llm.chain("plan")`
    and `llm.routes()` inside a handler that turns `RoutesInvalid` into a declined plan beside the
    `BudgetSettingInvalid` one. The two spend-gate tests then drive the refusal through `llm.call` under a tiny daily
    cap with a client that never sends, and the break they must catch is today's `call_model` wrapping
    `BudgetExhausted` as `ExtractUnavailable`, which leaves the proposal branch at `tools/writes.py:1171` unreached. A
    routing table `llm.routes()` refuses joins `core/tests/test_postdoc_agent.py` and `core/tests/test_extract.py`,
    answered in words at both doors.
21. **The tests' one connection serialises every session, so spend's day lock is never raced (`db/session.py:99`).**
    Closes H12-03 (S3). Files: `core/tests/test_spend.py`. Size: small. One test points `spend._ENGINE` at an engine
    of its own on the test database, as `conftest.py:47-48` does for live tests, races threads through `spend.reserve`
    behind a barrier against a small cap, asserts the cap holds, and deletes the day's committed rows after. The break
    it must catch is the advisory lock deleted from `spend._reserve` (`spend.py:156`); it comes ahead of groups 24 and
    25, which change `spend.py` under it.
22. **The conformance suite reads checks 1, 3, 4, 5 and 8 on conforming engines alone.** Closes H12-02 (S3). Files:
    `core/tests/test_engines.py` (five negative tests, drafted in `bughunt/repro/H12-02/test_zz_h12_02_probe.py`, and
    a whole-word read of check 5's words at `:2047`). Size: small. Each new test hands `conform` an engine or a
    service that breaks one check, and the break each must catch is that check made to hold anything: check 1 passing
    an engine it never reached, check 3 a run no row keeps, check 4 a replay that differs, check 5 an SFF file that
    fails validation, check 8 a row with the wrong `created_by`. It comes ahead of groups 24, 29 and 30, which change
    the engine contract's code under these checks.
23. **The refusal branches of `guard.py` stand with no failing case.** Closes H12-04 (S3), H12-09 (S4), H12-08 (S4).
    Files: `core/tests/test_request_guard.py`, `core/tests/test_key_override.py`. Size: small. Refused cases join the
    guard's tests, each holding one break: a POST with Host `127.0.0.1:8000`, Origin `http://rebind.evil.example.com`
    and X-Forwarded-Host `rebind.evil.example.com` answered 403 catches the forwarded-host check deleted from
    `guard.py:133`; Hosts `rebind.evil.example.net` and `evilts.net` answered 403 catch the suffix check at
    `guard.py:78` widened past `.ts.net`; a Funnel GET naming a key catches the Funnel clause of `key_refusal`
    (`guard.py:100-101`) dropped, and `llm.request_key` called with a blank key catches the blank-key rule at
    `llm.py:699` dropped. They come early because `guard.py` sits under a stop condition, and every later change to
    the service's doors runs against them.
24. **Three readers hold a number to its sign or its type and leave out finiteness.** Closes H1-06 (S3), H9-08 (S3),
    H9-12 (S3). Files: `core/openferment_core/models.py` (`EnginePrecision`), `core/openferment_core/spend.py`
    (`_setting`), `core/openferment_core/tools/__init__.py` (`numbers_in`, `non_finite_in`). Size: small.
    `EnginePrecision` refuses `inf` and `nan` (pydantic's `allow_inf_nan=False`), which `WorkerEngine._listed` then
    reports as `EngineBroken`; `spend._setting` tests `math.isfinite`; and `numbers_in` and `non_finite_in` count an
    integer `models.float_holds` rejects as non-finite, ahead of the `try` in `tools.run`. Extend
    `core/tests/test_finite_inputs.py` with an engine listing an infinite `atol`, budget settings of `nan` and `inf`,
    and a 400-digit quantity value, each refused in words.
25. **`spend._settle` charges the day of its own clock, and a day's check counts that day's holds alone.** Closes
    H9-09 (S3). Files: `core/openferment_core/spend.py` (`_settle`, `_day_state`). Size: small. `_settle` writes the
    cost on the reservation's own day, or `_day_state` counts every unexpired hold whatever its day. Extend
    `core/tests/test_spend.py` with a hold taken just before midnight UTC and settled after it under a stand-in clock,
    and assert the new day's spend stays inside its cap.
26. **`_out_of_budget` is asked after a round spends, and `_turn_tokens` gives a round every dollar left.** Closes
    H9-05 (S3). Files: `core/openferment_core/postdoc_agent.py` (`_attempt`, `_turn_tokens`). Size: small. Each round
    is sized to leave the answer turn's worst case inside `OPENFERMENT_ASK_BUDGET_USD`, and the stop check prices the
    next round together with the answer. Extend `core/tests/test_postdoc_agent.py` with a stand-in client at the real
    prices, and assert a question's spend stays at or under the 0.75 USD default.
27. **`postdoc_agent.ask` cuts the plan chain at two models.** Closes H9-10 (S3). Files:
    `core/openferment_core/postdoc_agent.py:714` and `:728`. Size: small. The loop walks the whole plan chain, as
    `llm.call` walks a route (`llm.py:859`), or `docs/api/postdoc.md`, the routing notes in `llm.py` and the health
    field's words state the one-restart cap; it edits the lines group 20 moves into a handler, so it follows that
    group. Extend `core/tests/test_postdoc_agent.py` with a three-model plan route whose first two models fail, and
    assert the third receives the question.
28. **`llm._call` builds the Anthropic client before it reads each model's provider.** Closes P-01 (S3). Files:
    `core/openferment_core/llm.py:844`. Size: small. `_call` builds the Anthropic client at the first Anthropic model
    its loop reaches, so a route of one local model runs with no key. Extend `core/tests/test_llm.py` with a keyless
    call on a local-model route that passes no `client_factory`, the path the test at `test_llm.py:900` passes over.
29. **A configuration name is resolved by different rules at different doors.** Closes H1-05 (S3), H1-08 (S3), H2-06
    (S3). Files: `core/openferment_core/engine/biosteam.py` (`default_configuration`, `run`, `parameters`),
    `core/openferment_core/engine/runs.py` (`thing_of`), `core/openferment_core/models.py` (`EngineThing`),
    `core/openferment_core/api.py:1315` (`library_regression`). Size: small. The biosteam engine's run and parameters
    check a named configuration against the thing's listed ones before any build, `library_regression` resolves its
    configuration through `default_configuration` as `library_parameters` does, and `EngineThing` refuses a
    configuration name that differs from its stripped self. Extend `core/tests/test_engines.py` with an unlisted
    configuration at both biosteam doors (refused with no build and no row) and a listed name with spaces (refused at
    listing), and `core/tests/test_library.py` with the regression route for a configured plant asked with no
    configuration.
30. **`conform._inside` asks `engine.unready` before it enters the checks' project.** Closes H1-03 (S3). Files:
    `core/openferment_core/engine/conform.py:1050`. Size: small. `_inside` enters the project it makes, then asks
    `unready`. Extend `core/tests/test_engines.py` with the documented conform command for a scenario flowsheet, and
    assert it keeps a verdict.
31. **`keep_run` reads the held row and then upserts, with no lock between the two (`engine/runs.py`, `rows.put`).**
    Closes H1-01 (S3). Files: `core/openferment_core/engine/runs.py` (`keep_run`, `compute_kept`). Size: small.
    `keep_run` writes through `rows.put_first`, or a lock holds from the held check in `compute_kept` to the write, so
    identical asks compute once and the row names one asker. Extend `core/tests/test_runs.py` with two identical runs
    asked at once, and assert one computation and a row whose `created_by` and body come from one ask.
32. **`kinetics.mass_balance` scales the gap by the sugar consumed.** Closes H4-04 (S3). Files:
    `core/openferment_core/kinetics.py:1346`. Size: small. The scale becomes the sugar the run handled, its start plus
    what was fed. Extend `core/tests/test_kinetics.py` with a no-uptake fed-batch, and assert a gap near zero and no
    "does not close" flag.
33. **Text the database and the JSON encoder cannot hold (U+0000, a lone surrogate) reaches them unrefused.** Closes
    H10-02 (S3), H9-13 (S4), H8-03 (S3). Files: `core/openferment_core/api.py` (the handlers at `:424-426`, the tool
    door at `:2960`), `core/openferment_core/literature/collectors.py` (`uploaded`), `core/openferment_core/intake.py`
    (`store`). Size: small. One shared check refuses U+0000 and lone surrogates in path ids, query filters and body
    strings with a 404 or 422 in words, or the database's data error maps to a refusal beside `api.py:424-426`.
    `collectors.uploaded` applies the check after `unquote`, so an upload stops before the kit keeps a document, and
    `intake.store` answers any other store error as a `failed` outcome. Extend `core/tests/test_route_models.py`,
    which already reads every route, with a NUL case and a surrogate case at each door, and
    `core/tests/test_intake.py` with an upload named `report%00.md`.
34. **`fermos.forecast_run` catches `FileNotFoundError` around a read that raises `ArtifactNotFound`.** Closes H5-05
    (S3). Files: `core/openferment_core/fermos.py:927`. Size: small. It catches `artifacts.ArtifactNotFound` and
    `ArtifactDamaged` and raises `FitRefused` in words, as `_fit_art` does at `fermos.py:1704-1711`, and the tool door
    then carries the same words. Extend `core/tests/test_fermos.py` with a forecast naming a fit the project does not
    hold, and assert a 422 in words at the route and the same words at the tool door.
35. **`collectors._fetch` catches `httpx.HTTPError` alone, and a redirect's `InvalidURL` escapes it.** Closes H8-05
    (S3). Files: `core/openferment_core/literature/collectors.py:445`. Size: small. `_fetch` catches
    `httpx.InvalidURL` beside `httpx.HTTPError` and raises `HostFailed` in words naming the redirect. Extend
    `core/tests/test_sff_url.py` with a stand-in transport answering a Location that has a scheme and no host, and
    assert a refusal in words.
36. **`report.py` keys the kit rule's question document by its title.** Closes H8-07 (S3). Files:
    `core/openferment_core/literature/report.py:364` and `:450`. Size: small. The kit column scores by `document_id`,
    which `Asked` already holds (`report.py:366`), or by a quote match. Extend `core/tests/test_literature_report.py`
    with two documents of one title, and assert a passage of the other document counts as irrelevant.
37. **The sci-rag MCP server passes any named project id (`literature_mcp._named`).** Closes H5-08 (S3). Files:
    `core/openferment_core/literature_mcp.py:68-70`. Size: small. `_named` checks that the id is valid and held,
    cached once held as `mcp_server._Store.refusal` caches it, and refuses in words naming the missing project. Extend
    `core/tests/test_literature_mcp.py` with an id the database lacks, and assert the refusal names it.
38. **`units.json` files every percent denominator in one family at factor 1.** Closes H3-09 (S3). Files:
    `core/openferment_core/schema/units.json`, `src/engine/units.ts`, `scripts/export-unit-fixtures.ts`. Size: small.
    Each denominator (% DW, % v/v, % of total protein) gets a family of its own, with refusal rows in the words of
    `units.json:558`. A fixture pair for each conversion that now refuses joins `scripts/export-unit-fixtures.ts`,
    read by `core/tests/test_units.py`.
39. **`measurements.corrected_by` ties a correction to its reading by the current sample time, and no test reads its
    choice of the last correction.** Closes H3-05 (S3), H12-12 (S4). Files: `src/store.ts` (`setSampleTime`),
    `core/openferment_core/project_state.py` (`deposition_refusal`), `core/tests/test_measurements.py`. Size: small.
    `setSampleTime` and `deposition_refusal` move a correction's hour with its reading's hour, in the panel and on the
    service. Extend `core/tests/test_measurements.py` with a correction given its own sample time after it is made,
    asserting the mis-read stays corrected, and with a reading de-1 corrected by de-3 and again by de-10; the break
    the second case must catch is a `corrected_by` that names the first correction (`later[-1]` at
    `measurements.py:104` turned to `later[0]`).
40. **The released band of DepositionDetail draws every released value as measured.** Closes H3-14 (S3). Files:
    `src/screens/DepositionDetail.tsx:511` and `:516`. Size: small. The badge and the tick read `e.confirmed`, or the
    service's computed class (`module_stores.py:475-476`). Extend `scripts/walk.ts`, which deposits a reading on its
    way, with an unconfirmed released value, and assert the band shows it unverified.
41. **`capture.normalise` strips every comma.** Closes H14-07 (S3). Files: `src/engine/capture.ts:28`. Size: small.
    `normalise` keeps a comma between digits as a thousands separator when exactly three digits follow it, and
    `matchToSchema` keeps any other comma between digits as an observation. Extend `scripts/check-state.ts` with "7,4
    g/L", "0,74 g/L" and "1,200 rpm", and assert the first two file as observations and the third reads 1200.
42. **Witness counts precision as defined after one rejection. Its callout counts it on the gold set.** Closes
    H14-04 (S3). Files: `src/screens/Witness.tsx` (`:379`, `:480`, `:490`). Size: small. The tile, its delta and the
    CSV row count precision as defined once the gold set holds a value (`goldSize > 0`), as the callout does. Move
    that rule beside the precision it guards in `src/engine/metrics.ts`, and extend `scripts/check-state.ts` with an
    empty gold set and one rejection, asserting no precision is written.
43. **App's project effect reopens an address id the store swapped for a held one.** Closes H7-05 (S3). Files:
    `src/App.tsx:140-142`, `src/store.ts` (`openProject`, `loadProjects`). Size: small. The effect compares the
    address's id with the project list before opening it, and an id the list lacks shows a screen naming the missing
    project. Extend `scripts/smoke.ts` with an address naming an id the service lacks, and assert one load and that
    screen.
44. **The rail's logo link is written by hand as `#/`.** Closes H7-08 (S3). Files: `src/App.tsx:498`. Size: small. The
    anchor takes `href('/')`, as the rail entries and Settings do. Extend the link checks of `scripts/check-state.ts`
    (`:920`) with the logo inside a project, and assert its address keeps `/p/<project>`.
45. **The detail pages' not-found branches read the store's lists. They read none of its load problems.** Closes H7-06 (S3).
    Files: `src/screens/RunbookDetail.tsx:584`, `src/screens/DepositionDetail.tsx:249`,
    `src/screens/PaperReader.tsx:254`, `src/screens/GuildSkills.tsx:83`, `src/screens/Postdoc.tsx:395`. Size: small.
    Each branch reads its load's problem (`stateProblem`, `cataloguesProblem`, `serviceUp`) and says it, as
    `src/screens/StrainPage.tsx:908-917` does. Extend `scripts/smoke.ts` with the five pages opened as the service
    answers 503, and assert each names the failed load.
46. **Deposition's Next step button and its staged runbook link fall short of 44 px.** Closes H7-07 (S3). Files:
    `src/screens/Deposition.tsx:954-960` and `:351`. Size: small. The button gains a `minWidth` of 44 px or more, and
    the link takes the classes the bench's own runbook link carries at `Deposition.tsx:1152`; the file's header
    comment stays. Extend `scripts/smoke.ts` with a measure of every target box on the takeover at 810 px portrait,
    and assert each is at least 44 px each way.
47. **`lib.sh`'s `REPO` keeps the line `cd` prints under a CDPATH.** Closes H11-09 (S3). Files:
    `scripts/host/lib.sh:6`. Size: small. The line becomes `CDPATH= cd -- "..." >/dev/null && pwd`. Extend
    `core/tests/test_host.py` with `CDPATH=.` exported, and assert `REPO` holds one absolute path.
48. **`test_workers.ALLOWED` holds no biorefineries row, and `test_boundaries.NEVER` covers five packages.** Closes
    H12-06 (S3). Files: `core/tests/test_workers.py:133-157`. Size: small. A `"biorefineries"` row names
    `workers/library_plants.py` and `workers/kept_references.py`, with `flowsheets/` skipped as the biosteam row skips
    it. The break it must catch is an `import biorefineries` planted in a service function such as
    `proforma.retired_entry_of`.
49. **The one test of the literature row runs at the kit's head.** Closes H12-11 (S3). Files:
    `core/tests/test_ready.py`. Size: small. One test migrates a database, takes `sci_rag` back one revision, and
    asserts the literature row fails with "pnpm db:migrate" in its words. The break it must catch is `at != head`
    dropped from `ready.py:206`.
50. **The kit catches `llm.kit_client`'s `ModelUnavailable` and reports it as an empty stage or a class name.** Closes
    H8-06 (S3), H8-08 (S3). Files: `core/openferment_core/llm.py` (`kit_client`),
    `core/openferment_core/literature/kit.py` (`search`, `answer`), `core/openferment_core/api.py:2134`. Size: medium.
    `KitLLM` keeps the words of each `ModelUnavailable` it raises for the request, `kit.search` names the deep layers
    whose call failed in `degradedStages`, and `kit.answer`, the function group 16 edits, puts the kept words in its
    `error` event. Extend `core/tests/test_literature_kit.py` with a deep search and an answer stream run with no key,
    and assert `degradedStages` names the graph and HyDE layers and the error names the missing key.
51. **The in-process `ask_postdoc` calls `postdoc_agent.ask` outside the turn keeping that `api._answer` holds.**
    Closes H9-11 (S3). Files: `core/openferment_core/api.py:502-547`, `core/openferment_core/mcp_server.py:417`. Size:
    medium. The keeping (`conversations.begin`, the tool-call hooks, `finish`) moves into one function that
    `api._answer` and the in-process `ask_postdoc` both call. Extend `core/tests/test_mcp.py` with an in-process
    `ask_postdoc` over a stand-in client, and assert a conversation, a turn and its tool-call rows are kept.
52. **`hydrateProjectState` returns on a failed load, and nothing calls it again in that page.** Closes H7-02 (S3).
    Files: `src/store.ts:1050`, `src/App.tsx:378`. Size: medium. The store runs `hydrateProjectState` again once the
    service answers after a failed load, which lays the queue over the rows and flushes it. Extend
    `scripts/check-state.ts` with a load that fails and then succeeds, and assert the queued readings reach the
    service in the same page.
53. **A scenario run states `rtol 0`, and its build carries last-digit state from a plant the worker built earlier.**
    Closes H2-02 (S3). Files: `core/openferment_core/workers/proforma_worker.py:197-198`,
    `core/openferment_core/proforma.py:808-809` and `:1521`, `docs/api/engines.md:616-618`,
    `docs/api/runs.md:229-231`. Size: medium. The scenario build is made free of what the worker built before, or
    `proforma.run` gains a stated precision and a replay tolerance, as a library run keeps ten digits
    (`engine/library.py:68-74`), with the two pages to match. Extend the replay test in `core/tests/test_runs_sim.py`
    that group 13 extends with a scenario run kept after a library run and replayed after a worker restart.
54. **`test_no_seed.py` matches the seed's export names and record ids.** Closes H12-05 (S3). Files:
    `core/tests/test_no_seed.py`. Size: medium. A scan of typed numbers beside science words across
    `core/openferment_core/` and `src/` joins it, with an allowance for what `CLAUDE.md:12` counts as software
    (versions, ports, tolerances, unit-conversion factors, file hashes, the library's own regression values). The
    break it must catch is a service module typing a titre, a yield, a composition and a price, and a `src/data/` file
    exporting a yield table by strain under a name outside `SEEDED_NAMES`.
55. **`simulator.status` answers the kept `_STATE`. It never reads the worker's process.** Closes H1-10 (S4). Files:
    `core/openferment_core/engine/simulator.py:43-44` and `:87`. Size: small. `status()` checks that the worker is
    alive once the state reads `ready`, and `call` sets the state back after a crash or a timeout. Extend
    `core/tests/test_engines.py` with a stand-in worker that dies, and assert `GET /api/engines` reads its worker as
    down.
56. **`kit.rest_app` mounts the kit's app whole, with four routes outside its key check.** Closes H10-03 (S4). Files:
    `core/openferment_core/literature/kit.py:848-849`. Size: small. A key check covers every route `rest_app` keeps,
    or the four routes (`/rag/health`, `/rag/v1/corpus-manifest`, `/rag/docs`, `/rag/openapi.json`) leave the mount.
    Extend the no-key test at `core/tests/test_literature_kit.py:235-242` to the four routes.
57. **`catalogues._entries` and `protocols.held` answer an empty list on `ProjectRequired`.** Closes H5-06 (S4).
    Files: `core/openferment_core/catalogues.py:585-590`, `core/openferment_core/protocols.py:291-296`,
    `core/tests/test_protocols.py:224`. Size: small. Both let `ProjectRequired` reach the 422 handler at
    `api.py:414-416`, and their docstrings and the assertion at `test_protocols.py:224` change with them; group 17
    reads through the same reader. Extend `core/tests/test_catalogues.py` with protparam, pureOS propose and Guild
    check asked with no project header, and assert a 422 in words.
58. **`ask_postdoc` and `get_artifact` take typed signatures, which the MCP SDK validates before the body runs.**
    Closes H9-15 (S4). Files: `core/openferment_core/mcp_server.py:405` and `:422`. Size: small. Both take their
    argument as sent, as the registry tools do through `_Raw`, and answer a missing or non-string one in words through
    `refusal()` or `artifact_refusal()`. Extend `core/tests/test_mcp.py` with each tool called with no argument and
    with a number, and assert a refusal in words as JSON.
59. **`report._save` rebuilds the whole retrieval report from the demo text and `render()`.** Closes H13-02 (S4).
    Files: `core/openferment_core/literature/report.py:195-202` and `:732-816`,
    `docs/reports/literature-retrieval.md`. Size: small. `render()` writes the two hand sections from fields the
    part's JSON keeps, or the hand text moves to a file the generator leaves alone. Extend
    `core/tests/test_literature_report.py` with a save over a report holding the hand sections, and assert they stay.
60. **The nightly dump test reads `nightly.sh`'s text.** Closes H11-07 (S4). Files: `core/tests/test_host.py:347-350`.
    Size: small. The test runs `nightly.sh` on `_dump_stand_ins`'s stand-ins with a stand-in `core/.venv/bin/python`,
    and asserts the `pg_dump` call comes before the extract call and a failed dump gives a non-zero exit. The break it
    must catch is the line `backup_database || status=$?` at `scripts/host/nightly.sh:33` commented out.
61. **The series case in `test_basis.py` uses an id the id clause already rejects.** Closes H12-13 (S4). Files:
    `core/tests/test_basis.py:203-212`, `core/tests/test_fermos.py`. Size: small. A series case with id `dep-b1/de-1`
    and fermOS's note joins `test_basis.py`, and a `test_fermos.py` fit on that id asserts the kept fit is `computed`.
    The break they must catch is the note clause of `basis.is_measurement` (`basis.py:202`) dropped, which labels a
    fermOS fit measured.
62. **Home's `stateOf` writes fixed words into its destination lines.** Closes H14-05 (S4), H14-06 (S4), H14-08 (S4).
    Files: `src/screens/Home.tsx` (`:244-256`, `:284-291`, `:366-379`). Size: small. `Counted` gains a gold count for
    the BioRepo line, the Postdoc line reads the health answer's `hasKey`, and the pureOS line names the trains pureOS
    builds and runs. Extend `scripts/walk.ts`, which opens Home on a keyless service, with a gold record kept, and
    assert each line follows its state.
63. **Words and records that drifted from the code they describe.** Closes H10-05 (S4), H13-06 (S4), H6-05 (S4), H5-07
    (S4), P-03 (S4), R1-01 (S4), R1-05 (S4), H7-09 (S4), H8-11 (S4). Files: `core/openferment_core/guard.py:22-24`,
    `.github/workflows/verify.yml:15`, `docs/decisions/ADR-001-postgresql.md:62`, `CLAUDE.md:66`,
    `docs/PROGRESS.md:483` and `:541`, `core/openferment_core/guild.py:395`, `core/openferment_core/practice.py:487`,
    `core/openferment_core/models.py:1425-1426`, `src/screens/Guild.tsx:627-628`, `src/lib/review.ts:224` and `:310`,
    `docs/reports/handoff-2026-11.md:82`, `src/screens/Settings.tsx` (the Storage row), `src/lib/durable.ts:6-8`,
    `core/openferment_core/catalogues.py:571` or the three texts that describe it. Size: small. Each is a phrase, a
    path, a number or a docstring: the guard's docstring names `.localhost`, verify.yml names `scripts/smoke.ts` and
    `scripts/walk.ts`, JSONB becomes `json` in ADR-001, CLAUDE.md and the departures row, the refusal words name the
    skill catalogue, the Guild strip names documents the project does not hold, the D8 row names `GET
    /api/biorepo/artifacts?tool=`, 838 becomes 837, the Storage row and the header of `durable.ts` say a reload ends a
    bench run, and a catalogue file's entry names its file beside a row's own source. `pnpm gen:api` follows the
    docstring at `models.py:1425-1426`, `core/tests/test_guidance.py` holds the CLAUDE.md line, and a test in
    `core/tests/test_catalogues.py` posts a row that carries its own source.
