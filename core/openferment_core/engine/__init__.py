"""The engine (execution prompt §7.2; ADR-003, ADR-004): BioSTEAM through one
adapter, and SFF as the flowsheet record.

    simulator   the Proforma worker, BioSTEAM in its own process: started,
                kept warm, and called by every engine module
    sff         SFF flowsheet records: a run's export, an imported file, the
                toolkit's reference flowsheets fetched and hashed; each with
                its validation, completeness report, tags and graph
    library     the library plant runner: every plant the installed
                `biorefineries` exposes, on a shelf regenerated from
                discovery; its parameters read back as library defaults; a
                run with a person's values, priced, kept, held to the
                package's own test
    runs        engine runs on the `runs` table: a library run's inputs
                with their origins, its artifact, its SFF file written and
                checked, its status (a refusal kept as a receipt)

The engine imports what §7.2 lists (`db`, `models`, the `workers` client,
`params`, `binding`), and two more until they move into it: the shelf's
package-test reader (`flowsheets/shelf.py`, no BioSTEAM) and the artifact
store a run is kept in (`artifacts`), the project a run belongs to
(`projects`) and the provenance rules (`basis`). BioSTEAM
and the vendored SFF toolkit run in the worker alone (workers/proforma_worker.py,
workers/library_plants.py, workers/sff_toolkit.py, flowsheets/). Importing
this package imports none of its modules.
"""
