# H14-01: a second ask over the same runs retitles the one comparison and keeps its maker

## Statement

The candidate says that when a person compares runs another maker already compared in the same
order, the service replaces the kept comparison's title with the new one and keeps the row's `by`
and `at` as the first maker's, so the first title goes with no audit row.

## Contract the candidate names

- `docs/api/studies.md:127`: "the same runs in the same order are one comparison".
- `CLAUDE.md:56`: "Every scientific row carries `project_id`, `created_by` and `created_at`".
- `CLAUDE.md:8`: "every claim, number and result stays inspectable back to its source, its
  calculation and its assumptions".

What the tree itself says a repeated ask does:

- `core/openferment_core/db/rows.py:59-60` (`rows.put`): "A row that exists keeps who made it and
  when; `updated_at`, where the table has it, moves."
- `core/tests/test_comparisons.py:106-111`
  (`test_the_same_runs_in_the_same_order_are_one_comparison`): Ada Moreno compares, Grace asks
  again over the same runs titled "Dearer cane, renamed", and the test asserts the same id, the
  title "Dearer cane, renamed", `by == "Ada Moreno"` and one listed comparison.
- `core/openferment_core/studies/scenarios.py:141-143`, the sibling store built the same way:
  "the same plant, configuration and values kept already are that scenario, its title and note
  brought up to date".
- `docs/api/studies.md` names an audit row for a reading's choice, a runbook's lock and a
  protocol's keep. It names none for a comparison.

## Command

    bash bughunt/repro/H14-01/run.sh

The script makes a fresh database `bh_r_h14_01_cmp` and starts the keyless service on
127.0.0.1:9300. It runs corn and sugarcane at the package's own defaults as Ada. Then Ada
compares them titled "A: Ada's question", and Ben compares the same two runs in the same order
titled "B: Ben's question". The script prints both answers, the project's list, the
`comparisons` row, the count of audit rows that name a comparison, and the tree's own lines on a
repeated ask. Then it stops the service and drops the database.

## Expected

By `studies.md:127`, `rows.py:59-60` and the test at `test_comparisons.py:106-111`, Ben's ask is
the one comparison Ada made: one row under the artifact's id, `by` and `at` Ada's, the title the
latest ask's. No document asks for an audit row for a comparison. The candidate expects Ada's
title to stay, Ben's ask to be refused, or a second row in Ben's name. None of the cited lines
says any of these.

## Observed

Both runs (`run1.log`, `run2.log`) show what the candidate saw. There is one comparison, and the
second answer keeps its id. Its title is now "B: Ben's question", its `by` is Ada and its `at` is
Ada's time. The row's `created_by` is Ada, and no audit row names a comparison. This is the
behaviour the tree specifies and its own test pins, so the script prints `RESULT: NO-DEFECT`.

## Likely cause (of the behaviour)

`core/openferment_core/studies/comparisons.py:266-273`: `make` reads the held row, keeps
`held.by` and `held.at`, takes the asker's title and writes the row through `rows.put`
(`core/openferment_core/db/rows.py:49-66`), an upsert that replaces the body and keeps
`created_by`. The code does this on purpose. The one gap is in the words:
`docs/api/studies.md`'s Comparisons section never says that a later ask retitles the comparison
and keeps its maker. The test pins it, and the sibling scenarios module says it in words.
