# H11-10: a night's dump stopped half way leaves its .part file in the backups folder for good

**Statement.** When the nightly job is stopped by SIGTERM while `pg_dump` runs (launchd stopping the job, or a
restart, which signals the job's process group), bash ends before `backup_database` reaches its
`rm -f "$file.part"`, and the rotation's glob names only `openferment-YYYY-MM-DD.dump`, so each stopped night
leaves its `openferment-<date>.dump.part` in `~/openferment-backups/`, and no later night removes it.

**Contract.**

- `scripts/host/lib.sh:172-173`: "The dump is written beside its name and moved into place once whole, so a
  failed night keeps the seven as they were."
- `scripts/host/lib.sh:188-189`: the failure path itself removes the half file:
  `if ! (umask 077 && "$tool" ... --file="$file.part" openferment); then` / `rm -f "$file.part"`.
- `core/tests/test_host.py:344`, the project's reading of that promise for a failed night:
  `assert sorted(p.name for p in backups.iterdir()) == before, "no half file, and nothing rotated away"`.
- `docs/runbooks/live-host-install.md:260`: "... into `~/openferment-backups/openferment-<date>.dump`, ... and
  the newest seven are kept".

The words of lib.sh:172-173 and the runbook hold for the seven dated dumps: the stopped night loses none of
them. The broken part is the failure path's own promise of no half file (lib.sh:189, test_host.py:344), which a
signal to the night's process group bypasses.

**Command.** From the repository root: `bash bughunt/repro/H11-10/run.sh`

It makes a fresh test database `bh_r_h11_10_dump` (bh_db_fresh), adds a detached worktree of 2047f5a under
`$BH_WORK/H11-10/wt`, and runs `backup_database` from that worktree's `scripts/host/lib.sh` the way
`nightly.sh`'s first step calls it, in a process group of its own, with HOME a scratch folder. The real
`/usr/bin/pg_dump` (PostgreSQL 16.15) dumps the test database; the only stand-ins are `date +%F` (each
night's date) and a wrapper that swaps the database name `openferment` for the test database. The folder
starts with seven dumps dated 2026-11-03 to 2026-11-09. For night 2026-11-10, a second session holds an
ACCESS EXCLUSIVE lock on one table, so the real `pg_dump` has opened its `.part` and waits; the night's
process group is then sent SIGTERM. Three ordinary nights follow (2026-11-11 to 2026-11-13). The script
then stops everything, drops the database and removes the worktree.

**Expected.** The stopped night leaves no `.part`, or a later night clears it: after the stopped night and
three ordinary nights, the folder holds the newest seven `openferment-<date>.dump` files and nothing else.

**Observed (run1.log and run2.log alike).**

```
night 2026-11-10: exit 143; the night's log: pg_dump: terminated by user
night 2026-11-10: folder: openferment-2026-11-03.dump ... openferment-2026-11-09.dump openferment-2026-11-10.dump.part
night 2026-11-11: exit 0; ... openferment-2026-11-03.dump removed: the newest 7 are kept
night 2026-11-13: folder: openferment-2026-11-06.dump openferment-2026-11-07.dump openferment-2026-11-08.dump
  openferment-2026-11-09.dump openferment-2026-11-10.dump.part openferment-2026-11-11.dump
  openferment-2026-11-12.dump openferment-2026-11-13.dump
RESULT: DEFECT
```

Each ordinary night makes a whole dump (`pg_restore --list` reads all three) and rotates away the oldest
dated dump, and the stopped night's `.part` stays through all three. Here the `.part` is 0 bytes, since the
lock stops `pg_dump` before it writes; the custom format writes the file in its closing phase, so a stop
during the data phase of a larger database leaves a partial file of up to a dump's size (an inference from
the format; this run does not measure it). A retry on the same date overwrites and moves the `.part`; the 03:00 job's
next run is a later date, so that path does not clear it.

**Likely cause.** `scripts/host/lib.sh:188-191`: the `.part` is removed only on `pg_dump`'s own failure
return, with no `trap` for TERM or INT and no sweep of earlier `.part` files at the start of a night;
`scripts/host/lib.sh:197`: the rotation's glob `openferment-[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].dump`
never names a `.part`. A trap alone misses SIGKILL (launchd's follow-up after its exit timeout), so a sweep
of stale `.part` files before the night's dump covers both.

**Severity.** S4: no kept dump is lost and every whole dump stays readable; the effect is a stray half file
(mode 600, in the owner's folder) per stopped night, which grows the folder and is removed by hand.
