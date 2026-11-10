# H11-02: OPENFERMENT_HOST at install widens the server's bind, and guard.py admits a LAN Host

**Statement (the candidate's).** `scripts/host/install.sh` takes `OPENFERMENT_HOST` from the environment and writes
it into the server's LaunchDaemon, so `OPENFERMENT_HOST=0.0.0.0` installs a service listening on every interface with
one line of notice, and `guard.refusal` allows a POST that names the Mini's LAN address in `Host`.

**Verdict: not reproduced (RESULT: NO-DEFECT in both runs).** The mechanics hold exactly as the candidate says. The
tree records them as the install's explicit opt-in, held by a test, with loopback the default and a reinstall
returning to it, so the behaviour is the designed one. See "Why NO-DEFECT" below.

## Contract the candidate cites

- `CLAUDE.md:52`: "R: The service binds `127.0.0.1`; the loopback bind and `core/openferment_core/guard.py` are the
  access control until accounts exist (§7.6, §11.5)."
- `CLAUDE.md:137`, under "Stop conditions (ask the owner first; execution prompt §11.1)": "R: Widening network
  exposure or weakening `core/openferment_core/guard.py`; the service keeps its loopback bind."
- `docs/runbooks/live-host-install.md:146-147`: "The service binds `127.0.0.1` and nothing else; `tailscale serve`
  is how your phone and laptop reach it".

## What the tree records about the knob

- `scripts/host/lib.sh:37-39`: "install.sh only. The host is what OPENFERMENT_HOST says this time, else loopback;
  never what an earlier install was given, because listening wider than loopback is a choice made each time, never a
  default that lingers."
- `core/tests/test_host.py:160-170`, `test_a_reinstall_never_keeps_a_wide_host_unasked`, parametrized
  `[(None, "127.0.0.1"), ("0.0.0.0", "0.0.0.0")]`: the wide address when asked is the tested outcome.
- `docs/PROGRESS.md:3432-3435` (alpha 2.2 G), under "Left for the owner": "`OPENFERMENT_HOST` stays an install's
  explicit choice, default loopback."
- `docs/history/CLAUDE-2026-10-21.md:261-264` (alpha 1.0, no authority, the ancestor of CLAUDE.md:52): "The server
  binds to `127.0.0.1` ... Widening it (`OPENFERMENT_HOST`) is a decision for [the owner], never a default."
- `core/openferment_core/guard.py:3-6` and `:22-26`: the guard is for two browser tricks (a cross-site request and
  DNS rebinding) and counts on the bind for who can reach the service; it answers to "an IP address, a name with no
  dot, a `.local` name (Bonjour), a `.ts.net` name ... or one listed in OPENFERMENT_ALLOWED_HOSTS".

## Command

From the repository root: `bash bughunt/repro/H11-02/run.sh`

It runs `install.sh` unchanged in a detached worktree of 2047f5a, on Linux, over stand-ins for macOS and Homebrew (the
hunt's `standins.sh` set, written inline). Three installs: A, a first install with `OPENFERMENT_HOST` unset; then
`install.sh --uninstall`; B, an install with `OPENFERMENT_HOST=0.0.0.0`; C, a reinstall with it unset. It reads each
installed server plist with `plistlib`. Then it starts the real service on 127.0.0.1:9070 over a fresh test database
`bh_r_h11_02_svc` and sends three POSTs to `/api/projects` with no Origin, naming in `Host` a LAN address, a `.local`
name and a public domain. Last it prints the record lines above from the worktree. It cleans up the service, the
database, its data copy and the worktree.

## Expected

The candidate's expectation: the installed server job listens on 127.0.0.1, or install.sh stops and asks before it
writes a wider address.

The verdict rule run.sh applies, from the tree's own record: DEFECT when a wider address reaches the job with
`OPENFERMENT_HOST` unset (install A or reinstall C), or when the knob is nowhere recorded as the install's explicit
choice.

## Observed (both runs, run1.log and run2.log)

- A, `OPENFERMENT_HOST` unset: install.sh exit 0; the job's `--host --port`: `127.0.0.1 8000`.
- B, `OPENFERMENT_HOST=0.0.0.0` (after `--uninstall`, so no job is installed): exit 0; `0.0.0.0 8000`; the one line
  install.sh prints on the address: "The server listens on 0.0.0.0:8000 (OPENFERMENT_HOST), so Tailscale is left
  alone." Its closing block still says "On this Mac: http://127.0.0.1:8000".
- C, reinstall after B with the variable unset: exit 0; `127.0.0.1 8000`, and install.sh says "The server listened
  on 0.0.0.0 and will now listen on 127.0.0.1. Set OPENFERMENT_HOST to choose otherwise."
- The service: `Host: 192.168.1.20:8000` 201, `Host: mini.local:8000` 201, `Host: attacker.example.com:8000` 403
  "this service does not answer to 'attacker.example.com'. Add the name to OPENFERMENT_ALLOWED_HOSTS if it is yours".
- The record lines are present (lib.sh:37-39, test_host.py:160, PROGRESS.md:3432-3435); the live-host runbook names
  `OPENFERMENT_HOST` on 0 lines.

## Likely cause of the mechanics (as the candidate named them, checked)

- `scripts/host/lib.sh:41`: `HOST="${OPENFERMENT_HOST:-127.0.0.1}"` in `install_address`, called at
  `scripts/host/install.sh:39`.
- `scripts/host/install.sh:79-81`: `launchd.py ... --host "$HOST" --port "$PORT"`.
- `scripts/host/launchd.py:57-62`: the paths, the user and the port are checked; the host goes into
  `ProgramArguments` as given (`:84-85`).
- `core/openferment_core/guard.py:68-78`, `answers_to`: every IP address and `.local` name is a host it answers to,
  and `refusal` (`:109-136`) admits a write with no Origin from such a host.

## Why NO-DEFECT

- The wider address reaches the job only when the person installing sets `OPENFERMENT_HOST` that time. A first
  install without it writes loopback, and a reinstall without it returns to loopback with a line saying so (A, C).
  Only `lib.sh`, `install.sh` and `test_host.py` name the variable, and nothing in the tree sets it or tells anyone
  to export it, so a value in the installing shell is one the person put there.
- CLAUDE.md:137 is a stop condition on the builder: it lists what the agent asks the owner before doing. The owner
  setting `OPENFERMENT_HOST` at install is that decision made by the owner. The alpha 1.0 line that CLAUDE.md:52
  descends from states the loopback bind and this knob side by side, and alpha 2.2 G kept the knob knowingly and
  listed it under "Left for the owner" (PROGRESS.md:3432-3435), with `test_host.py:160` holding `0.0.0.0` as the
  outcome when asked.
- guard.py admitting an IP address or a `.local` name is its documented rule (`guard.py:22-26`), and its docstring
  puts reach on the bind (`guard.py:3-4`: "Bound to loopback and published by `tailscale serve`, only the owner's own
  devices reach it"). The 403 for a public domain shows the guard doing the job it states.
- What remains is wording: the runbook's "binds `127.0.0.1` and nothing else" and CLAUDE.md:52 name no opt-in, and
  the runbook names `OPENFERMENT_HOST` nowhere. That is drift at S4, a matter for the owner's open item in
  PROGRESS.md.
