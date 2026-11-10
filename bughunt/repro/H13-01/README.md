# H13-01: a keyless fresh clone following README's Run it gets no database

**Statement.** On a fresh clone with no key and no `core/.env`, README's Run it block stops at
`pnpm db:migrate` (no `OPENFERMENT_DATABASE_URL` is named), and `pnpm prototype:up` runs
`scripts/session-start.sh`, whose database step adds the development address only when `core/.env`
already exists, so the service starts, `/api/health` says ok, the app is served, and Home's
`GET` and `POST /api/projects` answer 503.

## The contract it breaks

- `scripts/session-start.sh:18-20`: "4. the database (ADR-001): when PostgreSQL answers on 127.0.0.1 and
  core/.env names none, the development address (compose.yaml's) joins core/.env; then pnpm db:migrate,
  whatever it exits with"
- `README.md:46-47`: "Without a key the app runs whole, and the steps that need a model say so."
- `README.md:41`: "pnpm db:up && pnpm db:migrate     # PostgreSQL 16 or later with pgvector; or name a server in core/.env"
  (the comment offers naming a server as the alternative to `db:up`; with `db:up`'s server, the block names none)

## Command

```
bash bughunt/repro/H13-01/run.sh
```

A scratch worktree at 2047f5a stands for the fresh clone (no `core/.env`, no key, the built `dist/`
linked in). PostgreSQL already answers on 127.0.0.1:5432 with compose.yaml's role, which is what
`pnpm db:up` starts, so `db:up` itself is not run. Step 0 runs README line 41's migrate entry point
in the clone. Step 1 runs the clone's `scripts/session-start.sh` whole with stand-ins for `pnpm` and
`uv` on PATH (install, sync and ready skipped; `db:migrate` resolves the address as
`migrations.main` does and connects to nothing), once with no `core/.env` and once with a placeholder
key line in it. Step 2 starts the service with prototype-up.sh's own uvicorn line and its own node
app server (read from the script) on 10500 and 10501. Step 3 is the control: the same service over a
fresh database `bh_r_h13_01_ctl` named in `OPENFERMENT_DATABASE_URL`, on 10502.

## Expected

With PostgreSQL answering on 127.0.0.1 and no `core/.env`, session-start's database step writes the
development address and `db:migrate` migrates it; the keyless app then runs whole: Home lists and
makes projects, as the control service does once an address is named (POST 201, GET 200).

## Observed (run1.log, run2.log)

- README line 41's `db:migrate`: exit 2, "refused: OPENFERMENT_DATABASE_URL is not set. Put it in core/.env: ...".
- session-start.sh with no `core/.env`: the database step writes nothing; `core/.env` stays absent and
  the step's `db:migrate` refuses in the same words. With a key line in `core/.env`, the same step adds
  `OPENFERMENT_DATABASE_URL` (one line).
- The service as prototype-up.sh starts it on that clone: `GET /api/health`
  `{"ok":true,...,"hasKey":false}` (prototype-up.sh's wait passes and it prints the address),
  `GET /` 200 through the app server, `GET /api/projects` 503 and `POST /api/projects` 503, each
  "OPENFERMENT_DATABASE_URL is not set. Put it in core/.env: ...".
- RESULT: DEFECT on both runs.

## Likely cause

- `scripts/session-start.sh:62`: `if [ -e core/.env ] && ! grep -q '^OPENFERMENT_DATABASE_URL=' core/.env && ...`:
  the `[ -e core/.env ]` term keeps the address from an absent file; the header (lines 18-20) counts
  an absent file as one that names none. Only step 1 (lines 28-43) makes
  `core/.env`, and it does so from a key alone.
- `README.md:39-42` names no step that writes the address for the `db:up` case before `db:migrate`.
- `core/openferment_core/db/engine.py:51-58` has no default address (by design, it refuses in words),
  and `core/openferment_core/api.py:467-487` reports `ok: true` with no database, so
  prototype-up.sh's health wait passes.

The refusal's own words name the line to put in `core/.env`, so a person who reads them has the
workaround.
