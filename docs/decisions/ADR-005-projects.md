# ADR-005 — Projects replace programs

- **Status**: accepted (requirement: the owner named projects as the organizing object)
- **Date**: 2026-10-30

## Context

At `alpha-1.0` three programs (casein A–O, PHA P, yeast ethanol Q) partition the seed by thread
letter, with one archive switch (`showArchived`) threaded through every list, request and tool
context (`programs.ts`, `programs.py`, `programOf`, `HiddenByArchive`, `ArchivedBanner`,
`includeArchived`, `OPENFERMENT_INCLUDE_ARCHIVED`).

## Decision

A **Project** scopes documents, records, flowsheets, runs, artifacts, runbooks, depositions,
conversations and Guild entries. Literature is stored only when a project selects a document for
ingestion. Every table carries `project_id`; every API route is project-scoped; the MCP server
takes a project. The program machinery is deleted with the programs. Accounts are designed for and
stubbed (`project_members`), with no login: the loopback bind and `guard.py` stay the access
control.

## Implementation (stage 2, 2026-10-30)

- **How a request names its project.** The `X-OpenFerment-Project` header, or `?project=` where a
  header cannot be sent (the event stream of §7.3). One middleware in `api.py` checks the id's
  shape and that the database holds it (a 422 or a 404 in words, a 503 when the database does not
  answer) and sets it for the request; it runs after `guard.py`, so a refused request never
  reaches the database. A store reads the project from `projects.current()`, and a store call in
  a request that names none is a 422 that says which header to send. `/api/health` and
  `/api/projects` act in no project, so a page that remembers a project the database no longer
  holds can still recover.
- **Commands and the MCP server** name the project once, in `OPENFERMENT_PROJECT`; the MCP server
  reads it, and the database address, from the environment or `core/.env` by those two names
  alone, so how the key is read is unchanged (§11.1).
- **The client** remembers the last-open project in `localStorage` (`durable.ts`: read
  synchronously, so the first call after a load already names it) and names it on every call
  (`lib/project.ts`). With none open and exactly one held, that one opens. Switching projects
  reloads the page, so nothing of the last project stays on screen. A project is made in the
  reviewer's name, from the top bar or from the notice every screen shows while none is open.
- **Ids** are made from the name (`Corn stover ethanol` gives `corn-stover-ethanol`, a second
  `corn-stover-ethanol-2`) or given; a taken id is a 409. Making a project is audited under it.
- **Tests** run in one project, `test-project`, written in each test's rolled-back transaction;
  every `TestClient` a test makes names it, as the browser does.

## Implementation (alpha 2.2 D.0: the MCP server through a running service)

- **`--service <origin>`.** The MCP server acts through a running service when started with
  `python -m openferment_core.mcp_server --project <id> --service <origin>`: every registry call is
  `POST <origin>/api/tools/<name>` with the arguments as the client sent them, the project in
  `X-OpenFerment-Project` and the client's declared name in `X-OpenFerment-Assistant`;
  `ask_postdoc` is `POST <origin>/api/ask` and `get_artifact` `GET
  <origin>/api/biorepo/artifacts/<id>`. A builder handed a project id and a service's address, in
  a worktree with no `core/.env`, reaches the project that service holds, whatever database it runs
  on. The server then opens no database and reads `core/.env` for `OPENFERMENT_PROJECT` alone,
  when `--project` names none.
- **Loopback alone.** The origin is `http://` or `https://`, the host `127.0.0.1`, `[::1]` or
  `localhost`, an explicit port, and nothing after it (`mcp_server.service_origin`); anything else
  is refused in words when the server starts, a value holding a user or a password in words that
  never repeat it, and every call answers with those words. `localhost` is sent to `127.0.0.1`,
  the address the service binds, so no resolver is asked where it is. The server sends through
  `httpx.Client(trust_env=False, follow_redirects=False)`, so no proxy carries a loopback call and
  a redirect the service answers is its words, followed nowhere; `get_artifact` sends an id of an
  artifact's shape alone (sixteen hex digits), so a dot segment steers the read nowhere. No
  listener and no host is added, and `guard.py` is unchanged: it holds these POSTs as it holds any.
- **A project the store does not hold.** In its own process the server checks the project against
  its database at the first call and answers every call with words naming the project while the
  database lacks it; through a service, the service's own 404 words come back as the call's error.

## Consequences

- Home opens on the person's projects; module screens become views inside a project (ADR-009).
- The `includeArchived` parameter disappears from requests and tool contexts.

## Revisit condition

Accounts and multi-user access (a later build).

## Evidence

- Execution prompt §4.5; development plan §1 ("a conversation with Postdoc inside a chosen
  project").
