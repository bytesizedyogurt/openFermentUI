# R1-03 (with R2-01): the concept graph's dry run prices a whole build as one request

**Statement.** `pnpm lit:graph --project <id> --dry-run` adds the characters of every batch's prompt into one
count and prices that count with `llm.cost_usd` as one request, so once a build's prompts together pass 100,000
tokens Haiku 5.5's long-prompt pair (0.50 and 2.50 USD a million) prices every batch; each batch is its own request
of at most about 10,700 kit tokens, priced at 0.10 and 0.50, so the dry run's input and its most come out five times
what the build's requests cost, and the records' 0.2199 and 2.3239 USD for F.5's 92 batches come to 0.0440 and 0.4648
USD priced request by request.

**Contract.**

- `core/openferment_core/llm.py:340-342`: "A model whose price rises with the prompt: past the threshold (in prompt
  tokens, cache reads and writes included) the whole request pays the second pair." A request's own prompt sets
  its tier; every answer is charged one response at a time (`llm.py:921`, `:1067`, `usage_of`) and held one request
  at a time (`llm.py:888`, `_reserve`).
- `core/openferment_core/literature_live.py:11-13`: the dry run prints "what their input and the most a build could
  cost come to on the route's first model (each batch's whole answer, the figure the day's cap holds against)".
- `docs/api/intake.md:69`: "what the input and the most a build could cost come to on the route's first model".
- The build sends one request a batch: `core/openferment_core/literature/graph.py:15` "one model call on the client
  the caller hands in", `graph.py:172`, and the kit's step `extractor.py:313`
  (`payload = await llm.generate_json(prompt, max_tokens=8192)`).
- Recorded: `docs/reports/literature-retrieval.md:115-117` "their input comes to 0.2199 USD on `claude-haiku-5-5`,
  and the most the build could cost, each batch's whole answer counted, to 2.3239 USD"; `docs/PROGRESS.md:3372`
  "0.2199 USD of input on `claude-haiku-5-5` and at most 2.3239 USD"; `docs/PROGRESS.md:609` (Open debts) "at most
  2.3239 USD on `claude-haiku-5-5` by the dry run".

**Command.** From the repository root: `bash bughunt/repro/R1-03/run.sh` (keyless, no model call, no service, about
ten seconds). It makes the fresh database `bh_r_r1_03_run`, keeps one project with 12 documents of 10 placeholder
passages each (4,000 characters a passage, the kit's cut, so each batch is the largest a batch can be), runs the
real `python -m openferment_core.literature_live graph --project r103 --dry-run` whole and with `--limit 40`, runs
`graph.build` over the same passages on a client that records each request and answers an empty graph, prices each
request with `llm.usage_of` and the dry run's own hold arithmetic, drives `graph_command`'s dry-run branch over F.5's
recorded measure (92 prompts summing to 1,758,899 characters, its two reads stood in for), greps the records, and
drops the database.

**Expected.** The dry run's `inputUsd` and `mostUsd` are the sums of each batch request's own price: 0.012816 and
0.074772 USD for the fresh database's 12 batches, and 0.0440 and 0.4648 USD for F.5's 92; a batch costs the same in
a 4-batch build and a 12-batch one.

**Observed (both runs).** The build sends 12 requests of 42,705 characters each (10,676 kit tokens; 21,353 at the
guard's two characters a token), the very prompts the dry run measured. The dry run prints `inputUsd` 0.064058 and
`mostUsd` 0.373881, 5.00 times the per-request sums; with `--limit 40` (4 batches, 42,705 kit tokens) a batch's
input is 0.001068 USD, and over all 12 batches 0.005338 USD, the same prompt priced at 0.10 USD a million and then
0.50. F.5's measure through `graph_command` prints `inputUsd` 0.219862 and `mostUsd` 2.32393, the records' figures
to the digit; priced request by request they come to 0.0440 and 0.4648 USD. Three lines of `docs/` at 2047f5a carry
2.3239 USD.

**Likely cause.** `core/openferment_core/literature_live.py:106` sums the prompts (`chars = sum(len(p) for p in
prompts)`) and `:110-112` price the sum as one request: `llm.cost_usd(model, round(chars / 4), 0)` and
`llm.cost_usd(model, chars // llm.CHARS_PER_TOKEN_ESTIMATE + len(prompts), answer * len(prompts))`;
`llm.cost_usd` (`llm.py:499`) reads its tier from `prices_for(model, input_tokens + ...)` (`llm.py:491-496`), and
`LONG_PROMPT_PRICES` (`llm.py:343-345`) moves every token of that one count to the second pair past 100,000. A
per-prompt sum (`sum(llm.cost_usd(model, round(len(p) / 4), 0) for p in prompts)` and its hold twin) fixes both
figures. `core/tests/test_literature_live.py:97` asserts `0 < inputUsd < mostUsd` alone, over a one-passage store
far under the threshold, so the tier passes the suite unseen.

**The records.** `docs/reports/literature-retrieval.md:116-117` and `docs/PROGRESS.md:3372` give 0.2199 USD as the
build's input: that figure is wrong as stated (0.0440). The 2.3239 USD is given as "the most the build could cost,
each batch's whole answer counted" and, in the Open debts row at `docs/PROGRESS.md:609`, as "at most 2.3239 USD ...
by the dry run": by the dry run's own definition (one whole answer a batch, each batch's hold) the most is 0.4648
USD, so the row carries a ceiling five times the measure it names. Read as a bare inequality over 92 requests,
2.3239 lies above 0.4648, and the row's number misstates the dry run's measure fivefold.
