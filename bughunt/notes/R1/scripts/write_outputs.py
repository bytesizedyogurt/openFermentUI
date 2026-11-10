"""R1: writes candidates.json and coverage.jsonl from the lists below (the hunt's return value)."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
S = "bughunt/notes/R1/scripts"

candidates = [
    {
        "id": "R1-03",
        "title": "The graph dry run prices all 92 batches as one prompt at Haiku's long-prompt rate: 0.2199 and 2.3239 USD are five times the build's per-call cost",
        "severity": "S3",
        "kind": "Wrong number",
        "area": "pnpm lit:graph --dry-run (core/openferment_core/literature_live.py); docs/PROGRESS.md stage F log; docs/reports/literature-retrieval.md",
        "statement": "The dry run passes the characters of every batch prompt summed into one llm.cost_usd call, so the 439,725 kit tokens cross claude-haiku-5-5's 100,000-token long-prompt threshold and are priced at 0.50/2.50 USD per million; each batch is a separate call of about 4,780 kit tokens, which the service charges at 0.10/0.50; the recorded 0.2199 USD of input and 2.3239 USD at most come out at 0.0440 and 0.4648 priced call by call.",
        "contract": "docs/reports/literature-retrieval.md:116-117 \"their input comes to 0.2199 USD on `claude-haiku-5-5`, and the most the build could cost, each batch's whole answer counted, to 2.3239 USD\"; docs/PROGRESS.md:3372 \"0.2199 USD of input on `claude-haiku-5-5` and at most 2.3239 USD, each batch's whole answer counted\"; docs/api/intake.md:69 \"what the input and the most a build could cost come to on the route's first model\"; core/openferment_core/llm.py:340-342 \"past the threshold (in prompt tokens, cache reads and writes included) the whole request pays the second pair\" (a request's own prompt)",
        "reproCommand": f"source bughunt/lib/env.sh; cd core && bh_env OPENFERMENT_DATABASE_URL= .venv/bin/python ../{S}/dryrun_price.py",
        "expected": "The dry run prices each batch as the call it will be (cost_usd per prompt, summed): about 0.0440 USD of input and at most about 0.4648 USD for 1,758,899 characters over 92 batches of at most ten passages each.",
        "observed": "Driven through graph_command's own dry-run branch with 92 prompts totalling 1,758,899 characters (database read stubbed), it prints inputUsd 0.219862 and mostUsd 2.32393, the report's figures to the last digit; priced one call at a time the same prompts come to 0.0440 and 0.4648 USD, 5.0 times less each; the largest batch is 4,780 kit tokens against a 100,000-token threshold.",
        "cause": "core/openferment_core/literature_live.py:110-111 call llm.cost_usd(model, round(chars / 4), 0) and llm.cost_usd(model, chars // 2 + len(prompts), answer * len(prompts)) on the sum over all prompts; llm.cost_usd (llm.py:509, prices_for at llm.py:491-496) applies LONG_PROMPT_PRICES when that one input exceeds 100,000 tokens. Every real call is charged on its own usage (llm.py:533). core/tests/test_literature_live.py:97 asserts only 0 < inputUsd < mostUsd, so the tier passes unseen. The figure also stands in docs/PROGRESS.md:609 (Known debts).",
        "confidence": "high",
        "fixSize": "small",
        "evidence": "dryrun_price.py output: dry run says {'batches': 92, 'promptCharacters': 1758899, 'kitTokens': 439725, 'model': 'claude-haiku-5-5', 'inputUsd': 0.219862, 'mostUsd': 2.32393}; per call: input 0.0440 USD, most 0.4648 USD; ratio 5.0 and 5.0. The 92 batches match the per-document passage counts of docs/reports/live-questions-2026-11.md's table at ten a batch cut at each document's end (19+6+1+1+3+3+4+4+4+4+4+3+3+4+4+4+4+3+3+3+4+4 = 92), so no batch nears 100,000 tokens. llm.PRICES claude-haiku-5-5 (0.10, 0.50), LONG_PROMPT_PRICES (100_000, (0.50, 2.50))."
    },
    {
        "id": "R1-01",
        "title": "A Departures row names GET /api/artifacts, a route the service does not serve",
        "severity": "S4",
        "kind": "Drift",
        "area": "docs/PROGRESS.md, Departures (alpha 2.2 D8, C.6)",
        "statement": "PROGRESS.md's row on retiring /api/proforma/benchmark and /api/proforma/reference/{id} says the reference screen reads the project's kept reference runs at `GET /api/artifacts`; neither openapi.json nor api.py has that path at C.6 or at the head, and the screen reads GET /api/biorepo/artifacts?tool=.",
        "contract": "docs/PROGRESS.md:483 \"the reference screen reads the library plant's runs (`GET /api/runs?engine=biosteam`) and the project's kept reference runs (`GET /api/artifacts`)\"",
        "reproCommand": f"python3 {S}/routes.py   (prints every METHOD /api/... the record names that openapi.json and api.py lack; line 483 is the one phantom, the rest are concrete values of parametrized routes)",
        "expected": "The row names the route the screen reads: GET /api/biorepo/artifacts (src/screens/ProformaReference.tsx:20, src/lib/artifacts.ts:67).",
        "observed": "routes.py: \"483 GET /api/artifacts no such route\"; openapi.json paths at f5405f8 and 2047f5a hold /api/biorepo/artifacts and no /api/artifacts.",
        "cause": "Written so at C.6 (git log -S'(`GET /api/artifacts`)' names f5405f8) and never held to the schema.",
        "confidence": "high",
        "fixSize": "small",
        "evidence": "python3 bughunt/notes/R1/scripts/routes.py; python3 -c over docs/api/openapi.json listing paths containing 'artifact' at f5405f8 and 2047f5a: ['/api/biorepo/artifacts', ...] only."
    },
    {
        "id": "R1-02",
        "title": "A Departures row still says no store holds a protocol, after E.12a made the protocols table and routes",
        "severity": "S4",
        "kind": "Drift",
        "area": "docs/PROGRESS.md, Departures (alpha 2.2 D7, C.5)",
        "statement": "The bench's readings-alone row gives as its reason that no store holds a protocol in this build; since E.12a (37addaf) migration 0010 makes a protocols table and the service serves /api/protocols with its versions, ADR-016 gained an implementation note saying so, and the row was left as C.5 wrote it.",
        "contract": "docs/PROGRESS.md:467 \"No store holds a protocol in this build, and D7's walk deposits a reading at the bench on step 5's locked runbook\"; docs/PROGRESS.md:113-114 stage H \"wrote this file's Resume, Known debts ... to the branch's end\"; ADR-017 \"A project keeps its protocols\"",
        "reproCommand": f"bash {S}/stale_rows.sh",
        "expected": "The row says the readings-alone mode stands beside a project's protocols (ADR-017), as the Decisions row for ADR-016 and ADR-016's own note do.",
        "observed": "Row 467 says no store holds a protocol; the tree at 2047f5a holds core/openferment_core/db/alembic/versions/0010_protocols.py (create_table('protocols')) and the paths /api/protocols, /api/protocols/{protocol_id}, /api/protocols/{protocol_id}/versions; ADR-016:51 has \"Implementation note (alpha 2.2 E.12a)\".",
        "cause": "E.12a updated the Decisions row and ADR-016 and left the Departures row's reason (ADR-016:17 and ADR-006:225 carry the same sentence, the ADR with a later note).",
        "confidence": "high",
        "fixSize": "small",
        "evidence": "stale_rows.sh output, first block."
    },
    {
        "id": "R1-04",
        "title": "Two Departures rows disagree on whether the browser keeps the lessons finished",
        "severity": "S4",
        "kind": "Inconsistency",
        "area": "docs/PROGRESS.md, Departures (§5.5, stage 2 and alpha 2.2 E.12)",
        "statement": "The stage 2 row says the browser keeps three preferences, the third the lessons finished here; the E.12 row in the same table says the Durable snapshot keeps no lesson, and src/lib/durable.ts holds learnProgress as a legacy field nothing reads and the next save drops.",
        "contract": "docs/PROGRESS.md:543 \"and three preferences, who is deciding, who is acting in Guild, and the lessons finished here\"; docs/PROGRESS.md:502 \"The Durable snapshot keeps no lesson ... the modules slice, `learnProgress` and `completeLesson` leave the store\"",
        "reproCommand": f"bash {S}/stale_rows.sh",
        "expected": "One account: the snapshot keeps two preferences (reviewerName, guild.actingId) and the unacknowledged writes, with no lesson.",
        "observed": "Row 543 names three preferences with the lessons; row 502 and src/lib/durable.ts:142-148 (\"LEGACY, left where it lies ... nothing reads this, and the next save leaves it out\") say none; git grep finds learnProgress in src/ only as that type.",
        "cause": "E.12 (c18c0e7) added row 502 and left row 543 as stage 2 wrote it.",
        "confidence": "high",
        "fixSize": "small",
        "evidence": "stale_rows.sh output, second block."
    },
    {
        "id": "R1-05",
        "title": "The handoff report says the agent builder read docs/TOOLS.md's 838 lines; the file at CORE holds 837",
        "severity": "S4",
        "kind": "Wrong number",
        "area": "docs/reports/handoff-2026-11.md, Round 1, the agent builder",
        "statement": "The report counts the TOOLS.md the agent builder read at CORE=6f85338 as 838 lines; that file has 837 lines (84,382 bytes, ending in a newline).",
        "contract": "docs/reports/handoff-2026-11.md:82 \"`docs/TOOLS.md` whole (838 lines)\"",
        "reproCommand": "git show 6f85338:docs/TOOLS.md | wc -lc; git show 6f85338:docs/TOOLS.md | tail -c 2 | od -c",
        "expected": "837 lines",
        "observed": "wc -l 837, 84382 bytes; the last byte is a newline, so there is no unterminated 838th line.",
        "cause": "Likely a count of split('\\n') pieces, which gives one more than the lines for a file ending in a newline.",
        "confidence": "high",
        "fixSize": "small",
        "evidence": "git show 6f85338:docs/TOOLS.md | wc -lc -> 837 84382."
    },
]

held = [
    "Resume 1: claude/alpha-2-2-base is at 2047f5a and cut from main's 112eb8b (git merge-base origin/main 2047f5a); origin/main is 112eb8b; the origin holds no tag (git ls-remote origin 'refs/tags/*' empty), alpha-1.0 d19224f and alpha-2.1 fa1b744 exist locally as Blockers row 4 says; a local tag alpha-2.2 now points at 2047f5a",
    "Resume 2: pnpm install, uv sync, db:up (docker compose up -d --wait db), db:migrate and db:reset exist in package.json with the commands named; the service loads core/.env with override=False (api.py:178); core/.env.example holds five routing lines, all commented (MODEL, FALLBACK_MODEL, EFFORT, INDEX_MODEL, ROUTES); this session's environment pins the three model settings to claude-haiku-5-5 and OPENFERMENT_EFFORT to medium, OPENFERMENT_API_KEY set and ANTHROPIC_API_KEY unset (env, values of keys not printed)",
    "Resume 2 and ADR-008 Impl. 17: llm.ROUTES gives plan, explain, extract Opus then Sonnet at high, index Haiku at low, judge Opus then Sonnet at max; plan.ROOM is 64,000 at xhigh and 128,000 at max, MAX_TOKENS 32,000 below (run: llm.routes() keyless with and without the plain settings; judge and index's effort keep their defaults under the plain settings)",
    "Resume 5 and Blockers 1: every live command's flags exist (evaluation.py --live --suite --tag --judge --only, judge, summary --rows; literature_live graph --project --by --dry-run, report --project --by --judge --render --from; ready --probe; prove --live); model-routing-2026-11.md line 491 is the alpha 2.2 'To finish it', and its five steps and OPENFERMENT_MAX JSON match Resume and Blockers word for word",
    "Resume 5: OPENFERMENT_DATA_DIR moves both caches (intake.DATA_DIR and sff.library_root, sff.py:163-170); the session copy /tmp/.../scratchpad/f/data holds models, sff-library and literature; `python -m openferment_core.engine.sff fetch` with fetch alone fetches (sff.main), and pnpm geneos:fetch fetches both models",
    "Resume 4 and Current stage: src/data/types.ts and src/engine/geneos/enumeration.ts are gone (e90deeb, 8281f5e); /catalogues is routed (App.tsx:178); E.1 to E.14 are one commit each; H.0 is five commits (744e32e, a024dfc, bde5a76, 3cd2919, 9b6e5c7); the landing's nine cherry-picks carry the messages PROGRESS.md:3304-3307 names",
    "Resume 6 and Blockers 3: nightly.sh runs backup_database first (nightly.sh:33), keg's pg_dump -h 127.0.0.1 --format=custom openferment into ~/openferment-backups/openferment-<date>.dump via .part, folder 700, newest 7 kept (lib.sh:177-201); test_host.py's three backup tests exist and pass (test_host.py 52 + test_guidance.py 6 = 58 passed)",
    "Owner questions 11 to 13: basis.basis_provenance implements the default (assumed on any assumption or estimate, else measured on any measurement, else the weakest); flowsheet_import takes a reference file's id alone; has_key is unchanged since before stage G (git diff 58b345e~1..2047f5a scripts/host/lib.sh touches no has_key line) and greps an unquoted ANTHROPIC_API_KEY=sk-ant- line",
    "Environment facts re-measured: Node v22.22.0, pnpm 10.33.0, uv 0.11.32, Python 3.13.17 with 3.12 present, 4 CPUs, 15 GB, PostgreSQL 16.15 (Ubuntu noble), postgresql-16-pgvector 0.6.0, Docker client present, core/.venv Python 3.13.17",
    "Spend (alpha 2.2): every row's parts sum to its totals: 5 Nov 1+31+94+14 = 140 calls, 0.000004+5.377950+4.376768+4.684600 = 14.439322; 8 Nov 75+92+41 = 208, 6.920110+11.903559+6.460811 = 25.284480; F 348 and 39.723802; alpha 2.2 349 and 39.723806 with A's 0.000004; the probe's 0.000004 is 18 in at 0.10 and 4 out at 0.50 per million on claude-haiku-5-5 (llm.PRICES); holds expire as said (spend.RESERVATION_TTL_S, _reserve deletes expired holds); check_tools_26521_a78452 is gone from the server and sci_rag_test holds no spend table (read-only SELECT on information_schema); a proof reads its own spend table (prove.py:1430)",
    "Spend (alpha 2.1): B's parts 4.53+1.80+4.54+5.01+1.60 = 17.48, plus the 0.17 named, 17.65",
    "Decisions: every ADR-000 to ADR-018 file exists with the status the table gives (ADR-012 open, the rest accepted); ADR-008 holds Implementations 13 to 19 and ADR-002 Implementation F",
    "Departures, alpha 2.2 rows checked against the code: the fixed dispatch and the four recaptured hashes (test_engine_pins.py:143-167); study comparison 1 and 2 (comparisons.py:56-57); kinetics worker None, workerStatus none, train thingsAre (GET /api/engines on a fresh service); a kinetics parameter with no default has value and origin null and sourceRule naming assumption (GET /api/engines/kinetics/parameters?thing=batch_v1: 9 of 18); growth_forecast at the HTTP door with no by is a 422 in words; contract.CONTRACT_RUN 'engine run 1'; ENGINE_NAME_MAX 40, CONFIGURATION_MAX 80; the train's SFF refusal words (proforma_worker.py:1218) and replay_precision (0, 0); 'is set twice' at pureOS's door; module_stores.PARTIAL holds no runbooks line; project_state.deposition_refusal and amend_depositions; kept_references.py with replay_reference and replay_benchmark; import-url refuses a user or password in words (422); GET /api/state carries depositedBy; GET /api/depositions/readings answers",
    "Departures: every backticked path the checked sections name exists at 2047f5a or is named as deleted (paths.py); every pnpm script named in the present tense exists (pnpm_cmds.py: only the retired data:push, demo:fixtures, eval:o, ids, rag:eval are absent, each named as retired); every METHOD /api/... named exists except row 483 (routes.py)",
    "Log, stage B and H counts: TOOLS.md has 48 tool sections from B.5 to C.7 and 50 at CORE (B.2's '48 tools still'), 58 at the head with the sci-rag section's 8; test_engines_sim.py 3 tests at e375ede; the 20 validate_claims tests removed and 11 validate_plan tests added at 3cd2919 as H.0 says; check:state's check calls 86 at 448adbb, 90 at a024dfc (+4) and 95 at bde5a76 (+5), and 95 checks print at the head (96 lines with the summary); check:guild 146 checks at the head; check:plan holds 9 provenance classes in one order",
    "Log, stage H: Known debts hold 33 paid, 11 open and 18 left rows (H.2); CLAUDE.md has 149 lines (H.6); 39 test files import standins.py (H.6); README's first section has five lines on alpha 2.2 and Read further lists docs/BASE.md first (H.4)",
    "Log, the alpha 2.2 entries name 53 test files and 34 more test modules by name; every one exists at 2047f5a",
    "Log and live-questions report: the three warm-up runs give the same ids at the head on a fresh service (cornstover bfda026530692adc, cellulosic_ethanol_v0 dilute acid IB e7efa2505b4633de, hot water IB 784c94d9bd67d20e; warmup_ids.sh), cornstover 19.3 s with the worker's cold start against the report's 22.1 s",
    "live-questions-2026-11.md, 5 November table: 22 rows sum to 814 passages, 457 kept, 54 refused, 5.3780 USD, 803 s, median 24 s, most 151 s (PMC6053494), 13 Opus and 9 Sonnet; the refusal kinds sum 31 + 21 + 2 = 54; the carbon-source drops 121 + 13 = 134",
    "literature-retrieval.md and .json (F.5): recomputed from the kept run /tmp/.../scratchpad/f/data/literature/ethanol-20261108T081732Z.json (litrun.py): its commit 311990d and time 08:17:27; 130 questions from 457 of 457 candidates in 130 groups over 20 of 22 documents; the field counts sum to 130; every hit@10, MRR and nDCG cell; the three missed lists equal the records (108, 108, 129); keyword_only returned 0 passages for 102, 1 for 22, 4 for 1 and 10 for 5; interactive and vector_only 10 for all; the JSON's project part equals the run's public part and its demo part equals 112eb8b's whole payload; the kit rule's hit@10 equals a same-document count (70 and 70), so H8-07's one stray rank moves no hit@10",
    "literature-retrieval.md: 1,758,899 characters over 4 is 439,725 kit tokens; 92 batches follow from the per-document passage counts at ten a batch; tiktoken is absent from core/.venv, so the kit's estimate is four characters a token",
    "model-routing-2026-11.md, alpha 2.2 part: recomputed from its own per-question rows (routing_tables.py): every code and judge mean of the four tables to the third digit (haiku citations 0.749 against 0.748 from rounded rows), tool calls mean/median, claims kept/dropped and for numbers, the dropped-kind sums, stops, the cost means, medians and sums, 4.9626 and 9.0614 for haiku, 23.5 and 2.62 as cost ratios, and all twelve rows of the rule table (differences and above/below/level counts); 46 = 14+14+14+4 judgements; questions 4, 7, 8 and 14 follow 3, 6, 5 and 5 in evaluate.py",
    "handoff-2026-11.md: no file under core/openferment_core, core/tests, core/pyproject.toml, src or scripts changes 6f85338..37e6bd0; the mirror is seven files, its pyproject registers mirror = openferment_engine_mirror.engine:ENGINE with no licence and no dependency, its README ten lines, its tests 30 (collected); the mirror is unchanged since 37e6bd0; record_reader.py names mcp>=2.3,<3, clientInfo example-agent 0.1, the skill example-agent.0.1-a-skill, pops VIRTUAL_ENV, takes --root; its README six lines; TOOLS.md at CORE 84,382 bytes and 50 tools; question 13's expectation names the registry's engines (evaluate.engines_here); E.16's five points stand at the head (auditIds on a write, GET /api/audit filtered by action and target with no null fields, the VIRTUAL_ENV advice and the client pointer in TOOLS.md)",
    "Blockers 2: alpha 2.1's lib.sh looks for pg_isready on PATH (git show 112eb8b:scripts/host/lib.sh:111), which a keg-only postgresql@17 leaves off it; the runbook's steps 0 to 7 carry the names Blockers and Resume give them",
    "Live owed: pnpm lit:report alone runs the demo and --project the project's lanes with --judge; prove.py's step 6 asks the routed models with --live",
]

suspected = [
    {"title": "Departures row 536 still says search_passages' seam answers 'no literature index exists yet'",
     "tried": "git grep finds no such words at 2047f5a; tools/passages.py: search runs Sci RAG Kit's retrieval. The row's own Why says stage 3 fills the seam, so a reader learns it was filled; left as a historical stage 1 departure; R1-02's reason carries no such word."},
    {"title": "Departures row 546 says nothing reads core/data/biorepo.json",
     "tried": "Hunt P found import_alpha1 reads it by default; the same row says db:import-alpha1 carries it, so the words 'nothing reads it' mean the service. Not reported."},
]

needs_live = [
    "The graph build's real per-call spend against the dry run's estimate (R1-03): pnpm lit:graph --project ethanol --by <name> spends on the index route; its tally would show the per-call charges",
    "The second judge (Sonnet alone at max), the opus-max-room measure and opus-max's other ten questions that model-routing-2026-11.md's rule and decision rest on",
    "F.3 (the fourteen on the Postdoc screen), F.4 (pnpm prove --live) and F.5's model lanes (graph, HyDE, the judge's grading and the answer lane)",
    "pnpm ready --probe's row and the account's limit date",
    "The judge's disagreement with itself (model-routing-2026-11.md's floor table): it needs the first-pass judgements kept in openferment_dev's eval_runs",
]

unexamined = [
    {"item": "Known debts (docs/PROGRESS.md:561-643)", "reason": "the brief leaves it to task P (bughunt/notes/P); only its row counts were held to H.2's 33/11/18"},
    {"item": "Last green runs (docs/PROGRESS.md:252-381)", "reason": "the brief leaves it to the baseline"},
    {"item": "Spend tables against the databases (openferment_dev, openferment_dev_alpha21)", "reason": "the brief gives no leave to copy those databases, and the hard rules forbid connecting to them; the rows' sums and the code's keeping were checked instead"},
    {"item": "core/.env's budgets (150 and 8 USD) and its five routing lines commented out", "reason": "the hard rules forbid reading core/.env; core/.env.example was read"},
    {"item": "Log counts at historical commits that need a build there (check:plan 1629 fields across 218 types at E.11 to E.14, test_engines.py's 22 and 82 tests at e375ede and ed33c02, smoke's 13 and 20 screens, prove's check counts)", "reason": "each needs a worktree with its own venv and node_modules at that commit; test def counts (17 and 64 before parametrize) were read and the head's counts measured"},
    {"item": "ShellCheck 0.11.0 clean over the host scripts (H.6)", "reason": "shellcheck is not installed in this container"},
    {"item": "CI run ids and timings (run 325, 41865693107) and the tag push's HTTP 403", "reason": "GitHub's API is not reached from this hunt, and a tag push is outside the hunt's rules"},
    {"item": "The Log's stages C, D and E in full (docs/PROGRESS.md:1495-3064)", "reason": "read in part and sampled: every backticked identifier, path, route, test file and test name checked mechanically (idents.py, paths.py, routes.py), and the claims named under held; the narrative of each step beyond those was not re-derived"},
    {"item": "model-routing-2026-11.md and live-questions-2026-11.md, alpha 2.1 parts", "reason": "alpha 2.2 changed words alone there (git diff 112eb8b..2047f5a); the changed sentences were read"},
]

out = {"candidates": candidates, "suspected": suspected, "needsLiveModel": needs_live, "held": held, "unexamined": unexamined}
(HERE / "candidates.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

cov = [
    ("file", "docs/PROGRESS.md", "executed", ["R1-01", "R1-02", "R1-03", "R1-04"], "Resume, Current stage, both Spend tables, Decisions, every Departures row (alpha 2.2 rows read whole, older rows read), Blockers, Owner questions, Environment facts, Live owed, the alpha 2.2 Log (sampled in full by scripts, H.0 and H read whole); Known debts and Last green runs left to P and the baseline"),
    ("file", "docs/reports/literature-retrieval.md", "executed", ["R1-03"], "recomputed from the kept run (litrun.py); dry run's figures reproduced through the code (dryrun_price.py)"),
    ("file", "docs/reports/literature-retrieval.json", "executed", [], "project part equals the kept run's public part; demo part equals 112eb8b's payload"),
    ("file", "docs/reports/model-routing-2026-11.md", "executed", [], "alpha 2.2 part recomputed from its per-question rows (routing_tables.py); To finish it held to Resume and Blockers"),
    ("file", "docs/reports/live-questions-2026-11.md", "executed", [], "warm-up run ids reproduced on a fresh service; extraction table summed"),
    ("file", "docs/reports/handoff-2026-11.md", "executed", ["R1-05"], "git diff over CORE, file counts, test collection, TOOLS.md at CORE"),
    ("file", "core/openferment_core/literature_live.py", "executed", ["R1-03"], "dry-run branch driven with stubbed database read"),
    ("file", "core/openferment_core/llm.py", "executed", ["R1-03"], "ROUTES, routes(), PRICES, LONG_PROMPT_PRICES, cost_usd"),
    ("file", "core/openferment_core/spend.py", "read", [], "reservations, expiry, state()"),
    ("file", "core/openferment_core/engine/sff.py", "read", [], "main's fetch, library_root"),
    ("file", "core/openferment_core/postdoc/evaluate.py", "read", [], "ETHANOL_QUESTIONS follows, engines_here, JUDGE_TOKENS"),
    ("file", "core/openferment_core/evaluation.py", "read", [], "the eval CLI's flags"),
    ("file", "core/openferment_core/literature/graph.py", "read", ["R1-03"], "ANSWER_TOKENS, prompts, batch size"),
    ("file", "core/openferment_core/postdoc/plan.py", "read", [], "MAX_TOKENS and ROOM"),
    ("file", "core/openferment_core/basis.py", "read", [], "basis_provenance (owner question 11)"),
    ("file", "core/openferment_core/workers/proforma_worker.py", "read", [], "the train's SFF refusal, replay ops"),
    ("file", "core/openferment_core/pureos/train_spec.py", "read", [], "replay_precision, set twice"),
    ("file", "core/openferment_core/studies/comparisons.py", "read", [], "versions 1 and 2, _row_of"),
    ("file", "core/openferment_core/module_stores.py", "read", [], "PARTIAL"),
    ("file", "core/openferment_core/project_state.py", "read", [], "deposition_refusal, amend_depositions"),
    ("file", "core/openferment_core/engine/contract.py", "read", [], "CONTRACT_RUN"),
    ("file", "core/openferment_core/engine/registry.py", "read", [], "ENGINE_NAME_MAX"),
    ("file", "core/openferment_core/models.py", "read", [], "ENGINE_NAME_MAX, CONFIGURATION_MAX"),
    ("file", "core/openferment_core/api.py", "read", [], "load_dotenv override=False, routes"),
    ("file", "core/tests/test_engine_pins.py", "read", [], "fixed dispatch and pins"),
    ("file", "core/tests/test_literature_live.py", "read", ["R1-03"], "the dry run's test holds 0 < inputUsd < mostUsd alone"),
    ("file", "core/tests/test_phase3_review.py", "read", [], "H.0's removed spend-lock test and would_pass"),
    ("file", "core/tests/test_spend.py", "read", [], "H.0's rewrite"),
    ("file", "core/tests/test_validate.py", "read", [], "20 tests out, 11 in at 3cd2919"),
    ("file", "core/tests/test_host.py", "executed", [], "52 passed with test_guidance's 6"),
    ("file", "core/tests/test_guidance.py", "executed", [], "6 passed"),
    ("file", "src/lib/durable.ts", "read", ["R1-04"], "DurableSnapshot fields"),
    ("file", "src/screens/ProformaReference.tsx", "read", ["R1-01"], "the routes it reads"),
    ("file", "scripts/check-state.ts", "executed", [], "95 checks"),
    ("file", "scripts/check-guild.ts", "executed", [], "146 checks"),
    ("file", "scripts/check-plan.mjs", "executed", [], "9 classes"),
    ("file", "scripts/host/lib.sh", "read", [], "backup_database, has_key"),
    ("file", "scripts/host/nightly.sh", "read", [], "backup first"),
    ("file", "scripts/host/install.sh", "read", [], "against alpha 2.1's"),
    ("file", "scripts/walk.ts", "read", [], "the engine step from the Runs screen"),
    ("file", "scripts/prove.py", "read", [], "spend read, CONFORM_TIMEOUT_S"),
    ("file", "examples/agents/record-reader/record_reader.py", "read", [], "handoff claims"),
    ("file", "examples/agents/record-reader/README.md", "read", [], "six lines"),
    ("file", "examples/engines/openferment-engine-mirror/pyproject.toml", "read", [], "entry point, no licence or dependency"),
    ("file", "examples/engines/openferment-engine-mirror/README.md", "read", [], "ten lines"),
    ("file", "examples/engines/openferment-engine-mirror/tests/test_worker.py", "executed", [], "collected, 30 with test_engine"),
    ("file", "examples/engines/openferment-engine-mirror/tests/test_engine.py", "executed", [], "collected"),
    ("file", "docs/decisions/ADR-016-bench-readings-alone.md", "read", ["R1-02"], "E.12a note"),
    ("file", "docs/runbooks/live-host-install.md", "read", [], "step names and step 7"),
    ("file", "docs/TOOLS.md", "read", [], "client recipe, tool counts across commits"),
    ("file", "README.md", "read", [], "H.4's five lines"),
    ("file", "core/.env.example", "read", [], "routing lines"),
    ("file", "CLAUDE.md", "read", [], "149 lines (H.6)"),
    ("operation", "POST /api/projects", "executed", [], ""),
    ("operation", "GET /api/engines", "executed", [], "kinetics worker none, train thingsAre"),
    ("operation", "GET /api/engines/{name}/parameters", "executed", [], "a parameter with no default"),
    ("operation", "POST /api/engines/{name}/run", "executed", [], "three warm-up runs, ids as the report"),
    ("operation", "POST /api/tools/{name}", "executed", [], "growth_forecast with no by; catalogue_write with by"),
    ("operation", "POST /api/flowsheets/import-url", "executed", [], "user and password refused"),
    ("operation", "GET /api/state", "executed", [], "depositedBy"),
    ("operation", "GET /api/depositions/readings", "executed", [], ""),
    ("operation", "GET /api/audit", "executed", [], "action and target filters, null fields left out"),
    ("tool", "growth_forecast", "executed", [], "422 in words with no caller"),
    ("tool", "catalogue_write", "executed", [], "auditIds names the row"),
    ("engine", "biosteam", "executed", [], "cornstover and cellulosic_ethanol_v0 ids reproduced"),
    ("engine", "kinetics", "executed", [], "listing and parameters"),
    ("engine", "train", "executed", [], "listing"),
]
with (HERE / "coverage.jsonl").open("w", encoding="utf-8") as f:
    for kind, item, method, findings, note in cov:
        row = {"kind": kind, "item": item, "method": method, "findings": findings}
        if note:
            row["note"] = note
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
print(len(candidates), "candidates;", len(cov), "coverage lines")
