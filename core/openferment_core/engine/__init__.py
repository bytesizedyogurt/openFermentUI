"""The engine (execution prompt §7.2; ADR-003, ADR-004): BioSTEAM through one
adapter, and SFF as the flowsheet record.

    simulator   the Proforma worker, BioSTEAM in its own process: started,
                kept warm, and called by every engine module
    sff         SFF flowsheet records: a run's export, an imported file, the
                toolkit's reference flowsheets fetched and hashed; each with
                its validation, completeness report, tags and graph

The engine imports `db`, `models`, the `workers` client, `params` and
`binding`; BioSTEAM and the vendored SFF toolkit run in the worker alone
(workers/proforma_worker.py, workers/sff_toolkit.py, flowsheets/). Importing
this package imports none of its modules.
"""
