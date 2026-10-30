# ADR-004 — BioSTEAM is the engine, through one adapter

- **Status**: accepted (provisional choice; stage 4 implements it)
- **Date**: 2026-10-30

## Context

At `alpha-1.0` BioSTEAM runs in `workers/proforma_worker.py` behind the JSON-lines `SimWorker`
contract, with a shelf of four flowsheets, reference runs read against the `biorefineries`
package's own regression test (`flowsheets/shelf.py`, by `ast`), and scenario flowsheets
(`ethanol_glucose_v0`, `pha_sugar_v0`). The first domain of alpha 2.0 is cellulosic ethanol from
characterized biomass.

## Options

1. Keep the four-entry shelf.
2. A second engine.
3. Keep the worker and add a library plant runner and a composed cellulosic ethanol flowsheet.

## Decision

Option 3. The Proforma worker and the flowsheet pattern stay. `engine/library.py` discovers every
`biorefineries` plant the installed version exposes, builds each inside `package_defaults()`, reads
back its parameters as `ParameterSpec`s with `library-default` origins, runs with overrides
(`person-assumption` or `model-estimate`), prices and exports SFF. `flowsheets/cellulosic_ethanol_v0.py`
composes the `biorefineries.cellulosic` factories (pretreatment kind, fermentation kind `IB` or
`SCF`, reaction sets read from the package classes at import) and carries no number of its own.
Gates: per-reactant conversion sums, `InfeasibleRegion` turned into a refusal receipt, A→B→A
determinism after `empty_recycles()` and `tea._sales = 0`.

## Consequences

- fermOS, pureOS and Proforma keep their worker ops; their inputs become `Quantity` objects.
- NSKinetics keeps a socket in the adapter for a later phase.

## Revisit condition

A second engine; NSKinetics once a kinetic model exists.

## Evidence

- Execution prompt §3.2 (biosteam 2.54.0, thermosteam 0.54.2, biorefineries 2.35.1; cold import
  about 31 s; reference plant about 17 s; composed plant under 1 s after import; `SSCF` raises
  "not yet implemented"; `SCF` yields two `bst.BatchBioreactor` units).
- `core/pyproject.toml` `sim` extra pins at `alpha-1.0`.
