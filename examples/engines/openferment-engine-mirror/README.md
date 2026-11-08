# openferment-engine-mirror

A placeholder engine for openFerment's engine contract (`docs/api/engines.md`); it computes nothing scientific.
- `reflect`, its one thing, takes `placeholder-a` and `placeholder-b`, each with a placeholder default in a placeholder unit.
- A run returns each value it sets (one left alone, as its default) in its unit and key order, then `values set`, their count.
- The time the run took is the diagnostic `time taken` (ms) beside the outputs, since a replay compares the outputs alone.
- Its precision is rtol 0, atol 0, so a replay is identical; it has no plant, so it refuses its SFF file in words.
- Install (PEP 660 editable: uv's `pip install -e`, held to `core/uv.lock`) from the repository's `core/` in bash or zsh, then restart the service: `uv pip install --python .venv/bin/python -c <(uv export --frozen --all-extras --no-hashes --no-emit-project --quiet) -e ../examples/engines/openferment-engine-mirror`
- Test from this directory, with no database: `../../../core/.venv/bin/python -m pytest`
- Check it against the contract on a PostgreSQL server: `cd core && uv run python -m openferment_core.engine.conform mirror`
