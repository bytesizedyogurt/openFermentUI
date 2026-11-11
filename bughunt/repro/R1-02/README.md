# R1-02: a Departures row says no store holds a protocol, and the store has kept protocols since E.12a

**Statement.** The Departures row "alpha 2.2 D7, C.5" in `docs/PROGRESS.md` (line 467 at 2047f5a) still gives
"No store holds a protocol in this build" as the reason for the bench's readings-alone mode; since E.12a
(37addaf) migration 0010 makes the `protocols` table and the service keeps and serves a project's protocols at
`/api/protocols`, and the same table's row "alpha 2.2 §6.5, E.12" (line 503) says so.

**Contract.**
- `docs/PROGRESS.md:503` (the same Departures table): "A project keeps its protocols on the service since E.12a
  (ADR-017), and the protocol screens, Guild's Matrix and skills, Primer's path and the bench read them".
- `docs/PROGRESS.md:435` (Decisions, ADR-016): "alpha 2.2 E.12a: its first revisit condition met by ADR-017, the
  readings-alone mode standing beside a protocol's steps".
- `docs/decisions/ADR-016-bench-readings-alone.md:51-55`: "Implementation note (alpha 2.2 E.12a) ... a project keeps
  its protocols, and a deposition opened from a kept protocol walks its steps."
- `CLAUDE.md:82`: "A project keeps its protocols, made once and each version kept as it was kept ... (ADR-017)";
  `CLAUDE.md:149`: "`docs/PROGRESS.md` holds the log of every stage, the departures, the debts and the blockers".
- The row itself, `docs/PROGRESS.md:467`: "No store holds a protocol in this build, and D7's walk deposits a reading
  at the bench on step 5's locked runbook."

**Command.** `bash bughunt/repro/R1-02/run.sh` from the repository root. It reads `docs/PROGRESS.md`, ADR-016,
migration 0010 and `docs/api/openapi.json` at 2047f5a; then it makes a fresh database `bh_r_r1_02_store`, starts the
service over it on 127.0.0.1:10940, keeps one placeholder protocol with `POST /api/protocols`, reads it back from
`GET /api/protocols` and from the `openferment.protocols` table, stops the service and drops the database.

**Expected.** The row's reason holds for the tree at 2047f5a, or the row carries an E.12a note as the Decisions row
of ADR-016 and ADR-016's own note do: the readings-alone mode stands beside a project's protocols (ADR-017).

**Observed.** Both runs: line 467, under "## Departures from the execution prompt", says "No store holds a protocol
in this build" and names no step after C.7 (no E.12a, E.12 or ADR-017 in the row); line 503 of the same table says a
project keeps its protocols on the service since E.12a; the Decisions row (435) and ADR-016:51 carry the E.12a note.
On a freshly migrated database the store holds `openferment.protocols`, `POST /api/protocols` answers 200 with the
protocol kept by Ada, `GET /api/protocols` lists `[PR-PLACEHOLDER]`, and the table holds one row. `RESULT: DEFECT`
in `run1.log` and `run2.log`.

**Likely cause.** E.12a (37addaf) wrote migration 0010
(`core/openferment_core/db/alembic/versions/0010_protocols.py:28`, `op.create_table('protocols', ...)`), the four
routes (`core/openferment_core/api.py:1218-1269`), the Decisions row (`docs/PROGRESS.md:435`) and ADR-016's
implementation note (`docs/decisions/ADR-016-bench-readings-alone.md:51`), and left the Departures row's Why
(`docs/PROGRESS.md:467`) as C.7 (1243e81) last wrote it. ADR-016:17 and ADR-006:225 carry the same sentence inside
dated C.5 text, ADR-016 with its later note beside it.

**Severity.** S4 (drift in a record; no behaviour changes). Fix size: small, one clause in one row.
