# H12-09: no guard test can tell a public .net name from the owner's own names

**Statement.** A guard that answers to every `.net` name (the hunt's M32 at `guard.py:78`) passes every guard test,
since each hostile Host the tests send ends in `.com`, `.org` or `.example` and none in `.net`, and under that guard a
rebound name such as `rebind.evil.example.net` makes a project.

**Contract.** `core/openferment_core/guard.py:22-26`:

> A host this service answers to: an IP address, a name with no dot, a `.local` name (Bonjour), a `.ts.net` name
> (Tailscale's names for the owner's devices), or one listed in OPENFERMENT_ALLOWED_HOSTS. Each of these is answered
> by the owner's own network or by Tailscale; a rebinding attack needs a public domain whose DNS the attacker
> answers, and none of these is one.

The tests that hold it are `core/tests/test_request_guard.py` (the guard's own file, "Only the owner's own pages may
change anything") and the key override's refusal in `core/tests/test_key_override.py:127-134`.

**Command** (from the repository root; exits 0 either way):

    bash bughunt/repro/H12-09/run.sh

In a worktree of 2047f5a of its own, the script:

1. scans every test file in `core/tests` by ast for each Host a test sends that the head's guard refuses (`scan.py`);
2. probes the head (`probe.py`, on the fresh database `bh_r_h12_09_head`): `guard.refusal` and
   `POST /api/projects` with Host and Origin `rebind.evil.example.net:8000`, as after a DNS rebinding;
3. applies a control (`control.patch`: the line answers to every `.com` name) and runs `test_request_guard.py`;
4. applies the mutation (`mutation.patch`, the hunt's M32: the line answers to every `.net` name) and runs the
   candidate's three files, `test_request_guard.py`, `test_key_override.py` and `test_projects.py`;
5. probes the mutated tree (fresh database `bh_r_h12_09_mut`).

The tests' session databases take the prefix `bh_r_h12_09_t`; every `bh_r_h12_09_*` database is dropped and the
worktree removed at the end.

**Expected.** A guard test sends a public name outside `.local`, `.localhost` and `.ts.net` that ends in `.net` (such
as `rebind.evil.example.net`) and asserts a 403, so a guard that answers to every `.net` name fails a test, as the
control's `.com` guard does.

**Observed** (run1.log and run2.log alike):

- The tests send six Hosts the head refuses: `rebind.evil.example.com` four times (`test_request_guard.py:38, 73,
  115, 165`), `openferment.example.org` once (`:120`) and `evil.example` once (`test_key_override.py:131`). Zero of
  them end in `.net`; the only `.net` Hosts in the tests are `mini.tail1234.ts.net` (`:52, 62, 95`), which the guard
  answers to.
- The head refuses `rebind.evil.example.net`: 403, and the database holds no project after it.
- The control's `.com` guard fails two tests (`test_a_rebound_hostile_name_is_refused`,
  `test_a_forwarded_name_cannot_launder_a_hostile_host`), so the run exercises the worktree's guard.
- The `.net` guard (M32): `58 passed`, pytest exit 0.
- Under it, `POST /api/projects` with Host and Origin `rebind.evil.example.net:8000` answers 201, and the project
  `made-through-a-rebound-name` stands in the database.

RESULT: DEFECT in both runs.

**Likely cause.** `core/tests/test_request_guard.py:30-77` names one hostile public domain,
`rebind.evil.example.com` (`:38`, `:73`), and the listed-name test at `:119-123` refuses `openferment.example.org`
before it is listed; `core/tests/test_key_override.py:131` sends `evil.example`. No refused Host ends in `.net`, the
top-level label the `.ts.net` suffix shares, so the boundary the contract draws at `.ts.net` goes untested and the
suffix check at `core/openferment_core/guard.py:78` (`host.endswith(OWN_SUFFIXES)`) can widen to every `.net` name
unseen. One parametrized refusal of `rebind.evil.example.net` (and of a name such as `evilts.net` that ends in
`ts.net` without its dot) beside `:38` closes it.

**Severity.** S4: the guard on the tree refuses the name today; the gap is a test that cannot catch a break of the
loopback guard's suffix boundary.
