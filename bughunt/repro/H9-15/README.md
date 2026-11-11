# H9-15: ask_postdoc and get_artifact answer a missing or mistyped argument with isError and pydantic's text

**Statement.** Over the openferment MCP server, `ask_postdoc` with no `question` (or a `question` of 7 or null) and `get_artifact` with no `id` (or an `id` of 7 or null) answer `isError: true` with the text `Error executing tool <name>: 1 validation error for <name>Arguments ... For further information visit https://errors.pydantic.dev/2.13/v/...`, while the registry tool `literature_document` answers the same three inputs with a ToolResult whose `error` holds words and `isError` false.

**Contract.** `docs/TOOLS.md:896`:

> A tool's refusal is its ToolResult with `error` set, and `ask_postdoc`'s an `AnswerPlan` whose `declined` holds the words. A refusal the server writes itself (no project, a project its store lacks, an origin refused, a service that did not answer or refused the call, an artifact id of no artifact's shape) is `{"error": <words>}` alone for a tool and for `get_artifact`, and an `AnswerPlan` holding the question and `declined` for `ask_postdoc`, so a client reads every other key with a default. `is_error` stays false, and no `structured_content` is sent.

The same file says each tool answers one text block holding its result as JSON (`docs/TOOLS.md:896`, "Over MCP each tool answers one text block holding its result as JSON"). The module's own comment at `core/openferment_core/mcp_server.py:408` says the ask declines in words, as over HTTP, and `_Raw`'s docstring at `core/openferment_core/mcp_server.py:105` reads "Every argument, as sent: the registry validates, never this layer."

**Command.** From the repository root:

    bash bughunt/repro/H9-15/run.sh

It makes the test database `bh_r_h9_15_mcp` fresh, makes the project `h9-15` in process, starts the MCP server in its own process (`python -m openferment_core.mcp_server --project h9-15`) over raw JSON-RPC lines on stdio, sends ten `tools/call` requests and drops the database. No service, no port, no key and no model call: the server's environment holds an empty `ANTHROPIC_API_KEY` and a dead loopback proxy, and every probe is refused before a tool body runs.

**Expected.** `ask_postdoc` with its question missing or of another type answers an `AnswerPlan` whose `declined` says so in words, and `get_artifact` with its id missing or of another type answers `{"error": <words>}` (an id of 7 or null is an artifact id of no artifact's shape), each as JSON in one text block with `isError` false, as `literature_document` answers `{}`, `{"document": 7}` and `{"document": null}` and as `get_artifact` answers the string id `"zz"`.

**Observed (run1.log and run2.log, the same in both).**

- Controls: `literature_document` answered a ToolResult with `error` in words and `isError` false in 3 of 3 cases ("literature_document refused its input: document: Field required", "a number was typed into document ...", "document: Input should be a valid string"); `get_artifact` with `"zz"` answered `{"error": "no readable artifact 'zz': an artifact's id is sixteen hex digits ..."}` with `isError` false.
- Probes: 6 of 6 answered `isError: true` with a text that is no JSON, for example `Error executing tool ask_postdoc: 1 validation error for ask_postdocArguments \n question \n Field required [type=missing, input_value={}, input_type=dict] \n For further information visit https://errors.pydantic.dev/2.13/v/missing` and `Error executing tool get_artifact: 1 validation error for get_artifactArguments \n id \n Input should be a valid string [type=string_type, input_value=7, input_type=int] ...`.
- Both runs end `RESULT: DEFECT`.

**Likely cause** (high confidence). `ask_postdoc` and `get_artifact` are registered with `@server.tool` and typed signatures, `question: Annotated[str, Field(...)]` at `core/openferment_core/mcp_server.py:405` and `id: Annotated[str, Field(...)]` at `core/openferment_core/mcp_server.py:422`, so the SDK builds an argument model from each signature and validates the call's arguments before the function runs. A `ValidationError` there becomes a `ToolError("Error executing tool <name>: <pydantic text>")` (`core/.venv/lib/python3.13/site-packages/mcp/server/mcpserver/tools/base.py:156`, mcp 2.3.0), which the SDK answers as `isError: true`. The registry tools reach `tools.run` with every argument as sent because `_register` swaps their argument model for `_Raw` (`core/openferment_core/mcp_server.py:104-110` and `:367`), and the registry's own validation turns the same inputs into a ToolResult whose `error` holds words. The refusal paths written for the two tools (`refusal()` and `artifact_refusal(id)` at `core/openferment_core/mcp_server.py:410-412` and `:426`) are never reached for these inputs. A small fix gives both tools a `_Raw`-style argument model (or `question: Any`, `id: Any` checked in the body) and answers a missing or non-string argument in words.

**Severity.** S4, wording and shape at the edge of two tools: a well-formed call answers as the page says, and a malformed one receives a library's validation text and URL with `is_error` true.
