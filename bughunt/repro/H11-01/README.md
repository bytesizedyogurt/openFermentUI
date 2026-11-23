# H11-01: the example's placeholder key reads as a key at /api/health and the nightly's brief step

**Statement.** Over the `core/.env` that the live-host runbook's step 1 makes (the example with its
database line taken out, so `ANTHROPIC_API_KEY=sk-ant-...` stands on the key line), install.sh's
`has_key` and `pnpm ready` read the placeholder as no key, and GET /api/health answers `hasKey: true`
and the nightly's `checks brief --missing` takes its drafting branch, so the Postdoc screen hides its
no-key callout and the nightly asks the model for briefs on the placeholder.

**Contract.**

- `scripts/host/install.sh:54`: "core/.env holds no key yet. The app runs; Postdoc and extraction wait
  for one." (printed when `has_key` is false, which it is for the placeholder line)
- `scripts/host/nightly.sh:50-51`: "Each new check gets the model's brief while the key is there;
  without one the checks wait in the queue and an assessor can ask for a brief later."
- `core/openferment_core/api.py:471-472`: "`hasKey` lets the UI tell "the service is down" from "the
  service is up but has no key""
- `src/screens/Postdoc.tsx:144` shows the callout "Postdoc is running without an API key" on
  `health.ok && !health.hasKey` alone, and `src/screens/Postdoc.tsx:498` says "The Postdoc service
  answers on <model>" on `hasKey` true.

**Command** (from the repository root): `bash bughunt/repro/H11-01/run.sh`

It adds a detached worktree of 2047f5a under the scratch folder, runs step 1's block there verbatim
(`docs/runbooks/live-host-install.md:81-84`), and asks four doors about the worktree's `core/.env`, with
`ANTHROPIC_API_KEY` unset in the environment so each reads the file: `has_key` from the worktree's
`scripts/host/lib.sh`, `python -m openferment_core.ready --no-network --no-workers` (the key row),
`python -m openferment_core.checks brief --missing` over a fresh test database, and GET /api/health
from the worktree's service on 127.0.0.1:10260. It then empties the key line and asks the same four
doors again as a control. `ANTHROPIC_BASE_URL` and every proxy variable name closed loopback ports, so
no request leaves the machine; the only key value anywhere is the example's placeholder. The database,
the service and the worktree are removed at the end.

**Expected.** Every door reads the placeholder as no key: `has_key` false, ready's key row ✗, the brief
step prints "N check(s) without a brief; no key in core/.env, so they wait", and `hasKey` false, so the
Postdoc screen shows "Postdoc is running without an API key".

**Observed** (run1.log and run2.log, the same both times).

| door | step 1's core/.env (placeholder) | control (key line emptied) |
|---|---|---|
| install.sh's `has_key` | no key | no key |
| `pnpm ready` key row | ✗ "core/.env holds no key" | ✗ "core/.env holds no key" |
| `checks brief --missing` | prints nothing, exit 0: the drafting branch | "0 check(s) without a brief; no key in core/.env, so they wait" |
| GET /api/health | `hasKey: true` | `hasKey: false` |

The run's database holds no check, so it shows the branch alone. Read from the code
(`checks.py:667-676`), with a check waiting the drafting branch calls `brief()` once a check, each call
goes out on the placeholder and fails, and the step returns 1 when every one fails, so the night's
status turns to failure at the step whose comment says the checks wait.

**Likely cause** (confidence high). `core/openferment_core/api.py:488`
`hasKey=bool(os.environ.get("ANTHROPIC_API_KEY"))` and `core/openferment_core/checks.py:664`
`if not os.environ.get("ANTHROPIC_API_KEY"):` test that the variable is set and non-empty, and accept the
placeholder. `core/openferment_core/ready.py:52,81` (`PLACEHOLDER_KEY = "sk-ant-..."`,
`if not key or key == PLACEHOLDER_KEY`) and `scripts/host/lib.sh:89-93` (`has_key` refuses
`^ANTHROPIC_API_KEY=sk-ant-\.\.\.\s*$`) refuse it. One shared test (ready's `check_key` mark) at the
two Python doors would bring the four into one answer.

**Severity** S3: an edge case on the install path (the service started before the key is written)
with a workaround (write the key, or empty the line, and restart).
