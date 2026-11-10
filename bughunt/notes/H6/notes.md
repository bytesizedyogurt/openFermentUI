# H6: the upgrade path

Hunt H6 at 2047f5a: alpha 2.1 (main, 112eb8b) filled through its own API, migrated with the head's migrations
and read by the head; the head's migrations on their own; `pnpm db:import-alpha1` on alpha 1.0 data. Keyless
throughout, no model call, no network beyond loopback. Services on 127.0.0.1:8860-8866, every one stopped;
databases bh_h6_*, every one dropped; worktrees wt-main and wt-head removed. Five candidates, H6-01 to H6-05.

To run a script again, make the two worktrees first (scratch `$BH_WORK/H6/`):

    git -C /home/user/openFermentUI worktree add --detach $BH_WORK/H6/wt-main 112eb8b
    (cd $BH_WORK/H6/wt-main/core && bh_env uv sync --frozen --all-extras)
    git -C /home/user/openFermentUI worktree add --detach $BH_WORK/H6/wt-head 2047f5a
    (cd $BH_WORK/H6/wt-head/core && bh_env uv sync --frozen --all-extras)

## 1. Alpha 2.1 filled, migrated, read by the head

`main_svc.sh` starts alpha 2.1's service (fixture mode) over bh_h6_a21, made with alpha 2.1's migrations (0007).
`fill_prove.py` imports alpha 2.1's own `scripts/prove.py` and runs its steps 2 to 7 against it (39 checks, all
held): a project, the kit's demo corpus through Intake's upload, a stand-in's candidate extracted and accepted,
the cornstover library run, the composed flowsheet, sugarcane, a replay, a scenario with an assumption and an
estimate, its run, a comparison, a study runbook locked, the export, Postdoc's evaluation offline (two turns,
tool calls, eval rows), a reference SFF file imported. `fill_extra.py`, `fill_extra2.py` and `fill_extra3.py`
add the rest in the shapes alpha 2.1's client sent (src/data/types.ts at 112eb8b): a pasted document, two
collected through the fixtures (JATS, SGD), a catalogue CSV, one entry of each catalogue kind (a product in a
class and one in alpha 2.1's free words, a third through alpha 2.1's own catalogue_write), Guild's people,
policy, evidence and a check, a page runbook and its lock, a deposition with a series, measured evidence,
fits, overrides, a Proforma scenario and three Proforma runs (overrides, the older `assumptions`, an estimate),
the retired benchmark and corn_drygrind reference, a fermOS fit, forecast, simulation and vessel, a train read
from the run, run and saved in the Builder, a proposal's property artifacts, thermo, ProtParam, an SFF export
and upload, a page's Live conversation, and a second project with its own rows.

`snapshot.py` reads every list and detail route of each project before and after; `compare.py` and
`deepdiff.py` set them side by side (logs/compare.log, logs/deepdiff.log). After `pnpm db:migrate` every value
read the same except: the product catalogue (3 to 1, H6-01), the shelf's two retired entries (by design, D8),
one page runbook I wrote with a kind alpha 2.1's own client never sends (named in `refused` and in the screen's
toast, as documented), and words in notes and tool descriptions. `replay_all.py` replayed every alpha 2.1
artifact at the head: all identical but the three proforma.run (1 ulp; the same at alpha 2.1 cold; suspected).
`screens.cjs` opened every rail entry and 112 more pages in Chromium: no console error, no failed request
(three flags were my own wrong links or the regex reading "not found in them").

Found: H6-01. Held: run engines from 0008, project scoping, kept retired runs, depositions written onto, a
fermOS request asked again keeping its row.

## 2. The migrations alone

`migrate_checks.sh`: empty to head twice (schema dumps equal), alembic `compare_metadata` against the table
models (0 differences), 0010 to 0007 and back, head to base and back (schemas equal); the kit's 0006 to base
and back. A copy of the upgraded database with a head kinetics row went to 0007 and back with its engine
kept. `check_jsonb.sh`: every content column is json (H6-05). The head over an unmigrated 0007 database
answers most reads and a bare 500 for /api/protocols; `pnpm ready` names the revision (suspected, S4 at most).
`db:migrate` and `db:reset` ran as package.json writes them from wt-head.

## 3. pnpm db:import-alpha1

The alpha-1.0 tag's core/data holds biorepo.json alone (empty). `gen_alpha1.py` loads alpha 1.0's own
models.py (it imports pydantic alone) and writes a full data directory with them (decisions labelled curated,
gold and demo; guild, checks, practice, proposals, audit, an artifact naming demo, a model and a hand
extraction, a kept train), plus copies: truncated, empty file, empty directory, a bad status, an estimate as a
gold value, a decision naming no reviewer, a key/recordId mismatch, a person twice, a paper's extraction
twice, an artifact twice, 30000 decisions. `run_imports.sh` runs package.json's exact command from wt-head on
each (logs/imports.log); `repro_import.sh` is the short form for H6-02 to H6-04.

Held: the full directory lands and reads back through the head (demo read as assumed, the output hash
recomputed, the provenance computed as biorepo.write computes it), files left byte for byte, malformed and
empty files refused in words with nothing written, a 0007 database refused naming db:migrate, 30000 decisions
in 18 s, the environment's packages unchanged. A second import makes alpha-1-0-full-2 with the same rows, as
the docstring says it makes a new project. Found: H6-02 (an estimate carried as gold), H6-03 (tracebacks),
H6-04 (counts of rows the upsert did not keep).

## Files

Scripts: main_svc.sh, fill_prove.py, fill_extra.py, fill_extra2.py, fill_extra3.py, snapshot.py, compare.py,
deepdiff.py, replay_all.py, screens.cjs, migrate_checks.sh, check_jsonb.sh, gen_alpha1.py, run_imports.sh,
repro_h6_01.sh, repro_import.sh. Logs under logs/; catalogue-products-after-upgrade.png is the head's Products
tab over the upgraded database (ethanol gone, the state toast shown, no word on the catalogue).
