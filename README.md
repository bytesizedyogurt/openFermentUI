# openFerment

**Interim (alpha 2.0 foundation build).** The alpha 1.0 README is at
`docs/history/README-2026-10-21.md`; stage 8 of the build writes this file's replacement.

- Where the build stands and how to resume it: [`docs/PROGRESS.md`](docs/PROGRESS.md).
- The decisions it follows: [`docs/decisions/`](docs/decisions/) (`ADR-000` to `ADR-012`).
- Working guidance for a session: [`CLAUDE.md`](CLAUDE.md).

## Run

```
pnpm install --frozen-lockfile
cd core && uv sync --all-extras && cd ..
pnpm test:core       # offline
pnpm test:sim        # the BioSTEAM worker
pnpm typecheck && pnpm build
```

The service binds `127.0.0.1`. The app ships with no scientific content: documents arrive
through Intake.
