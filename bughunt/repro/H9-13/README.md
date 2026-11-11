# H9-13: a lone surrogate escape answers a bare 500 at the REST tool door

**Statement.** A JSON body holding the escape `"\ud800"` in a string that a tool echoes back (search_records'
`query`, `field` or `organism`, search_passages' `query`, yield_ceiling's `product`, selling_price's or
run_flowsheet's `scenarioId`) answers `500 Internal Server Error` with no words, since the tool's result carries
the lone surrogate and FastAPI cannot encode the answer as UTF-8.

**Contract it breaks.**
- `core/openferment_core/api.py:208`, the service's description in the OpenAPI document: "A refusal is a status
  with its reason in `detail`, in words."
- `core/openferment_core/api.py:2924-2925`, the tool door's own docstring: "A refusal is a result with `error`
  set; an unknown tool is a 404."
- `core/openferment_core/tools/__init__.py:502-503`, `tools.run`: "Every refusal is a result with `error` set;
  nothing here raises." `tools.run` keeps its word and returns a ToolResult; the raise comes after it, while the
  door serializes that result.

**Command.** From the repository root: `bash bughunt/repro/H9-13/run.sh`
(a fresh database `bh_r_h9_13_svc`, the head's service on 127.0.0.1:10410, keyless, no model call; it sends
seven calls with `"ab"` and the same seven with `"a\ud800b"`, then reads the service log).

**Expected.** Each call with `"a\ud800b"` answers as its `"ab"` twin does: a 200 ToolResult whose `error` says in
words why nothing matched or ran (the text holds a character UTF-8 cannot carry), or the text with the
surrogate dropped, as `tools.caller_name` already drops one from a caller's name.

**Observed (both runs).** All seven `"ab"` calls answer 200 with a ToolResult (search_records and search_passages
echo the text in `summary`; yield_ceiling, selling_price and run_flowsheet refuse naming it in `error`). All seven
`"a\ud800b"` calls answer `500` with the body `Internal Server Error`, and the service log reads
`PydanticSerializationError: Error serializing to JSON: UnicodeEncodeError: 'utf-8' codec can't encode character
'\ud800' in position 1: surrogates not allowed`. See `run1.log` and `run2.log`.

**Likely cause.** Starlette's `json.loads` accepts a lone surrogate escape, and nothing on the door's path drops
or refuses one in the body: `tools.run` (`core/openferment_core/tools/__init__.py:500`) runs the tool, the tool
echoes the text into its summary or refusal, and `tools_run` returns that result
(`core/openferment_core/api.py:2960`), where FastAPI's response serialization fails on it. Only the caller's
name is cleaned of surrogates (`tools.caller_name`, `core/openferment_core/tools/__init__.py:170-181`).

**Severity.** S4: a wordless refusal of text no well-formed client sends; nothing runs, nothing is kept.
