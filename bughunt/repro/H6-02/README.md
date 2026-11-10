# H6-02: the alpha 1.0 import carries a model's estimate into BioRepo, read back verified and gold

**Statement.** `pnpm db:import-alpha1` carries an alpha 1.0 `biorepo.json` whose verified decision holds a gold
value with an origin of kind `model-estimate` into the project's decisions, and BioRepo then serves that record
as verified with provenance gold, while BioRepo's own door (`biorepo.write`) refuses the same decision by rule
`estimate`.

**Contract.**

- `CLAUDE.md:54` (R): "a model estimate never enters a record store, and each store refuses one (ADR-006;
  `core/tests/test_estimates.py`, acceptance A6)".
- `docs/decisions/ADR-006-quantities-and-estimates.md:97-100`: "No record store takes an estimate:
  `basis.refuse_estimates` finds an origin or a source of kind `model-estimate`, or a provenance `assumed`,
  anywhere in what a store is asked to keep, and BioRepo (`WriteRefused` rule `estimate`, a dry run included)
  ... refuse it before writing."
- `CLAUDE.md:108`: "BioRepo computes its provenance from what it decides ... and refuses `assumed` and any
  estimate (ADR-006)".
- The importer's own exemption, `core/openferment_core/import_alpha1.py:16-18`: "The stores' rules are not run
  again on old records (several cite records alpha 2.0 does not hold); each ran when its record was written."
  The estimate rule cites no record, and alpha 1.0's write never ran it: alpha 1.0 had no estimate rule and no
  origin field.

**Command.** From the repository root: `bash bughunt/repro/H6-02/run.sh`

It writes one alpha 1.0 data directory (`biorepo.json` alone, made by alpha 1.0's own models from
`git show alpha-1.0:core/openferment_core/models.py`, then an origin `{kind: model-estimate, by: claude-x}` added
to the gold value, as the hunt's `gen_alpha1.py` `estimate` case does), makes a fresh database
`bh_r_h6_02_import`, runs the module `pnpm db:import-alpha1` names
(`python -m openferment_core.import_alpha1 --name "Alpha 1.0 estimate" --by "Ada Moreno" --data ...`, on the
tree's own venv, keyless), starts a keyless service on 127.0.0.1:10230 over the result, reads
`GET /api/biorepo/overlay` and asks `POST /api/biorepo/check` with the same decision. Everything it makes is
removed when it ends.

**Expected.** The importer refuses the directory as `biorepo.write` refuses the decision (rule `estimate`), naming
`biorepo.json` and `cl1-P1-0001`, and writes nothing.

**Observed (run1.log, run2.log, both `RESULT: DEFECT`).**

- The importer exits 0: "carried ... into project alpha-1-0-estimate: 1 decisions".
- The decisions row reads `verified|gold|model-estimate|claude-x` (status, provenance, gold origin kind, by).
- `GET /api/biorepo/overlay` serves `cl1-P1-0001` as status verified, provenance gold, gold 3.0 mg L-1 with
  origin kind `model-estimate` by `claude-x`.
- `POST /api/biorepo/check` with the same decision answers `ok: false`, rule `estimate`: "BioRepo keeps
  records, and gold.origin is a model's estimate or rests on an assumption: an estimate may reach a scenario or a
  run, never a record (ADR-006)".

**Likely cause.** `core/openferment_core/import_alpha1.py:174-180` inserts each decision into `t.decisions` with
its provenance recomputed by `biorepo.provenance_of` and nothing else checked; `biorepo.write` calls
`basis.refuse_estimates` first (`core/openferment_core/biorepo.py:304-307`), and the import calls no part of it.
The importer reads the file through alpha 2.0's models (`import_alpha1.py:43-56`), whose `Quantity` types an
`origin` (`core/openferment_core/models.py:803`), so the origin the file holds is kept whole.

**Reach.** Alpha 1.0's `Quantity` holds a value and a unit alone
(`alpha-1.0:core/openferment_core/models.py:506-510`); step 1 of the run shows alpha 1.0's own `ReviewDecision`
reading the gold value as `{value: 3.0, unit: mg L-1}`, its origin dropped. A `biorepo.json` alpha 1.0 wrote
itself holds no origin, so the case takes a file edited by hand or made elsewhere (the file is tracked in git, so a
pulled copy is one such way). On such a file the outcome is a gold label over a model's estimate.

**Severity.** S3. The outcome on such a file is of the S1 kind (a gold label over a model's estimate, served as
sound), and its reach is an edge case: only a `biorepo.json` someone edited or made outside alpha 1.0 holds an
origin at all, and the record's own body names the estimate's origin for a reader who opens it.
