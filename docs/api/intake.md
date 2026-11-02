# Intake: how documents enter

A project reads only what Intake brought into it (execution prompt §7.3 item 6; ADR-002). Every
document ends as a row of Sci RAG Kit's corpus, a `CorpusEntry` the kit ingests, embeds and
searches, linked to the project with the selection that brought it. The code is
`core/openferment_core/intake.py` (what the routes call), `literature/collectors.py` (one function
a collector) and `literature/kit.py` (the kit's adapter). The routes' schemas are in
`docs/api/openapi.json`.

## The collectors

| Collector | Asked for by | Fetched from | Licence |
|---|---|---|---|
| `europepmc` | a PMCID, a DOI or `PMID:<id>` | Europe PMC: the record, then the open-access full text as JATS XML | the article's own licence element, read into a class |
| `osti` | `OSTI:<id>` or an osti.gov address | OSTI's record, then the report's PDF from the laboratory that holds it | read from the report's words, else "The source states no licence." |
| `sgd` | `SGD:<SGDID>` or a yeastgenome.org address | the SGD strain entry as JSON | CC BY 4.0, as SGD states it |
| `upload` | a file a person uploads: PDF, Markdown, text, HTML or JATS XML, at most 50 MB | the request | the class the person chose and their words for it |
| `paste` | text a person pastes under a title | the request | the class the person chose and their words for it |

A bare number is refused in words, since a PMID and an OSTI id look alike. In fixture mode
(`OPENFERMENT_FIXTURES=1`) every collector that would fetch reads `core/tests/fixtures/`
(or `OPENFERMENT_FIXTURE_DIR`) and refuses the network.

## What a document carries into the kit

`CorpusEntry` fields, as Intake writes them: `path` (the document written as a file for the
kit's ingester), `title`, `authors`, `year`, `doi`, `journal`, `license_class` (one of the kit's
classes; `unknown` when nothing says), `source` (the project's source name, so two projects'
selections stay apart) and `source_ref` (where it came from).

The project's link (`documents_link`) keeps the selection: `collector`, `identifier`, `url`,
`pmcid`, `licence` (as the source stated it), `reason` (why it was collected), `collectedAt`,
and `created_by`, the person who asked.

## The routes

| Route | Does |
|---|---|
| `POST /api/intake/collect` | `{identifier, by, reason}`: a document by its identifier |
| `POST /api/intake/upload` | multipart `file`, `by`, `title`, `licenceClass`, `licence`, `reason` |
| `POST /api/intake/paste` | `{title, text, by, url, licenceClass, licence, reason}` |
| `GET /api/literature/documents` | every document the project holds, with its chunk count and selection |
| `GET /api/literature/stats` | documents and chunks by source, licence class and embedding version |
| `GET /api/literature/search?q=` | passages best first, each with its document, passage id and citation |
| `POST /api/intake/{documentId}/extract` | candidates anchored to the document's stored passages (`extract.py`) |

Each answers HTTP 200 with a `CollectOutcome`: `status` is `ingested` (stored in the kit for the
first time), `linked` (the kit held the same text, and the project now holds it too), `held` (the
project held it before) or `failed` with the `reason` in words, and `transient` marks a failure
that was the network's condition. A failure is an answer the Intake board renders: the route
raises no 5xx for a document it could not collect.

## A project's catalogues (alpha 2.1)

The strains and their other names, the products, Guild's skills and Primer's lessons are kinds of
row in the project's `catalogue` table (migration 0007; `core/openferment_core/catalogues.py`), each
kept whole with who added it and where it came from. Names and words only: a number a paper
reports is a record. Nothing here deletes an entry.

| Route | Answers |
|---|---|
| `GET /api/catalogues/{kind}` | The entries of `strain`, `product`, `skill` or `lesson`, by id; 404 in words for another kind |
| `GET /api/catalogues/{kind}/{id}` | One entry; 404 in words when the catalogue holds none |
| `POST /api/catalogues/{kind}` | `{"entry": {...}, "by": "<name>"}` kept, an entry under the same id replaced; 422 in words for a field the kind does not take (a sequence on a strain, a species on a product, a sequence with no `sequenceSource`) |
| `POST /api/intake/catalogue` | A file of entries of one kind (form fields `kind`, `by`, `file`): a JSON list of objects (or one under `entries`), or a CSV with `id` and `name` columns and a list's items split by `;`. Every row that is an entry is kept with the file as its source; every other row is refused with its reason (`{"kind", "kept", "refused"}`) |

The readers that had read an empty list read these: geneOS's hosts and the strain aliases
(`module_stores`), ProtParam's products, pureOS's proposer (a proposal's host is a strain kept
here), Guild's skills and the lessons that count toward them. Postdoc reads a catalogue with
`catalogue_read` and keeps an entry, marked as its own and audited, with `catalogue_write`
(`docs/TOOLS.md`).
