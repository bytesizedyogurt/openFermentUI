# H9-14: a NUL in an id answers with the driver's error, its SQL and its parameters

**Statement.** An id holding a NUL character (`"a\u0000b"`) at `engine_report`, `flowsheet_read`
and the sci-rag server's `get_document` answers with asyncpg's `DBAPIError`, carrying the SQL
statement the store ran and its bound parameters (the project's id and the id sent), where an id
of nothing at the same doors is refused in the platform's words.

**Contract.**
- `docs/TOOLS.md:30-31`: "the whole of a large output travels in `data`, which no model reads, and
  a refusal is `error`, in words."
- `docs/TOOLS.md:907` (the sci-rag server): "a document the project does not hold and a database
  that does not answer are said in words as well."
- `core/openferment_core/tools/__init__.py:501-503` (cited by the hunt): "Every refusal is a
  result with `error` set; nothing here raises." The answer holds to this line: `error` is set and
  nothing raises. The break is in the words `error` holds, which the two `docs/TOOLS.md` lines
  promise.

**Command.** From the repository's root: `bash bughunt/repro/H9-14/run.sh`. It makes the database
`bh_r_h9_14_svc` fresh, starts the head's service keyless on `127.0.0.1:9221` with the model API
pointed at a dead loopback port, makes the project `h914`, asks `engine_report` and
`flowsheet_read` at `POST /api/tools/<name>` once with an id of nothing and once with
`"a\u0000b"`, asks `get_document` the same two ways on `python -m openferment_core.literature_mcp
--project h914` over stdio (`scirag_get_document.py`), then stops the service, drops the database
and removes its work directory. About 9 s.

**Expected.** The NUL id is refused in words as the id of nothing is: `engine_report refused: the
project holds no run ...`, `flowsheet_read refused: the project holds no flowsheet ...`, `No such
document: ...`, with no driver message, SQL text or bound parameters.

**Observed** (both runs, `run1.log` and `run2.log`, `RESULT: DEFECT`):

```
[200] engine_report refused: the project holds no run no-such-run
[200] engine_report failed: DBAPIError: (sqlalchemy.dialects.postgresql.asyncpg.Error) invalid byte sequence for encoding "UTF8": 0x00 [SQL: SELECT openferment.runs.body  FROM openferment.runs  WHERE openferment.runs.project_id = $1::VARCHAR AND openferment.runs.id = $2::VARCHAR] [parameters: ('h914', 'a\x00b')] (Background on this error at: https://sqlalche.me/e/21/dbapi)
[200] flowsheet_read refused: the project holds no flowsheet no-such-record (flowsheet_read with no record lists them)
[200] flowsheet_read failed: DBAPIError: ... [SQL: SELECT openferment.flowsheets.body ...] [parameters: ('h914', 'a\x00b')] ...
CASE unknown isError=True Error executing tool get_document: No such document: no-such-document
CASE nul isError=True Error executing tool get_document: The kit's service failed: DBAPIError: ... [SQL: SELECT openferment.documents_link.project_id, ... FROM openferment.documents_link WHERE ...] [parameters: ('h914', 'a\x00b')] ...
```

**Likely cause** (high confidence). No door checks an id for a NUL before it reaches the query;
PostgreSQL's text type holds no NUL, so asyncpg raises on the bound parameter, and each door's
catch-all turns the exception's own string into the answer:
- `core/openferment_core/tools/__init__.py:551-558`: `except Exception as e:  # a defect or an
  outage, said in words to the caller` ... `ToolResult(error=f"{name} failed: {type(e).__name__}: {e}")`,
  reached from `engine/runs.py:316-317` (`runs.get`, `db.run(_get(projects.current(), run_id))`)
  for `engine_report`, and from the flowsheet store's read for `flowsheet_read`.
- `core/openferment_core/literature_mcp.py:78`: `ToolError(f"The kit's service failed:
  {type(e).__name__}: {e}")`, reached from `literature/kit.py:414-416` (`_held`, the
  `documents_link` lookup ahead of the kit's `get_document`).

A small fix: the id fields refuse a NUL (and other control characters) at the input model, or the
store's lookups treat an id holding one as an id of nothing, so the existing "holds no ..." words
answer.

**Severity.** S4: the call fails either way and nothing is kept or changed; what leaks is the
store's table and column names, the statement and the caller's own project id and input, which an
outside assistant or Postdoc's model reads as the tool's words.
