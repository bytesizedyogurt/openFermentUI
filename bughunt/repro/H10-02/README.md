# H10-02: a NUL character in an id, a filter or a text field answers a bare 500

**Statement.** A request whose path id, query filter or body text holds U+0000 reaches PostgreSQL,
which refuses the byte (asyncpg's `CharacterNotInRepertoireError`, "invalid byte sequence for encoding
"UTF8": 0x00"), and the service answers 500 with the bare body `Internal Server Error` at 20 /api doors
and a 500 naming `DBAPIError` at 2 /rag doors, while `GET /api/studies/runbooks/{id}`,
`/api/biorepo/artifacts/{id}` and `/api/catalogues/{kind}/{id}` answer the same id with a 404 in words.

## The contract it breaks

- `core/openferment_core/api.py:208` (the OpenAPI document's `info.description`, so also
  `docs/api/openapi.json`): "A refusal is a status with its reason in `detail`, in words."
  (The candidate named line 207; the sentence sits on line 208 at 2047f5a.)
- `CLAUDE.md:87`: "a refusal is a 422 in words."
- `docs/api/openapi.json`, `GET /api/runs/{run_id}`, response 404: "The project holds no run of that
  id, in words."

## Command

```
bash bughunt/repro/H10-02/run.sh
```

It makes a fresh database `bh_r_h10_02_svc`, starts the service keyless on 127.0.0.1:9960 (the /rag
mount given a throwaway local key in the service's environment, so its doors are reached at all),
makes project `r1`, and sends `probe.py`'s requests, each naming `r1`: five controls (the three doors
that already answer the NUL id `a\x00b`, and a plain missing id at `/api/runs/{id}` and
`/api/projects/{id}`), 20 /api requests carrying `a\x00b` in a path id, a query filter or a body
field, and 2 /rag requests. It then counts `CharacterNotInRepertoireError` in the service's log,
reads the projects the refused POSTs named, prints the contract lines, stops the service and drops
the database.

## Expected

An id the project does not hold answers a 404 in words, and a filter or a text field the service
will not take answers a 422 in words, at every door, as the five controls already answer (each a 404
with a `detail` in words).

## Observed (run1.log, run2.log)

- The five controls: 404 with a `detail` in words, for example
  `{"detail":"the project holds no runbook a\\x00b"}` and `{"detail":"the project holds no run no-such-run"}`.
- 20 of 20 /api doors answer 500 with the bare body `Internal Server Error`: `GET /api/projects/{id}`,
  `/api/runs/{id}`, `/api/flowsheets/{id}`, `/api/flowsheets/{id}/file`, `/api/protocols/{id}`,
  `/api/conversations/{id}`, `/api/conversations/{id}/turns/t/calls`, `/api/studies/scenarios/{id}`,
  `/api/studies/comparisons/{id}`; `GET /api/audit?who=`, `?action=`, `?target=`, `/api/runs?engine=`,
  `/api/biorepo/artifacts?tool=`, `/api/proposals?state=`; `POST /api/projects` with the NUL in `name`,
  `by` or `description`; `POST /api/studies/scenarios/{id}/run`; `POST /api/practice/record` with a
  NUL `sessionId`.
- 2 of 2 /rag doors (`GET /rag/v1/documents/{id}`, `?search=`) answer the kit's problem+json 500,
  title "Internal server error", detail "DBAPIError (see server logs, request_id=...)".
- The service log names `asyncpg.exceptions.CharacterNotInRepertoireError: invalid byte sequence for
  encoding "UTF8": 0x00` 22 times, once a 500.
- Nothing is left behind: after the probe `GET /api/projects/r1` answers 200 and the three projects
  the refused POSTs named answer 404. No 500 body carries a trace, a path or SQL.
- RESULT: DEFECT on both runs; the two logs agree line for line apart from the kit's request ids.

## Likely cause

- `core/openferment_core/api.py:424-426`: the service maps `OperationalError`, `InterfaceError` and
  `ConnectionRefusedError` to a 503 in words and nothing else from the database; the `DBAPIError`
  (asyncpg's `CharacterNotInRepertoireError`, a data error) PostgreSQL raises for 0x00 in a text
  parameter falls through to Starlette's generic 500.
- No request model, path parameter or query parameter refuses U+0000 before the store call, so the
  byte reaches the lookup key, the filter column or `projects.name`. The three doors that answer in
  words find their id in Python over rows already read (for example
  `core/openferment_core/studies/runbooks.py:152-155`, `_held` over the project's state), so no NUL
  reaches a text parameter there.
- The kit's /rag routes pass the same byte to their own SQL and answer through the kit's own 500
  handler.

Severity S3: an edge case a client meets only by sending U+0000; the store stays whole and the
workaround is to send no NUL.
