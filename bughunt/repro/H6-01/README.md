# H6-01: an alpha 2.1 product kept with a category in its own words drops out of every head read after the upgrade

**Statement.** After `pnpm db:migrate` the head (2047f5a) leaves out every product alpha 2.1 kept with a
category outside the twelve classes the head now types, with no word to the person: the catalogue list, the
entry's own read (a 404 saying the catalogue holds no such entry), the catalogues screen and Postdoc's
`catalogue_read` all answer as if the entry had never been kept, while its row stays in `openferment.catalogue`.

## Contract

- `src/screens/Catalogues.tsx:570`, the screen's subtitle: "Every entry stays once kept, and keeping a file under
  an entry's id replaces it."
- `docs/api/intake.md:101`: "`GET /api/catalogues/{kind}` | The entries of `strain`, `product`, `skill` or
  `lesson`, by id"; `docs/api/intake.md:102`: "`GET /api/catalogues/{kind}/{id}` | One entry; 404 in words when
  the catalogue holds none".
- `docs/decisions/ADR-010-deletions.md:10-11`: "a person's entry, decision or artifact on a live instance is never
  deleted by this build". The rows stay in the table, so this line holds as written.

Alpha 2.1 took any word here: `category: str | None = Field(default=None, max_length=80)` (112eb8b,
`core/openferment_core/catalogues.py:69`), and its `catalogue_write` tool the same (112eb8b,
`core/openferment_core/tools/catalogues.py:51`).

## Command

    bash bughunt/repro/H6-01/run.sh

From the repository root. It makes a git worktree of 112eb8b under the scratch `bh/work/H6-01/` (run on the
repository's venv: `core/uv.lock` is the same file at both commits), makes the database `bh_r_h6_01_upgrade`
fresh with alpha 2.1's own migrations (`bh_db_fresh`, openferment at 0007), starts alpha 2.1's service on
127.0.0.1:9930, and keeps three products in project `h6-01`: `ethanol` ("biofuel") and `cellulase`
("industrial_enzyme", the control) through `POST /api/catalogues/product`, `xylitol` ("sugar alcohol") through
alpha 2.1's `catalogue_write`. It stops that service, runs the head's migrations (0010), starts the head's service
on 9931 and reads the list, each entry by id, `catalogue_read` and the table's rows. Keyless, no model call; it
stops both services, drops the database and removes the worktree, and exits 0.

## Expected

The three products alpha 2.1 listed (`cellulase`, `ethanol`, `xylitol`) still listed and read by id at the head,
or each one the head cannot read named to the person with why, as `GET /api/state` names a row it cannot read in
`refused` (ADR-007:73-74).

## Observed (both runs, run1.log and run2.log)

- alpha 2.1 lists `[cellulase (industrial_enzyme), ethanol (biofuel), xylitol (sugar alcohol)]`.
- After the head's migrations, `GET /api/catalogues/product` answers a bare list of one: `cellulase`.
- `GET /api/catalogues/product/ethanol` and `/xylitol` answer 404 "the project's product catalogue holds no
  ethanol" (and "... no xylitol"); `cellulase` answers 200.
- `catalogue_read` matched 1 (`cellulase`).
- `openferment.catalogue` still holds all three rows, each by "Ada Moreno".
- The only trace is a WARNING line in the service's log for each read: "the product catalogue's row ethanol does
  not read as an entry and is left out: category: a product's category is one of the classes pureOS's proposer
  reads ...".

`RESULT: DEFECT` in both runs.

## Likely cause

- `core/openferment_core/catalogues.py:217`: `category: ProductCategory | None = None`, the twelve-class Literal
  alpha 2.2 E.8.2 gave the field, with `_a_products_class` at `:276-288` raising for any other word.
- `core/openferment_core/catalogues.py:401-416`: `_readable` leaves a row that does not validate out of the list
  and logs it, and nothing reaches the answer; `get` (`:429-433`) reads that list, so its 404 says the catalogue
  holds no entry the table holds.
- `core/openferment_core/db/alembic/versions/0008_run_engine.py`, `0009_engine_checks.py` and `0010_protocols.py`
  touch no catalogue row, so nothing carries or flags alpha 2.1's free words on the upgrade.

The leaving-out is a recorded choice of alpha 2.2 E.15 (`docs/PROGRESS.md:2828`: "a row of an older shape is
left out and logged with why"), and `core/tests/test_catalogues.py:557-566` holds it with a product whose
category is "a word", as catalogue_write took them before E.8. What the record leaves unsaid, and what the screen
and the API document contradict, is that the person is told nothing and the entry's own read says the catalogue
holds none.

## Severity

S3. The rows stay in the table, and a person's keep under the same id writes the entry afresh (the test above
holds that path); the person needs the id from somewhere outside the catalogue's doors (the log, an alpha 2.1
export). A pg_dump copy of `openferment.catalogue` from `openferment_dev` and `openferment_dev_alpha21` into
`bh_r_h6_01_devcopy` (dropped after) found no catalogue rows in either, so the owner's development data holds no
entry this would hide.
