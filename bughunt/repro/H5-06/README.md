# H5-06: a request naming no project is answered as an empty project

**Statement.** With no `X-OpenFerment-Project` header, the catalogue readers answer as if the project's
catalogue were empty (protparam and pureOS's proposer a 404 saying the product is not in the products
catalogue, Guild's check a 200 saying the skill is not held, Guild's evidence a 422 about the skill), and
the tool door answers 200 with `<tool> failed: ProjectRequired: ...` or a document "the project" does not
hold, where `GET /api/audit` and `GET /api/catalogues/product` answer the 422 that names the header.

**Contract.**
- `docs/decisions/ADR-005-projects.md:28-29`: "A store reads the project from `projects.current()`, and a
  store call in a request that names none is a 422 that says which header to send."
- `core/openferment_core/api.py:202-204` (the OpenAPI document's description, `docs/api/openapi.json`):
  "a request naming none is a 422 in words at its first store call".

**Command** (from the repository root): `bash bughunt/repro/H5-06/run.sh`

It makes a fresh test database `bh_r_h5_06_noproj`, starts a keyless service on the first free port of
127.0.0.1:9120-9129 from `core/` as at 2047f5a, makes project `bh-a` holding a product (`product-a`, with a
placeholder sequence), a strain (`strain-a`) and a skill (`SK-A`), then asks each route once naming `bh-a`
and once naming no project. The service is stopped and the database dropped at the end.

**Expected.** Each request naming no project answers 422 with the words "This names no project. A request
sends the X-OpenFerment-Project header ...", as `GET /api/audit` and `GET /api/catalogues/product` do.

**Observed** (run1.log and run2.log alike):

| request, no project named | answer | naming `bh-a` |
|---|---|---|
| `GET /api/audit` | 422, names the header | 200 |
| `GET /api/catalogues/product` | 422, names the header | 200, `product-a` |
| `GET /api/protparam?product=product-a` | 404 "there is no product 'product-a' in the products catalogue, so it carries no sequence to compute from" | 200 `{"artifact": null}` |
| `POST /api/pureos/propose` | 404 "there is no product 'product-a' in the products catalogue or among the chemicals ..." | 200, a proposal |
| `POST /api/guild/check` | 200 `ok:false`, "'SK-A' is not a skill Guild holds (none ship with alpha 2.0)" | 200, a later rule ("Primer has no lesson lesson-a") |
| `POST /api/guild/evidence` | 422 "skill: 'SK-A' is not a skill Guild holds" | (not asked: it writes) |
| `POST /api/tools/catalogue_read?by=bob` | 200, error "catalogue_read failed: ProjectRequired: This names no project. ..." | 200, one entry |
| `POST /api/tools/literature_document?by=bob` | 200, error "the project holds no readable document '...' (ProjectRequired)" | 200, the same words with (ApiError) |

**Likely cause.**
- `core/openferment_core/catalogues.py:585-590`: `_entries` catches `projects.ProjectRequired` and returns
  `[]`, and `as_products`, `as_hosts`, `as_strain_aliases`, `as_skills` and `as_lessons` read through it, so
  protparam (`protparam.py:253`), the proposer and Guild (`guild.py:151-152`) see an empty catalogue.
- `core/openferment_core/protocols.py:291-296`: `held` does the same for protocols (`guild.py:153`).
- `core/openferment_core/tools/__init__.py:551-558`: the tool door's `except Exception` turns
  `ProjectRequired` into `<name> failed: <class>: <words>` inside a 200 `ToolResult`.
- `core/openferment_core/tools/literature.py:52-56`: `_document` catches every exception, ProjectRequired
  among them, as a document the project does not hold.

**Severity S3.** The client and the MCP server's `--service` mode always name a project, so the case is a
request from a script or a stranger's client; sending the header is the workaround. The answers mislead
(a held product reads as absent, a held skill as unknown) and show no wrong number.
