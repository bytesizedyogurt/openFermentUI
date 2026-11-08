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

The same manners (the throttle, the User-Agent, a timeout, fixture mode's refusal) fetch the SFF
file a person names by its public https address (`literature/collectors.py` `fetch_file`, its host
checked as a public address before each request). That file becomes a flowsheet record of the
project and stays outside the kit's corpus (`docs/api/sff.md`, A file by its address).

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
| `GET /api/literature/stats` | documents and chunks by source, licence class and embedding version, and the concept graph's entities and relationships the project's own passages name and hold (`literature/graph.py`) |
| `GET /api/literature/search?q=` | passages best first, each with its document, passage id and citation |
| `POST /api/intake/{documentId}/extract` | candidates anchored to the document's stored passages (`extract.py`) |

Each answers HTTP 200 with a `CollectOutcome`: `status` is `ingested` (stored in the kit for the
first time), `linked` (the kit held the same text, and the project now holds it too), `held` (the
project held it before) or `failed` with the `reason` in words, and `transient` marks a failure
that was the network's condition. A failure is an answer the Intake board renders: the route
raises no 5xx for a document it could not collect.

## A project's catalogues (alpha 2.1; alpha 2.2 E.8 and E.12a)

The strains and their other names, the products, Guild's skills and Primer's lessons are kinds of
row in the project's `catalogue` table (migration 0007; `core/openferment_core/catalogues.py`), each
kept whole with who added it and where it came from. Names and words only: a number a paper
reports is a record. The numbers an entry holds are a person's own writing: a skill's policy, and
a lesson's minutes and the answers its checkpoint grades against (ADR-018). Nothing here deletes an
entry. The catalogues screen (`/catalogues`, a tab a kind) lists each catalogue, adds and edits an
entry in the name Settings holds, and takes in a file through `POST /api/intake/catalogue`.

Every kind takes `id`, `name`, `summary`, `note` and `source`; each kind's own fields are these, and
a field of another kind is refused in words:

| Kind | Its own fields |
|---|---|
| `strain` | `species`; `program`, the chemical set its trains use, as pureOS names it; `aliases`, the other names papers give it |
| `product` | `category`, one of the classes pureOS's proposer reads (`molecular_biology_enzyme`, `diagnostic`, `research_protein`, `food_protein`, `sweet_protein`, `structural_protein`, `industrial_enzyme`, `therapeutic_protein`, `hmo`, `terpene`, `glycoside`, `biopolymer`), any other refused in words at the keep and at the file; `location`, `secreted` or `intracellular`, which the proposer's rules split a protein or a polymer on; `sequence` with `sequenceSource`, where it was read |
| `skill` | `family`; `mastery`, what an assessor watches for; and its policy: `criticality` (`routine` or `critical`), `recencyDays` (how many days a qualification stands with nobody seeing the person perform), `supervisedRuns` (how many cosigned runs come before a witnessed check can qualify) and `prerequisites` (the ids of the skills that must be at Supervised or above first). A policy names its first three together, all three or none; Guild rates nobody on a skill kept with none, and the cosign, the run alone and a check asked for by name say so in words |
| `lesson` | `skills`, the ids of the skills it counts toward; `minutes`, how long it takes, 1 to 600; `blocks`, its body in order, each a run of prose in Markdown (`{"kind": "prose", "md"}`) or one of the nine embeds Primer's page draws (`{"kind": "embed", "embed", "arg"}`: `chip-demo`, `record-card`, `mini-queue`, `metrics-tiles`, `strip-plot`, `protocol-card`, `ask-prompt`, `scenario-widget`, `skill-steps`, with the id or the words it is drawn on); and `checkpoint`, its questions, each with an `id` of its own, a `prompt`, an `explanation` and an `evidenceChip`: a multiple-choice one (`kind: "mc"`) with two `options` or more and the `answerIndex` of the one that answers it, a numeric one (`kind: "numeric"`) with its `answer`, `{value, unit, tolerancePct}`, the unit empty for a pure number or one the unit converter reads and the tolerance 0 to 100 percent of the value. A JSON file takes a lesson's body, and a CSV row its minutes |

| Route | Answers |
|---|---|
| `GET /api/catalogues/{kind}` | The entries of `strain`, `product`, `skill` or `lesson`, by id; 404 in words for another kind |
| `GET /api/catalogues/{kind}/{id}` | One entry; 404 in words when the catalogue holds none |
| `POST /api/catalogues/{kind}` | `{"entry": {"kind": "<kind>", "id": "...", "name": "...", ...}, "by": "<name>"}`, the entry as the catalogue answers one, kept as a person's keep and audited as `keep_catalogue` (its target `<kind>/<id>`, under the module that reads the kind: `geneos`, `pureos`, `guild` or `primer`), an entry under the same id replaced; the service writes `by`, `agent`, `via` and `at` over what the entry sends. 422 with a list of field errors for a field the kind does not take (a sequence on a strain, a species on a product, a sequence with no `sequenceSource`, a category outside the classes, a policy with a part left out), and in the service's words for an entry of another kind and for a keep that names nobody |
| `POST /api/intake/catalogue` | A file of entries of one kind (form fields `kind`, `by`, `file`): a JSON list of objects (or one under `entries`), or a CSV with `id` and `name` columns and a list's items split by `;` (`aliases`, `mastery`, `skills`, `prerequisites`). Every row that is an entry is kept with the file as its source and audited as `keep_catalogue`, its detail naming the file; every other row is refused with its reason (`{"kind", "kept", "refused"}`) |

The readers that had read an empty list read these: geneOS's hosts and the strain aliases
(`module_stores`), ProtParam's products, pureOS's proposer (a proposal's host is a strain kept
here, and a product's class and location are read from its entry), Guild's skills with their
policies and the lessons that count toward them. Postdoc reads a catalogue with `catalogue_read` and
keeps an entry, marked as its own and audited, with `catalogue_write` (`docs/TOOLS.md`), which
takes no number: a skill a model keeps holds no policy until a person writes one, and a lesson a
model keeps holds no body. `catalogue_read` lists a lesson with its skills and minutes; Primer
draws its body, and the catalogues screen counts its blocks and checkpoint questions and keeps the
body as the lesson holds it when a person edits the lesson's other fields.
