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
