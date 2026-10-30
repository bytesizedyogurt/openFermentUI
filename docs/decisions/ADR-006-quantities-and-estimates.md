# ADR-006 — Typed quantities with origins replace Rule 1

- **Status**: accepted (requirement: the owner reopened Rule 1 and asked for labelling)
- **Date**: 2026-10-30

## Context

Rule 1 at `alpha-1.0` forbids any number of model origin: `validate_plan` drops a claim whose text
holds a digit, prompt rules 5, 8, 9, 12 and 15–17 forbid numbers and estimates, and
`tools.numbers_in` refuses any JSON number in a tool input outside `k` and `limit`. The revised
white paper and the development plan allow a clearly identified estimate whose origin and limits
stay visible.

## Decision

Every number a model, a person or a library supplies enters as
`Quantity {value, unit, basis?, low?, high?, origin}` with
`Origin {kind: record | artifact | person-assumption | model-estimate | library-default | convention, ref, by, at, note}`.

- Provenance is computed from origins by code (`basis_provenance`, `weakest_provenance`, the
  client's display of the server's answer), never set by a model or a person.
- A model-originated number is an estimate: it carries the model id; it makes any result that rests
  on it `assumed` (the old `demo` code, renamed); it never enters a record store; it is never
  averaged into evidence; it is marked wherever it appears.
- Claims carry numbers only in a typed `values` list. Text with a bare number is still dropped and
  counted.
- Tool inputs carry numbers only inside `Quantity` objects.

## Consequences

- `PROVENANCE_ORDER` renames `demo` to `assumed`; `basis_provenance` treats `model-estimate` like
  `assumption`; `binding.exclusion` keeps estimates and computed values out of aggregates; the
  figure encoding gains the `assumed` mark.
- A negative test plants a model estimate at each record-store boundary and watches the refusal
  (acceptance A6).
- Evaluations check the distinction between a labelled estimate and a number presented as a
  measurement.

## Revisit condition

A task needs a formal decision rule or uncertainty method; it is justified and evaluated for that
task (development plan §8).

## Evidence

- `core/openferment_core/postdoc_agent.py`, `validate.py`, `tools/__init__.py` (`numbers_in`) at
  `alpha-1.0`; development plan §2 "A conflict we need to resolve deliberately" and §8 "Make
  estimates useful and honest".

## Implementation

### 4.4 (2026-10-30): `demo` renamed `assumed`

- The class is renamed everywhere it is written: `Provenance` and `PROVENANCE_ORDER` in
  `models.py` (still ninth and weakest), `weakest_provenance`'s answer for a class it does not
  know, `basis_provenance`, and on the browser's side the `Provenance` union, `PROVENANCE_RANK`,
  the tick (`tick-assumed`), the legend, the figure encoding (`ENCODING.assumed`, still amber,
  hollow and short-dashed, and one of the two classes in `NEVER_EVIDENCE`), the CSV disclosure
  and every screen that names it. The label reads *Assumed · not measured*. `check:plan` holds
  the two vocabularies equal and `check:figures` holds the encoding.
- Rows already stored are rewritten by migration 0003 (`db/alembic/versions/0003_assumed.py`):
  every text column named `provenance`, and in every JSON column of the schema the value of
  every key named `provenance`; nothing else in a row changes. An artifact whose output named
  the class has its output hash computed again over the output as rewritten, so a replay
  compares like with like; artifact ids hash the inputs, which name no provenance, and runbook
  lock hashes cover predictions' values and measures, which name none, so both stay. The
  downgrade renames it back. `test_db.py` moves a database from 0002 to 0003 and back.
- Alpha 1.0's files say `demo`: `import_alpha1` reads every `provenance` through
  `models.renamed_provenance` (the map `RENAMED_PROVENANCE`) before a model checks it, and gives
  an artifact whose output changed the hash of its output as read, as the migration does.
- The lesson embed `chip-demo` (a demonstration of a citation chip), the `demo.py` the tests'
  stand-ins came from and the kit's demo corpus keep their names: none is the class.

### 4.4 (2026-10-30): quantities with origins, a model's estimate, the record stores' refusal

- `models.Origin {kind, ref, by, at, note}` with the six kinds this record names: a
  person-assumption or a model-estimate names its author (`by`), a record, an artifact or a
  library default names what it was read from (`ref`). `Quantity` gains `basis`, `low`, `high` and
  `origin`, all optional; a quantity with none of them is written exactly as before (a wrap
  serializer drops them), so stored outputs keep their hashes and stored records their rows. The
  browser's `Quantity`, `Origin`, `OriginKind` and `OverrideOrigin` mirror them (`check:plan`
  pairs `Origin`).
- A basis source may be a `model-estimate` (`basis.estimate_source`: the model's id in `by`, the
  moment in its note). `basis_provenance` makes anything resting on one `assumed`, as it does an
  `assumption` (`ASSUMED_KINDS`); `basis.origin_of` reads any basis source as its origin, the day
  stamped in its note included.
- An `Override` carries `origin`: `person-assumption` (the default, as every override was) or
  `model-estimate`, whose `by` names the model. `params.checked` holds a person's name to the
  reviewer rule and a model's to one line; `_from_override` and the library runner take their
  source from `basis.override_source`; the panel's chip reads `model-estimate` (`ParamOrigin`), and
  every reader of a run's basis (Proforma's sampling, fermOS's and pureOS's read-back, the vessel
  design, the composite, the tools' words) reads an estimate where it reads a person's value. The
  sourceRule entry `assumption` (a value set for the run may set this parameter) admits both.
- `binding.exclusion` (and the browser's `aggregateExclusion`) keeps an `assumed` value out of
  every aggregate.
- No record store takes an estimate: `basis.refuse_estimates` finds an origin or a source of kind
  `model-estimate`, or a provenance `assumed`, anywhere in what a store is asked to keep, and
  BioRepo (`WriteRefused` rule `estimate`, a dry run included), the candidates store and a
  project's depositions and measurements (`StateRefused`) refuse it before writing.
  `test_estimates.py` plants one at each and watches the refusal (A6), and shows an estimate
  reaching a library run (whose basis names the model and which is `assumed`), a parameter panel
  and a scenario's overrides.
- Unchanged on purpose: `BasisSource` and `BasisInput` gain no field, so every artifact id stays
  what it was (§7.4); ParamOrigin and the sourceRule keep the word `assumption` for a person's
  value, the name ADR-006 gives it being `person-assumption` in `Origin`.
