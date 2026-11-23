# H5: project isolation

Commit 2047f5a, read cold. Keyless throughout (bh_env), test databases bh_h5_main and bh_h5_fresh on
127.0.0.1:5432, services on 8850 and 8851 with the offline collectors and a /rag test key
(`bh-h5-ragkey-not-a-secret`, a value chosen for the test). No file under core/, src/, scripts/ or
examples/ was touched; every script is under `scripts/` here.

## What I did

- **Filled project A (`bh-a`) with one of everything a person or an assistant can make without a model**
  (`scripts/fill.py`): four catalogue entries, a protocol, a deposition with a confirmed reading, a made
  train, a Live conversation, fits, overrides, a Guild lead with evidence and a requested check, a pasted
  document, a candidate written through the tool door and verified into a record, two kinetics runs (runs
  and artifacts), a comparison, a study runbook locked, an SFF library record, a proposal (a gated write),
  a study scenario on cornstover. Project B (`bh-b`) starts empty.
- **Every operation of docs/api/openapi.json from B** (`scripts/probe_ops.py`, generated from the
  document): A's ids in each path, query and body; then the header missing, empty, spaces, `BH-A`,
  `bh‑a` (U+2011), 200 characters, `../bh-a`, a tab, an unknown project, and the header naming B over
  `?project=bh-a`. 1,614 requests. A's rows were read whole before and after (19 reads and the audit):
  unchanged. Heavy and model routes were sent from B alone.
- **The tool door and both MCP servers** (`scripts/probe_tools.py`): every registry tool from B through
  `POST /api/tools/<name>`, the openferment server in its own process and through `--service`, plus
  `ask_postdoc` and `get_artifact`; every sci-rag tool; each server again with `--project` naming
  `bh-zzz`, `../bh-a` and `BH-A`. A unchanged; no answer carried A's words or A's ids.
- **The event stream** (`scripts/sse.py`): B's stream while A ran a kinetics run and a tool call; replays
  with `Last-Event-ID` 0 and one below A's first id, `?after=0`, `?after=-5`; the header over `?project=`.
- **/rag** with the test key: health, status, manifest, documents, a document of A's, query.
- **The concept graph**: rows a build would leave, written by hand into the test database
  (`scripts/graph_rows.sql`, no model), read through the sci-rag server and `/api/literature/stats` as B
  and as A (`scripts/graph_reads.py`).
- **Ids within a project**: kinds that share a table (`scripts/kind_collision.py`,
  `scripts/train_collision.py`); a locked runbook through `/api/state`.
- **A document two projects hold** (`scripts/shared_doc.py`) and **a search racing an ingestion**
  (`scripts/race.py`, `scripts/race_tool.py`).
- `scripts/run_all.sh` runs the lot from a fresh database (it was run once that way, on bh_h5_fresh, with
  the same results as the first pass).

## What held

- Every store call reads the project from the request; every `select` with an id names `project_id`
  (static grep of every store module, then the probe). B read, listed, changed and deleted none of A's rows
  through any of the 133 operations; B made rows under A's ids freely, each its own (ids are unique within a
  project, `(project_id, id)`), and A's stayed as they were.
- The middleware: a malformed id is a 422 in words, an unknown one a 404, before any route; the header
  wins over `?project=`; uvicorn strips spaces, so `"   "` is an empty header, which names none.
- The tool door and both MCP servers act in the project they are given; through `--service` the service's
  own words come back. The openferment server refuses an unknown or malformed project in words.
- SSE: B's stream and every replay carry B's events alone. /rag narrows every route to the project, and
  answers 422 in the kit's shape with no project.
- Graph reads: B lists no entity and no edge that only A's passages prove; a description stands only where
  every naming document is B's; a quote not in B's passage is withheld.
- B's export package holds nothing of A's.

## Findings

H5-01 (S1) B's searches return A's documents ingested during the search, through the HTTP route and the
tool door (race; 8 of 40 and 6 of 30). H5-02 (S1) a shared document reads in B with A's title, private url,
source and licence class. H5-03 (S2) `/api/state` writes replace a study scenario or a model's kept train
under the same id. H5-04 (S2) a locked runbook is deleted through `/api/state`. H5-05 (S3) forecast 500.
H5-06 (S3) no project named answers as an empty project. H5-07 (S4) stale "none ship with alpha 2.0".
H5-08 (S3) the sci-rag server answers an unknown project as an empty one.

## Left and noted

- Audit ids and event ids are single sequences across projects, so B can count A's activity from the gaps
  between its own ids (events.py says so of event ids). Not filed.
- Two `X-OpenFerment-Project` headers: the first wins, with no refusal. Not filed.
- Anything a model must answer (an answer's citations, `answer_question`, a graph build's alias matching
  across projects) is under needsLiveModel.
