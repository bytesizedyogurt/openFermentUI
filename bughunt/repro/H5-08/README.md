# H5-08: the sci-rag MCP server serves a project the database lacks as an empty project

**Statement.** Started with `--project` naming a project the database does not hold (`bh-zzz`), an id of no
project's shape (`../bh-a`) or an upper-case id (`BH-A`, beside a held `bh-a`), the sci-rag server answers
every call as it answers a held project with no document (`documents: 0`, `sources: {}`, "No such document")
and its graph tools tell the client "The project <id> holds no passage yet: its documents enter on Intake",
while the openferment server refuses the same ids in words naming the database and the project.

**Contract.**

- `CLAUDE.md:98`: "the `openferment` server over the registry and the `sci-rag` server (...), both in
  `.mcp.json`, each acting in the project `--project` names and refusing in words without one".
- `docs/TOOLS.md:888` (the openferment server): "With no project, or one its store does not hold, the server
  connects and answers every call with words saying which, and nothing is read or made".
- `docs/TOOLS.md:907` (the sci-rag server): "With no project, every call is refused in words naming the two
  ways to name one; (...) A graph tool asked of a project that holds no passage is refused in words saying its
  documents enter on Intake".
- `core/openferment_core/projects/__init__.py:8-10`: the service "refuses one that names a project it does not
  hold", so the Intake the graph tools' words point to refuses each of these three ids.

The sci-rag server's own lines (TOOLS.md:907) promise a refusal for no project alone, and that line holds.
The defect is the inconsistency between the two servers that CLAUDE.md:98 describes
as one pair: the openferment server says a missing project is missing, and the sci-rag server, for the same
id on the same database, says the project exists, is empty, and takes documents on Intake.

**Command** (from the repository root): `bash bughunt/repro/H5-08/run.sh`

It makes a fresh test database `bh_r_h5_08_mcp` holding one project, `bh-a` (no document), and a scratch
worktree of 2047f5a whose `core/` holds no `.env`, then starts each server over stdio from that worktree for
five `--project` values: none, `bh-a`, `bh-zzz`, `../bh-a`, `BH-A`. The openferment server is asked
`literature_sources`; the sci-rag server `corpus_stats`, `list_sources`, `get_document`, `get_citations`,
`search_entities` and `get_entity_relationships`. Every one reads the store alone: no key, no model call, no
network. The database and the worktree are removed at the end. About 50 s.

**Expected.** For `bh-zzz`, `../bh-a` and `BH-A` every sci-rag call is refused in words saying the database
holds no such project, as the openferment server answers for the same ids.

**Observed** (run1.log, run2.log, identical outcomes):

- openferment server, each id: `{"error": "The database bh_r_h5_08_mcp on 127.0.0.1:5432 holds no project
  named 'bh-zzz'. Start this server with --project naming a project it holds, ..."}`.
- sci-rag server, each id: all six answers equal the held empty `bh-a`'s answers with the id swapped (6 of 6):
  `corpus_stats` `documents: 0`, `list_sources` `{"sources": {}, ...}`, `get_document` and `get_citations`
  "No such document", and both graph tools "The project ../bh-a holds no passage yet: its documents enter on
  Intake, and `pnpm lit:graph --project ../bh-a --by <name>` then builds the concept graph over their passages."
- Control: with no project the sci-rag server refuses every call in words ("This Sci RAG Kit server acts in no
  project ..."), so the refusal path exists and works for that case.

**Likely cause.** `core/openferment_core/literature_mcp.py:68-70`: `_named()` asks only that some project be
named (`projects.current_or_none() is None`), and `act_in` (`literature_mcp.py:128-134`) sets whatever
`--project` gives, with no `projects.valid_id` and no `projects.held` check of the kind the openferment server
makes in `_Store.refusal` (`core/openferment_core/mcp_server.py:329-343`). The kit's `ProjectService` then
reads an empty scope, and `core/openferment_core/literature/graph.py:77-80` states that `NO_PASSAGES` covers
"a store that holds no project of the id", so the graph tools answer a missing project with the words for an
empty one. Confidence high; the fix is small (one `held` check in `_named`, cached once held).

**Severity.** S3: an edge case with a workaround (start the server with the project's exact id). Nothing of
another project is read or shown; a client that mistypes the id is told the project is empty and pointed to an
Intake that refuses it.
