# H9: Postdoc and the tool door

Commit 2047f5a, keyless, zero spend. Databases bh_h9_* only (all dropped), ports 8890-8896,
every model call sent to a loopback stand-in (`scripts/standin_model_api.py`) that records each
request and answers an error. Nothing under core/, src/, scripts/ or examples/ was changed.
Sixteen candidates (H9-01 to H9-16) in `candidates.json`; evidence files in `evidence/`.

## The key override (owner question 10)

`scripts/key_override_run.sh PORT STANDIN` starts the stand-in, then the service with
`ANTHROPIC_BASE_URL` at it (the SDK reads it: anthropic 1.0.0 `_client.py:211`; llm.make_client
passes no base_url; the kit's own Anthropic client is replaced by `llm.kit_client`), an env key
that is a sentinel of its own and `OPENFERMENT_RAG_KEY`. It pastes a document and sends
`X-OpenFerment-Key: BUGHUNT-SENTINEL-<hex>` on ten routes (`scripts/key_sentinel.py`), reading
`/api/events` the whole time. Then it greps the service log, every response, the stream, a
pg_dump of the database, dist/ and the stand-in's record.

Held: the sentinel appears only in the stand-in's record (13 of 14 requests), one key_override
audit row a request. Broken: `POST /api/literature/answer` ran on the env key (H9-01), since
`kit.answer` starts a plain thread. Run twice from fresh databases, same result.

## The tool door, REST and MCP

`scripts/fuzz_rest.py` called all 48 tools at `POST /api/tools/{name}` with base, empty, extra,
missing and wrongly typed arguments, empty and 100 kB strings, NUL, a lone surrogate, negative,
zero, 400-digit integers, raw NaN/Infinity, unknown ids (4278 calls). `scripts/fuzz_mcp.py`
sends raw JSON-RPC lines to the openferment server in its own process (2017 calls) and to the
sci-rag server (193 calls). Held: refusals in words for nearly every case. Broken: a 400-digit
integer in a quantity (H9-12), a lone surrogate (H9-13), a NUL in an id (H9-14), ask_postdoc and
get_artifact with bad arguments (H9-15). `scripts/edge_inputs.sh` reproduces H9-12 to H9-14.

## Gated writes and the audit

`scripts/gated_audit.py` sends every gated pair of `gates.GATES` through REST with `?by=`, REST
with `X-OpenFerment-Assistant` and the MCP server in its own process, then reads each answer's
`auditIds` at `GET /api/audit`. Held for every gate but spend: who, agent, `detail.via` (http,
mcp, none for a person) and no effort for an outside assistant. The spend gate never proposes
(H9-02, `scripts/spend_gate.sh`), and its two tests stub the wrong exception (H9-03).

Twin rule: `runbooks_write lock` on `rb-same` by `?by=Alice%20Person`, then by `?by=Bob%20Other`,
then with `X-OpenFerment-Assistant: other/1`; the second and third are refused "already proposed
in this ask" (H9-16; `scripts/twin_rule.sh`, and `scripts/mcp_ask_turn.sh` for H9-11).

## Budgets

`scripts/spend_boundaries.py` (in process, bh_h9_spend): at the cap held, a cent over refused,
twenty concurrent 0.10 holds against 1.00 give ten; the UTC boundary lets the next day reach 1.80
of 1.00 (H9-09); NaN and Infinity caps are taken (H9-08). `scripts/ask_budget.py` drives
`postdoc_agent.ask` with a stand-in converse charging each turn its whole room: 0.91 USD on the
default 0.75 cap, two calls at 0, a crash at inf/nan (H9-05, H9-08). A spent daily cap ends an
ask in words with no restart (held).

## Routing table

`scripts/routes_invalid.sh` runs one service per OPENFERMENT_ROUTES value (malformed JSON,
unknown family, unknown model, unknown provider, effort outside the enum, empty plan models,
empty extract models). The ask and extract routes answer 500 for each table that cannot route
(H9-06); an unknown model declines in words. `ready --offline --no-workers` says Ready, exit 0,
for each (H9-07). No request reached the stand-in from a table that cannot route.
`scripts/plan_route_three.py`: a third plan model is never asked (H9-10).

## Conversations, events, MCP ask

Another project's conversation and turn ids read as 404 in words; an ask in pk2 naming pk's ids
begins a conversation in pk2 and leaves pk's alone; `/api/events?project=` sends that project's
events alone. MCP ask: with the service on 8890 over bh_h9_main, `ask_postdoc` over stdio (SDK
client "askbot/1") left `GET /api/conversations` at 0, and `POST /api/ask` then made it 1 (H9-11).

## Claims and numbers

`scripts/numbers_in_claims.py` holds eight claims quoting one passage to `validate_plan`: the
prompt's own bad example "Ethanol titre roughly doubled under anaerobic conditions" is kept, with
"halved", "quadrupled", "Table IV", "phase III", "x10", "pH7", "pH-4" (H9-04).

## Left

The offline evaluation run (needs the BioSTEAM worker), live judge paths, and valid worker runs
of the engine, geneOS, fermOS and pureOS tools. `scripts/served_id_price.py` shows a call served
under an id outside `llm.PRICES` is charged 0; whether the API serves such ids needs a live call.
