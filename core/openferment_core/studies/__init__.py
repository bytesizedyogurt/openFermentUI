"""Studies (execution prompt §7.2, §9.1 step 5): what a project asks of its
plants and keeps of the answers.

    scenarios   a plant on the shelf, its configuration and the values it
                sets, each a quantity whose origin is a named person's
                assumption or a model's estimate (ADR-006); run as an engine
                run (engine/runs.py)
    comparisons engine runs set side by side, kept as an artifact
    runbooks    a runbook made from an engine run, its predictions the
                run's outputs in their units, locked on the service under
                the digest the browser writes
    exports     the project's studies as one package: JSON, Markdown, the
                runs' SFF files and the versions they ran on, readable with
                no service

Studies import the engine, the literature layer and the store (§7.2), and
the project, artifact and provenance modules a study is kept and computed
with, the store of the project's runbooks and the lock digest
(test_boundaries.py names each). Importing this package imports none of
its modules.
"""
