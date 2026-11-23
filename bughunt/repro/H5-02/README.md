# H5-02 (with H8-02): a shared document reads in project B with project A's selection

**Statement.** When project B pastes a text project A pasted first, Intake tells B "linked" under B's
own title and licence class, and then every read B makes of that document (documents, overlay, search,
stats) serves A's title, A's url, a source naming project A, A's licence class and, when B states no
licence words, A's licence words.

## Contract

- `docs/decisions/ADR-002-sci-rag-kit.md:78-80`: "A document is stored once (the kit's content hash)
  with source `project:<id>:<collector>`; `documents_link` holds a row per project that holds it, with
  the selection (collector, identifier, licence as stated, reason, who)."
- `docs/api/intake.md:33-34`: "`source` (the project's source name, so two projects' selections stay
  apart)".
- `docs/api/intake.md:36-37`: "The project's link (`documents_link`) keeps the selection: `collector`,
  `identifier`, `url`, `pmcid`, `licence` (as the source stated it), `reason` ...".
- `docs/decisions/ADR-002-sci-rag-kit.md:84-85`: "a shared document is visible to each project that
  linked it and to no other". This clause governs which documents a project sees, and that part holds:
  B sees the two documents it linked. What A typed (a url, a title, licence words, its project id)
  is A's selection, and it reaches B.

## Command

```
bash bughunt/repro/H5-02/run.sh
```

It makes a fresh database `bh_r_h5_02_shared`, starts a keyless service on the first free port in
127.0.0.1:9010-9019 (collectors offline), makes projects `h502-a` and `h502-b`, and pastes two texts:

- text 1 (H5-02's shape): A as "A confidential draft title", `open_commercial`, licence words
  "CC-BY-4.0 as A states it", url `https://example.org/a-private-place`; B the same text as
  "B's own title", `restricted`, licence words "all rights reserved as B states it", no url;
- text 2 (H8-02's shape): A as "A's second title", `restricted`, licence words "A's words: internal
  use alone", no url; B the same text as "B's second title", `open_commercial`, no licence words.

Then it reads, as B, `GET /api/literature/documents`, `GET /api/biorepo/overlay`,
`GET /api/literature/search` and `GET /api/literature/stats`, scans them for A's words and compares
their licence class with B's statement. It stops the service, drops the database and removes the
service's data copy. `run1.log` and `run2.log` hold two runs.

## Expected

B's paste answers `linked` with B's title and class, and B's reads serve B's selection: B's titles, the
classes B stated (`restricted` for text 1, `open_commercial` for text 2), B's licence words or none, no
url, and no title, url, licence words or project id that A typed.

## Observed (both runs)

- B's paste answers: `linked`, "B's own title", `restricted`; `linked`, "B's second title",
  `open_commercial`.
- B's documents, text 1: title "A confidential draft title", citation "A confidential draft title.
  https://example.org/a-private-place", source `project:h502-a:paste`, sourceRef
  `https://example.org/a-private-place`, licenceClass `open_commercial`, beside B's own selection
  (licence "all rights reserved as B states it", url null).
- B's overlay, text 1: the same title, url `https://example.org/a-private-place`, licenceClass
  `open_commercial`, its passage heading "A confidential draft title".
- B's overlay, text 2: title "A's second title", url `paste:A's second title`, license
  "A's words: internal use alone", licenceClass `restricted`.
- B's search hits: A's titles and citations (A's url among them), licence classes `open_commercial`
  and `restricted`.
- B's stats: sources `{"project:h502-a:paste": 2}`.
- In all, 12 of A's words in B's reads and 6 licence-class reads that disagree with B's statement.
  `RESULT: DEFECT`.

## Likely cause

- `core/openferment_core/literature/kit.py:584-606` (`_store`): the kit keeps one `Document` per content
  hash, written at A's ingest; B's paste links it (`kit.py:603`) and keeps B's selection on the link
  alone; B's title, licence class and source reach no read.
- `core/openferment_core/api.py:2105-2107`: the documents route serves `d.title`, `d.formatted_citation`,
  `d.source`, `d.source_ref` and `d.license_class` from that one row; `api.py:2136-2137` serves the
  search hits' title, citation and licence class from the kit's row the same way.
- `core/openferment_core/intake.py:151,154,160,161`: the overlay falls back to `document.license_source`
  (A's words) when B stated none, and serves `document.title`, `document.source_ref` (A's url) and
  `document.license_class`; `literature/kit.py:719` heads each passage with the stored section path or
  A's title.
- `core/openferment_core/literature/kit.py:531-536` (`ProjectService.stats`) counts by the row's
  `source` and `license_class`; `tools/literature.py:72-74` serves the same row to Postdoc's tools.
- `core/openferment_core/intake.py:62` builds B's answer from B's own `Collected`, so the answer and
  the reads disagree.
