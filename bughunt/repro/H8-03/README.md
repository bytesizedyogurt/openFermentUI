# H8-03: an upload named with %00 answers 500 and leaves a kit document no project holds

**Statement.** `POST /api/intake/upload` of a file named `report%00.md` answers HTTP 500 after the kit
has committed the document; the uploading project holds nothing, and the next project to upload the
same bytes links a document whose `source` names the first project and whose `sourceRef` is the
server's removed temporary file.

**Contract.** `docs/api/intake.md:52-56`: "Each answers HTTP 200 with a `CollectOutcome` ... or `failed`
with the `reason` in words ... A failure is an answer the Intake board renders: the route raises no 5xx
for a document it could not collect." The module says the same at `core/openferment_core/intake.py:8`:
"A failure is a result, never an exception: the Intake board renders it." For an upload, the document
points back to how it came (`core/openferment_core/intake.py:73-74`, `sourceRef` set to
`upload:<name>`; `core/openferment_core/literature/kit.py:597-598`).

**Command.** From the repository root: `bash bughunt/repro/H8-03/run.sh`. It makes the test database
`bh_r_h8_03_svc`, starts the head's service keyless on the first free port in 9430-9439, makes the
projects `h803a` and `h803b`, uploads one Markdown note to `h803a` as `report%00.md` and the same bytes
to `h803b` as `report.md`, reads both projects' documents and the kit's tables, prints the service
log's error, then stops the service and drops the database.

**Expected.** HTTP 200 with a `CollectOutcome` for `h803a` (status `failed` with the reason in words, or
the document stored under a name the database can keep), and no kit document that no project links.

**Observed** (`run1.log`, `run2.log`, the same both times):

- `h803a`'s upload answers HTTP 500 `Internal Server Error`; the service log holds asyncpg's
  `invalid byte sequence for encoding "UTF8": 0x00` on
  `UPDATE documents SET source_ref=$1` with the parameter `'upload:report\x00.md'`.
- `h803a` holds 0 documents and `openferment.documents_link` has 0 rows, while `sci_rag.documents` keeps
  1 document with source `project:h803a:upload` and source_ref
  `/tmp/openferment-collected-<random>/report-.md.md`.
- `h803b`'s upload of the same bytes answers `linked`; its document's `source` is
  `project:h803a:upload` and its `sourceRef` is that temporary path, a file that no longer exists.

**Likely cause** (high confidence).

- `core/openferment_core/literature/collectors.py:1671`: `name = Path(unquote(filename or "")).name`
  turns `%00` into a NUL character, which stays in the identifier.
- `core/openferment_core/intake.py:74` writes the identifier into `selection["sourceRef"]`
  (`upload:report\x00.md`).
- `core/openferment_core/literature/kit.py:596-602`: after `ingest_entries` has committed the document
  with the temporary path as its source_ref, a second session updates source_ref to the value with the
  NUL, which PostgreSQL refuses; the exception leaves `_store` before `_link` (`kit.py:603`) runs.
- `core/openferment_core/intake.py:113-117` catches `NotCollected` alone around the collector, and
  `store` (`intake.py:88`) has no guard around `kit.ingest`, so the database error reaches the route
  (`core/openferment_core/api.py:2087`) as a 500.

**Severity.** S3: an edge case (a file name carrying a percent-encoded NUL) with a workaround (upload
under another name, which links the kept document), though the kept document's sourceRef stays the
removed temporary path for every project that links it.
