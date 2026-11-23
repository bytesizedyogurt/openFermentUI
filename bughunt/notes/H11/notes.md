# H11: the host scripts

Commit 2047f5a (the scripts under `scripts/host/`, `scripts/session-start.sh`, `core/tests/test_host.py` and the
runbook are byte for byte as at the head of the hunt branch). Everything ran keyless under `bughunt/lib/env.sh`,
in a worktree of the hunt's own, on test databases named `bh_h11_*` (all dropped) and ports 8911 to 8913 (all
stopped). Each result is marked **run** (executed here: Linux, bash 5.2, GNU tools, stand-ins for macOS) or
**read** (reasoned against /bin/bash 3.2 and the BSD tools).

## How the scripts were run

`bughunt/notes/H11/scripts/standins.sh` writes stand-ins for `uname` (Darwin), `id` (uid 501, sean), `brew` (the keg's prefix),
`sudo` (runs the command, `install` without -o/-g), a stateful `launchctl` (bootout answers 3 for a job not
loaded), `pmset`, `fdesetup`, `plutil` (plistlib), `tailscale`, `pgrep`, `curl` (health), `pnpm`, `uv`, `node`,
the keg's `pg_isready`, `psql`, `createdb` and `pg_dump`, and the checkout's `core/.venv/bin/python` (launchd.py
on the real Python, every `-m openferment_core.*` answered). Each stand-in logs its call. `with-worktree.sh SCRIPT
[lib]` runs any script below against a fresh detached worktree of 2047f5a and removes it after; every candidate's
reproduction is one such command from the repository root.

## What held (run)

- `install-twice.sh`: install.sh twice, from a checkout path and a HOME each with a space. The second run changes
  nothing: the daemons folder, launchd's jobs, core/.env (one database line, mode 600) and HOME are equal; the
  only differences in the calls are the --read of the installed job and the temporary folder's name.
- `backup-rotation.sh`: seven and eight files, night by night across 31 October and 31 December, the same night
  twice, half a dump, /dev/full, other files in the folder, modes 700 and 600, a HOME with a space. The names sort
  as the dates do (ISO dates under LC_ALL=C). Also run with BASH_COMPAT=32.
- `dump-restore.sh`: the real pg_dump through backup_database (the name `openferment` mapped to bh_h11_live by a
  wrapper) and the runbook's restore with the real createdb and pg_restore: 44 tables, equal row counts.
- `env_setting_fuzz.py`: env_setting and python-dotenv agree on 645 forms except the comment's named forms, a `\n`
  escape in double quotes and a later bare name.
- `deploy-cases.sh`, `nightly-cases.sh`: refusals, flags, the tests' server, step order and statuses.
- ShellCheck 0.11.0 (`uvx --from shellcheck-py shellcheck -x -S style -o all`): clean at the default checks;
  `-o all` adds brace, `[[ ]]`, masked-status and default-case notes only.
- The runbook's commands, flags and paths all exist (see candidates.json, held).

## Findings

H11-01 the placeholder key (four doors, two answers); H11-02 OPENFERMENT_HOST widens the bind with one line of
notice and guard.py admits LAN writes; H11-03 an exported database URL leaves core/.env without one, so the live
service has no database while health and ready pass; H11-04 the dump's database is fixed at `openferment`;
H11-05 session-start glues its settings onto a last line with no newline (the key line); H11-06 session-start
misses `export` and spaced database lines; H11-07 the nightly dump test passes with the dump commented out;
H11-08 has_key reads every line, the service the last (owner question 13 is open on has_key); H11-09 an
exported CDPATH breaks REPO; H11-10 a stopped dump's .part stays for good; H11-11 a clock set back removes
tonight's dump at once.

## Read against bash 3.2 and BSD (read)

No associative arrays, `mapfile`, `${var,,}`, `&>>`, `local -n`, `printf -v`, negative substring offsets,
`sed -i`, `readlink -f`, `stat` or `date -d` in the host scripts. Process substitution, here-strings,
`${!name:-}`, `[[:space:]]` in patterns, `tail -1`, `tail -n +8`, `paste -sd: -`, `mktemp -d`, `date +%F`,
`cut`, `tr`, `awk '!seen[$0]++'` and `sort -r` hold on macOS. Two points stay open (suspected): `\s` in has_key's
BSD grep, and `$'\n'` inside a double-quoted `${//}` in deploy.sh on bash 3.2. Building bash 3.2.57 here was
refused by the sandbox, so neither ran.

## Scripts

All under `scripts/`: standins.sh, with-worktree.sh, install-twice.sh, backup-rotation.sh, dump-restore.sh,
killed-dump.sh, deploy-cases.sh, nightly-cases.sh, hollow-nightly-test.sh, wide-bind.sh, env-url-install.sh,
no-database-service.sh, placeholder-key-doors.sh, session-start-newline.sh, session-start-export.sh, cdpath.sh,
pipefail-grep-q.sh, env_setting_fuzz.py.
