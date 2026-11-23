# H3-17: the catalogue route keeps an entry and drops a field no kind takes, with a 200

**Statement.** A person's keep of a strain carrying a field no kind takes (`titre`, a quantity whose
origin is a model's estimate) at `POST /api/catalogues/strain` is answered 200, the entry is kept, and
the field is dropped without a word.

**Contract.** `docs/api/intake.md:103`, the `POST /api/catalogues/{kind}` row: "422 with a list of
field errors for a field the kind does not take (a sequence on a strain, a species on a product, ...)".
`docs/api/intake.md:89` sets which fields a kind takes: "Every kind takes `id`, `name`, `summary`,
`note` and `source`; each kind's own fields are these". The route's own docstring
(`core/openferment_core/api.py:1174`) repeats it: "422 in words for an entry the kind does not take".

**Command.** `bash bughunt/repro/H3-17/run.sh` from the repository root. It makes a fresh database
`bh_r_h3_17_svc`, starts a keyless service on the first free port of 9500..9509, makes project `p1`,
runs `repro.py`, then stops the service and drops the database. Nothing is mutated or built, so no
worktree is made.

**Expected.** The keep of strain `s-h317` with `titre` refused with a 422 whose field errors name
`titre`, and nothing kept under `s-h317`.

**Observed (run1.log, run2.log).** The control (a species on a product) is a 422 in words. The strain
with `titre` is answered 200; the answer and the entry read back from
`GET /api/catalogues/strain/s-h317` hold no `titre`, kept in the name of Ada Lovelace. Both runs print
`RESULT: DEFECT`.

**Likely cause.** `core/openferment_core/catalogues.py:204`: `class CatalogueEntry(BaseModel)` sets no
`model_config`, so pydantic's default `extra="ignore"` drops any key outside the declared fields before
`_fits_its_kind` (`catalogues.py:290`) sees the entry; that validator checks the declared fields of the
other kinds alone. `CatalogueKeep.entry` (`core/openferment_core/api.py:1120`) is that model. Many
request models in `models.py` set `ConfigDict(extra="forbid")`; this one does not.

**Note.** The estimate never enters the store, so ADR-006's refusal of an estimate in a record store
holds; the break is the route's promised 422, and a person who sends a field by mistake (a misspelt
`specie`, a number a paper reports) gets a 200 and loses it silently.
