# H5-01: B's literature searches return documents A ingests while the search runs

**Statement.** Once project B holds one document whose kit source is project A's (a text A collected first, which B then collects), a search B runs while A ingests a new document under that source can return A's new document, its words and its passage id, because B's exclusion list is read before the retrieval runs.

**Contract.**
- `docs/decisions/ADR-002-sci-rag-kit.md:82-85`: "the sources of the project's documents go to the kit as its `sources` allowlist and the other documents of those sources as `exclude_document_ids`, so a shared document is visible to each project that linked it and to no other."
- `core/openferment_core/literature/kit.py:15-16` (the module's own contract): "Every read a project makes is narrowed to its linked documents".
- `CLAUDE.md:56`: "every route beside health and the projects list acts in one project".

**Command** (from the repository root): `bash bughunt/repro/H5-01/run.sh`

It makes a fresh database `bh_r_h5_01_race`, starts a keyless service on 127.0.0.1:10200 and makes projects `bh-a` and `bh-b`. A pastes a seed text and B pastes the same text, so the kit stores it once under `project:bh-a:paste` and B links it. Then A pastes up to 60 private notes, one at a time, while B calls `GET /api/literature/search` in a loop. Each hit B gets on a document B does not hold and A does hold is counted. At the end it stops the service, drops the database and removes the service's data copy.

**Expected.** Every hit B's search returns is a passage of a document B holds. None of A's private notes appears, during A's ingestion or after it.

**Observed.** In both runs, B received A's private note 0 (its full text and passage id `p0`) within the first paste. The document is held by A and absent from B's `GET /api/literature/documents` (run1.log, run2.log). A search from B after A stopped returns none of A's notes, so the leak lives in the window while A ingests. The hunt saw the same through `POST /api/tools/search_passages` (6 to 8 of 40 notes, each with a passage id B could cite).

**Likely cause** (high confidence).
- `core/openferment_core/literature/kit.py:353-372` (`visible`): the exclusion list is the documents of B's sources that B does not hold, read at that moment.
- `core/openferment_core/literature/kit.py:405-411` (`_narrowed`): it hands the kit that list with the sources allowlist.
- `core/openferment_core/literature/kit.py:429-437` (`retrieve`) and `kit.py:453-454` (`answer_stream`): the kit's retrieval runs afterwards, in statements of its own. A document A commits under the shared source in between passes both of the kit's conditions (`sci_rag/retrieve/types.py:88-91`: `source IN allowlist`, `id NOT IN exclusions`).

`cause_check.py` makes the interleaving deterministic, in process (cause_check.log). It reads B's scope, has A paste one note, then retrieves with that scope, and A's note comes back. A scope read after the paste excludes it. Either of two narrowings closes the window: one built from the documents B holds (for example `Document.id IN held`), or one that names the excluded documents by a condition the retrieval evaluates itself.

**Severity.** S1: a cross-project read. B receives A's private text and a passage id B can cite. It needs two projects sharing one document and A ingesting under that document's source while B searches. A background collect in A beside a Postdoc turn in B is enough.
