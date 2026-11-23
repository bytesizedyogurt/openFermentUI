# bughunt/

The working folder of the bug hunt on alpha 2.2 (November 2026), run at commit `2047f5a`, the head of
`claude/alpha-2-2-base`. The report is `docs/reports/bug-hunt-2026-11.md`.

- `lib/env.sh`: source it for a keyless shell. `bh_env` runs a command with the key and the cloud
  session's model pins unset; `bh_db_fresh` and `bh_db_drop` make and drop test databases named `bh_*`;
  `bh_svc_start` and `bh_svc_stop` start and stop the service on a loopback port over such a database;
  `bh_project` makes a project through the API.
- `lib/ledger.py`: builds `coverage.csv` from the tree (`init`) and fills it from each hunt's
  `notes/<hunt>/coverage.jsonl` (`merge`).
- `coverage.csv`: one row for every file changed in `112eb8b..2047f5a`, every operation in
  `docs/api/openapi.json`, every tool in `docs/TOOLS.md`, every rail entry and screen, and every
  registered engine, with the hunt that examined it, how, and the findings it produced.
- `notes/<hunt>/`: each hunt's notes, scripts, coverage lines and candidates.
- `repro/<id>/`: one reproduction a finding: `run.sh` (one command from the repository root),
  `README.md` (statement, contract, expected, observed, cause), and the two runs' logs.

Every run here is keyless and spends nothing; every database it makes is a test database, dropped after.
Nothing under `core/`, `src/`, `scripts/` or `examples/` is changed.
