# H8-01: a text one letter's case apart from a held one is linked, and the project reads the other text

**Statement.** Project `rb` pastes "The biorefinery processes 2000 mg of dry corn stover per day ..."
after project `ra` pasted the same sentence with "2000 Mg"; `rb` is answered `linked` to `ra`'s
document, and `rb`'s passages and search read `ra`'s "2000 Mg", a unit 10^9 times the one `rb` gave,
and `rb`'s own words are stored nowhere.

**Contract.**
- `docs/api/intake.md:53`: "`linked` (the kit held the same text, and the project now holds it too)"
- `core/openferment_core/models.py:524`: "`linked`, the kit held the same text already and the project now holds it too"
- `core/openferment_core/literature/kit.py:14`: "A document the kit already holds (the same text, whoever collected it) is linked"
- `core/openferment_core/intake.py:7`: "linked (the kit held the same text already)"

**Command** (from the repository root): `bash bughunt/repro/H8-01/run.sh`

It makes a fresh test database `bh_r_h8_01_case`, starts the head's service keyless on
127.0.0.1:10240 to 10249 (the first free), makes projects `ra` and `rb`, pastes the two sentences
(`probe.py`), pastes a control in `rb` one word apart ("2000 kg"), reads `rb`'s overlay passages
and a search, reads `sci_rag.chunks` with psql, then stops the service and drops the database.

**Expected.** "2000 mg" and "2000 Mg" are two texts, so `rb`'s paste is ingested as a document of
its own (`ingested`), and `rb`'s passage reads `rb`'s "2000 mg".

**Observed** (run1.log and run2.log, the same both times):
- `ra`'s outcome `ingested <id>`; `rb`'s outcome `linked <the same id>`.
- `rb`'s passage reads "The biorefinery processes 2000 Mg of dry corn stover per day in the H8-01 repro."
- `rb`'s search hits read "2000 Mg" and the control's "2000 kg".
- `sci_rag.chunks` holds one row with "2000 Mg", one with "2000 kg", and none with "2000 mg".
- The control one word apart is `ingested` as a document of its own, so the dedupe is blind to letter case alone.

**Likely cause.**
- `core/.venv/lib/python3.13/site-packages/sci_rag/ingest/ingester.py:55-58`: `content_hash_for`
  joins the chunk bodies, collapses white space and lower-cases them before hashing; the kit then
  answers `skipped_duplicate` with the held document's id (`ingester.py:125-137`), and
  `sci_rag.documents` keeps `content_hash` unique (`sci_rag/db/models.py:92`).
- `core/openferment_core/literature/kit.py:584-605` (`_store`): a `skipped_duplicate` outcome is
  linked to the project and reported `linked` (line 604), with no comparison of the held chunks'
  text against the entry's own. The same path answers `held` within one project for a case-only
  variant of a text the project holds (checked once by hand on a fresh database: `ra` pasted the
  "2000 mg" sentence after its "2000 Mg" one, was answered `held`, and its passage read "2000 Mg").
