# H9-11: an MCP ask in the server's own process leaves the project no turn

**Statement.** A question asked at `POST /api/ask` is kept as a conversation and a turn of the
project, its tool calls kept under the turn and its turn events said on the project's stream;
the same question asked through the `openferment` MCP server in its own process (no
`--service`, the way `.mcp.json` starts it) runs `postdoc_agent.ask` directly, and the project
keeps no conversation, no turn and no tool call of it, and its stream says nothing.

**Contract.**
- `docs/api/postdoc.md:3-4`: "Postdoc keeps each question as a turn of a conversation under the
  project, and says what every worker job, tool call, artifact and turn does as it happens".
- `docs/TOOLS.md:865`: the MCP server "adds `ask_postdoc` ... Postdoc's loop on a question"; at
  `docs/TOOLS.md:886-887` the server reaches the project "through a running service" (`ask_postdoc`
  as `POST <origin>/api/ask`, which keeps the turn) or "in its own process", where it "runs every
  call there", on the project's database. Nothing in either page says the second door keeps no turn.
- `CLAUDE.md:8` (R): "every claim, number and result stays inspectable back to its source, its
  calculation and its assumptions".

**Command.** From the repository root: `bash bughunt/repro/H9-11/run.sh`

It makes the database `bh_r_h9_11_mcpask` fresh, starts the service on 127.0.0.1:10051, makes the
project `h911`, reads the project's event stream for the whole run, asks one question through
the MCP server in its own process on the same database (an SDK stdio client named `h911bot/1`),
then the same question at `POST /api/ask`, and counts after each ask the project's conversations
(`GET /api/conversations`), its `turns` and `tool_calls` rows, and the `turn.*` events on
`GET /api/events`. Keyless: both asks decline for want of a key before any model call, and a
declined plan is an answer the service keeps (`docs/api/postdoc.md`, the status table).

**Expected.** After the MCP ask, one conversation and one turn, as after the REST ask, and turn
events on the stream.

**Observed (both runs).**

```
MCP ask -> conversations 0->0, turns 0->0, turn events 0; REST ask -> conversations 0->1, turns 0->1, turn events 5
```

The MCP answer carries no `conversationId` and no `turnId`; the REST answer carries both.

**Likely cause.** `core/openferment_core/mcp_server.py:415-417`: the in-process branch of
`ask_postdoc` calls `postdoc_agent.ask(question, ctx=tools.ToolContext(project=acting))` with no
`on_call` or `on_result`, and with no `conversations.begin`/`finish` around it. The keeping lives in
`core/openferment_core/api.py:502-547` (`_answer`: `_conversations.begin` at line 510, the
`on_call`/`on_result` hooks that write `tool_calls` and publish `tool.*` at 527-535, `finish` and
the `turn.*` events at 545-546), and `mcp_server` does not import `api`. The event stream is held
in memory in the service's process (`core/openferment_core/events.py:17-19`), so a server in its
own process could say nothing there even with the turn kept; the turn and its tool calls in the
tables are what a page reads on load.
