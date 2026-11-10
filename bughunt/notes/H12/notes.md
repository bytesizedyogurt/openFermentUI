# H12: the test audit

Hunt H12 at 2047f5a. Every run keyless and offline of any model; every database `bh_h12_*`, dropped after. Two
worktrees of my own (`$BH_WORK/H12/wt`, `$BH_WORK/H12/wt2`), each with the conform scratch prefix renamed to
`bh_h12_conform` (`mutations/BASE-scratch-name.patch`) so the conformance tests make no database outside `bh_h12_*`;
the one test that asserts the old prefix (`test_sigterm_ends_the_command_with_its_code_and_drops_the_checks_database`)
is left out of every mutation run. The generated fixtures `test:core` exports (units.json and five others) were
copied from the main tree, whose `src/` is 2047f5a's.

## Mutation testing

`scripts/mutate.py` applies one mutation at a time (`mutations.json`, `mutations2.json`, `mutations3.json`, made by
`scripts/make_mutations*.py`), runs the module's own tests and every test that imports it with `-x`, restores the
file and writes `mutations/<id>.patch` and a line of `mutations/results.jsonl`. 85 mutations over 25 functions and
their neighbours: 66 caught, 19 survived. `scripts/survivor.sh ID` shows a survivor from scratch.

Survivors and what they mean:

- conform checks 1, 3, 4, 5, 8 (M50-M54): H12-02. The suite has negative tests for checks 2, 6 and 7 alone.
- spend's day lock (M45): H12-03; the race probe overruns the cap in 20 of 20 rounds without it, 0 with it.
- guard's forwarded-host check (M30): H12-04; the probe shows the rebinding request let through.
- guard's Funnel refusal for a key on a read (M31) and request_key's blank key (M28): H12-08.
- answers_to's suffixes (M32): H12-09.
- keep_run's branch for a held row with neither file nor words (M21b, M24b): H12-10.
- ready's literature revision (M65): H12-11. corrected_by's latest correction (M37): H12-12.
- is_measurement's note rule (M05): H12-13.
- the IPv4-mapped rule (M57): survives on 3.13 alone, caught on 3.12 (H12-15).
- the worker boundary for biorefineries (N09): H12-06.
- Equivalent or near-equivalent, no candidate: M70 (RecordStatus holds no `corrected`), M33 (DepositionEntry
  requires `confirmed`, so a row without it does not validate).
- Caught for a reason worth noting: N01 (the kit's calls on a thread that loses the context) fails test_llm's room
  test through the tally, which rides the same context as the key; N08 (biorefineries imported on the catalogue's
  path) fails test_workers' subprocess test at run time.

## Beyond mutation

- `seed_probe.sh`: a service module typing a titre, a yield, a composition and a price, and a src/data file
  exporting a yield table, pass test_no_seed.py (H12-05). The current tree types none (grepped).
- `spend_nan.sh`: OPENFERMENT_DAILY_BUDGET_USD = nan, NaN or inf holds a $1,000,000 reservation (H12-01).
- `lock_drift.sh`: `uv run --all-extras` rewrites a stale core/uv.lock and runs; `uv lock --check` refuses it; CI runs
  no frozen sync (H12-07).
- check:plan fails on either ranking copy swapped alone (G1, G2), and passes the two swapped together (G4, H12-14);
  G3 (the Literal swapped too) is caught by test_openapi. check:secrets fails on a key-shaped string planted in a
  tracked src/ file and in a tracked service module; dist/ holds none.

## Python 3.12 and 3.13

`pyver.sh 3.12|3.13` over H12's 95 test files in the second worktree: 2273 passed and 3 failed on both, the same
tests (test_host's three, from the worktree having no core/.venv for scripts/host/lib.sh; 52 of 52 pass once it has one), 2276 rows identical.
`ipclass.py` reads the same refusal class for 36 addresses on both. No 3.13-only API is used in the service. The one
difference is H12-15: Python 3.13's ipaddress reads an IPv4-mapped loopback as loopback, so on 3.13 no test holds
`_v4`. The 3.12 here is Ubuntu's 3.12.3 (base prefix /usr), as the runner's is.

## Offline

`offline.sh` runs the same 95 files in a network namespace of their own, loopback alone, the database relayed in
over a unix socket (`relay.py`, `lo_up.py`): the same 2273 passed. test:core's "offline, no network" holds for them.

## CI against the records

verify.yml runs `pnpm verify` (ADR-011's sixteen stages, in order, as package.json writes them) then `pnpm prove`, on
ubuntu-latest's Python (no python-version, no .python-version file; CLAUDE.md:20 says so), with a pgvector/pgvector:pg17
service, Node 20 and Playwright's Chromium, in 30 minutes. PROGRESS.md's CI lines give verify 7 min 44 s to 13 min 43 s
and the proof 2 to 5 minutes there. Markers: no test is marked sim+live, lit+slow, sim+lit or slow+live; lit+live
holds one, which test:lit leaves out; test:core collects 3061 of 3236. What disagrees: the lock (H12-07).

## Tests that restate standins.py

`standin_restates.py` walks every test that leans on standins.py and marks each assert comparing against a value
the stand-ins make (`standin-restates.txt`). Those whose point is a stand-in's own value:

- test_proforma_shelf.py::test_the_stand_in_run_carries_every_table_and_says_it_is_the_stand_in, L125-127:
  tablesSource == PROFORMA_STANDIN, units R1/D302/U301, seven streams, the TEA lines summing to the price; every one is
  built by `_standin_ethanol_tables`, so the test holds that proforma.run relays the stand-in's tables.
- test_proforma.py::test_a_kept_reference_run_replays_through_its_registered_tool, L249: tablesSource ==
  PROFORMA_STANDIN (the rest of that test reads the code's own registration and replay).
- test_proforma_ethanol.py L219 and test_proforma.py L380: the TEA lines sum to the base price, an identity the
  stand-in builds in; on the real worker test_proforma_slow.py:48 holds it.

The other tests on the stand-ins (bindings, counts, refusals, ids, provenance) assert what the code computes from
them; the engine pins hash outputs computed through the code on stand-in inputs, which is their purpose.

## Left

test:sim, test:lit and verify whole (the brief); the TS guard scripts that need tsx (check-guild, check-state,
check-figures, check-reconcile-kinds).

## Running the scripts

H12's two worktrees are removed. `survivor.sh ID` and `probe_with.sh ID PROBE` make one of their own
(`$BH_WORK/H12/repro-wt`, 2047f5a with the scratch rename) when none stands; `seed_probe.sh WT` and `lock_drift.sh WT`
take a worktree; `pyver.sh` and `offline.sh` read `WT2`, `wtpytest.sh` and `mutate.py` read `WT` (each a worktree of
2047f5a with mutations/BASE-scratch-name.patch applied and test:core's generated fixtures copied in).
`spend_nan.sh` runs on the main tree's code over a database of its own. Every database is bh_h12_*, dropped after.
