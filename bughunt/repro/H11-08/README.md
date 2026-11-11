# H11-08: has_key reads every key line of core/.env, and the service reads the last one

**Statement.** `has_key` (scripts/host/lib.sh) answers true when some line of core/.env starts
`ANTHROPIC_API_KEY=sk-ant-` and no line is the example's placeholder, while python-dotenv, which the service
and `pnpm ready` read core/.env with, keeps the file's last `ANTHROPIC_API_KEY` line; so on a core/.env with
two key lines install.sh's message and `pnpm ready`'s key row (and the service's `hasKey`) give opposite
answers.

**Contract.**

- `scripts/host/lib.sh:88`: "True when core/.env holds something shaped like a real key. Never prints it."
  File B below holds a key-shaped line, and `has_key` answers false for it.
- `core/openferment_core/api.py:178` (`load_dotenv(Path(__file__).parent.parent / ".env", override=False)`)
  and `core/openferment_core/ready.py:638` (`load_dotenv(CORE / ".env", override=False)`): the service and
  `pnpm ready` take core/.env through python-dotenv, whose last line for a name wins; `api.py:488`
  (`hasKey=bool(os.environ.get("ANTHROPIC_API_KEY"))`) and `ready.py:79-86` (`check_key`) answer from that value.
- `scripts/host/lib.sh:96-98` records the same reading for every other setting: "the file's last line for it,
  in the forms of python-dotenv these settings take".
- `scripts/host/install.sh:51-56` prints `has_key`'s answer as "core/.env holds a key." or "core/.env holds
  no key yet ...".

**Command** (from the repository root):

    bash bughunt/repro/H11-08/run.sh

It makes a scratch worktree of 2047f5a under `$BH_WORK/H11-08/wt`, a fresh test database `bh_r_h11_08_svc`,
and writes three made-up core/.env files into the worktree in turn (A one key line; B the placeholder line,
then a key line; C a key line, then an empty one). For each it asks three doors: install.sh's own
`if has_key` block over the worktree's lib.sh; `python -m openferment_core.ready --no-network --no-workers`'s key
row; and `GET /api/health`'s `hasKey` from the service started in the worktree's core/ on 127.0.0.1:10070.
`ANTHROPIC_API_KEY` is unset in those processes so core/.env's line is the one read, and `ANTHROPIC_BASE_URL`
points at a closed loopback port. Everything is removed after.

**Expected.** For one file the three doors give one answer: install.sh says a key is held exactly when
`pnpm ready`'s key row and the service's `hasKey` do.

**Observed** (run1.log, run2.log, both `RESULT: DEFECT`):

| file | install.sh (`has_key`) | `pnpm ready` key row | service `hasKey` |
|---|---|---|---|
| A one key line (control) | key: "core/.env holds a key." | ✓ key | True |
| B placeholder line, then a key line | no key: "core/.env holds no key yet ..." | ✓ key | True |
| C a key line, then an empty one | key: "core/.env holds a key." | ✗ key "core/.env holds no key" | False |

On B, install.sh tells the person to write a key the service already serves on; on C, install.sh says a key is
held and the service starts with none (the Postdoc screen shows its no-key warning).

**Likely cause.** `scripts/host/lib.sh:90-92`: two `grep -qE` calls over every line of the file, one
asking for any `^ANTHROPIC_API_KEY=sk-ant-` line and one refusing when any line is the placeholder, with no
step that picks the file's last `ANTHROPIC_API_KEY` line as `env_setting` (lib.sh:95 onward) does for the other
names. Confidence: high.

**Scope.** The runbook (`docs/runbooks/live-host-install.md:86`) and install.sh's own words ask for "the one
line of that name", so a file with two key lines lies off the documented path; a person who appends a key
line under the example's placeholder (file B) meets it. Owner question 13 (docs/PROGRESS.md:669) asks how
`has_key` reads the key line (`\s`, quoted and `export` forms), and a change to how a key is read is a stop
condition; this facet, which of several lines counts, sits outside the question's wording and would join it.
Severity S4: a message at install disagrees with the service, and `pnpm ready`, which install.sh runs after,
gives the answer the service holds (install.sh:123).
