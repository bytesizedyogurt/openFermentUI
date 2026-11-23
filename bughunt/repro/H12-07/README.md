# H12-07: CI never holds core/uv.lock

**Statement.** `.github/workflows/verify.yml` runs no `uv sync --frozen|--locked` and no `uv lock --check`, and
every Python stage of `pnpm verify` it runs calls `uv run --all-extras` with neither `--frozen` nor `--locked`, so a
commit whose `core/uv.lock` no longer matches `core/pyproject.toml` has its lock re-resolved, rewritten and installed
in CI, passes, and leaves the committed lock pinning a version `pyproject.toml` excludes and CI never ran.

**Contract.**
- `CLAUDE.md:40` (R): "BioSTEAM 2.54.0, thermosteam 0.54.2 and biorefineries 2.35.1 are pinned in `core/uv.lock`".
- `CLAUDE.md:20` (C): "Install: `pnpm install --frozen-lockfile`, then `cd core && uv sync --frozen --all-extras`".
- `scripts/host/deploy.sh:80-82`, the same gate on the live host: "The gate's own `uv run` calls read core/uv.lock as
  committed, as the sync above does, so a newer uv leaves the tracked lock as it stands." / `UV_FROZEN=1 pnpm verify`.
- `.github/workflows/verify.yml:17-19`: "`uv run` without `--extra dev` falls through to whatever `pytest` happens to
  be on PATH, outside the project venv; `test:core` asks for the extra so the locked one is used."
- `.github/workflows/verify.yml:68` holds the JavaScript lock: `pnpm install --frozen-lockfile`.

**Command.** `bash bughunt/repro/H12-07/run.sh` (from the repository root; about 15 s; offline, uv's cache alone).

In a worktree of 2047f5a with a venv of its own made by CLAUDE.md:20's install, the script makes the commit a person
makes when they edit `core/pyproject.toml` and leave the lock: `"alembic>=1.13"` becomes `"alembic>=1.13,<1.20"`,
`core/uv.lock` still pinning alembic 1.20.1. It then runs the holding steps CI lacks, test:core's own command
(package.json:24) on `tests/test_db.py` (the migrations' tests, alembic's), prove's `uv run --frozen` form, and
CLAUDE.md:20's frozen install on the commit as pushed. The repository's own `core/.venv` is read alone, and its alembic
stays 1.20.1.

**Expected.** CI fails a commit whose `core/uv.lock` no longer matches `core/pyproject.toml`, as it fails a stale
`pnpm-lock.yaml`, through a step such as `uv lock --check` or `uv sync --locked --all-extras`; and verify's stages
run on the versions the committed lock pins, the ones CLAUDE.md:20's frozen install installs, as deploy.sh runs the
same gate with `UV_FROZEN=1`.

**Observed (both runs).**
- verify.yml holds the Python lock on 0 lines; 7 of verify's `uv run` stages (gen:api, gen:components, test:core,
  test:sim, test:lit, check:licences, check:tools) carry neither `--frozen` nor `--locked`.
- `uv lock --check`: exit 1; `uv sync --locked --all-extras`: exit 1 ("The lockfile at `uv.lock` needs to be
  updated").
- test:core's form, `uv run --all-extras pytest tests/test_db.py -m "not live and not sim and not slow and not lit"`:
  exit 0, 24 passed, after rewriting `core/uv.lock` (4 insertions, 4 deletions: alembic 1.20.1 to 1.19.1) and
  installing alembic 1.19.1.
- prove's form, `uv run --frozen --all-extras`, then runs on alembic 1.19.1: it reads the lock verify's stages left.
- CLAUDE.md:20's install on the commit as pushed (`uv sync --frozen --all-extras`, the committed lock) installs
  alembic 1.20.1, which `pyproject.toml` (`>=1.13,<1.20`) excludes and no CI stage ran.

**Likely cause.** `.github/workflows/verify.yml:63-79`: `astral-sh/setup-uv@v5`, then `pnpm install --frozen-lockfile`
(line 68) and `pnpm verify` (line 79), with no `uv sync --locked` or `uv lock --check` step and no `UV_FROZEN` or
`UV_LOCKED` in the job's `env` (lines 44-51); and `package.json:15,16,18,19,24,25,30` (check:licences, check:tools, gen:api,
gen:components, test:core, test:lit, test:sim) call `uv run --all-extras`, which locks and syncs before it runs. The fix
is small: a `cd core && uv sync --locked --all-extras` step before `pnpm verify` (or `uv lock --check`), with
`UV_FROZEN: '1'` in the job's env as deploy.sh sets it.
