# H11-11: a clock set back makes the night's rotation remove the dump it just made, and the night returns 0

**Statement.** `backup_database` in `scripts/host/lib.sh` keeps the seven dump names that sort last, so a
dump made while the Mac's date reads earlier than every kept file sorts first and is removed at once, with
"openferment dumped into ..." and "... removed: the newest 7 are kept" both in the log and status 0.

**Contract.** `scripts/host/lib.sh:168-170` (at 2047f5a): "The night's dump (the alpha 2.2 prompt §3):
`pg_dump openferment` on 127.0.0.1, as the owner, into ~/openferment-backups/, one file a day named by its
date, the newest seven kept." The same rule stands in `scripts/host/nightly.sh:5` "the database's dump into
~/openferment-backups/ (the newest seven kept)" and in `docs/runbooks/live-host-install.md:260` "and the
newest seven are kept". The rotation's own comment, `scripts/host/lib.sh:195`, names the assumption it rests
on: "A file a day, named by its date, so the names sort as the days do". The dump a night makes is the newest
dump in the folder, and the night says it was made.

**Command.** From the repository root: `bash bughunt/repro/H11-11/run.sh`

It runs `backup_database` from a detached worktree of 2047f5a, in a scratch HOME, with a `date +%F` stand-in
and a `pg_dump` stand-in that calls the real `/usr/bin/pg_dump` on a fresh migrated test database
(`bh_r_h11_11_dump`), so every dump is a real custom-format dump. Seven nights 2027-01-06 to 2027-01-12, a
control night 2027-01-13, then two nights with the clock a year back, 2026-01-14 and 2026-01-15. Nothing is
left behind: the worktree, the scratch folder and the database go at the end.

**Expected.** After a night that prints "openferment dumped into <file>" and returns 0, <file> is in
`~/openferment-backups`; a night that cannot keep its dump says so in words and returns non-zero.

**Observed** (run1.log and run2.log, the same both times). The control night holds the rule: 2027-01-13 is
kept and 2027-01-06 removed. On the night the clock reads 2026-01-14:

    openferment dumped into ~/openferment-backups/openferment-2026-01-14.dump
    openferment-2026-01-14.dump removed: the newest 7 are kept

status 0, and the folder holds 2027-01-07 to 2027-01-13 alone. The next night, 2026-01-15, does the same. So
every night until the clock passes the oldest kept name loses its own dump, `nightly.sh`'s dump step reports
success, and the newest copy of the database stays the one made before the clock went back.

**Likely cause.** `scripts/host/lib.sh:197-203`: the removal list is every `openferment-YYYY-MM-DD.dump`
sorted by name, descending, past the seventh (`LC_ALL=C sort -r | tail -n +$((keep + 1))`), and the file
just moved into place at `scripts/host/lib.sh:193` is among the candidates. Ranking by name equals ranking by
age only while the clock never runs back. A small fix keeps `$file` out of the removal list (or fails the
night in words when it lands there).

**Severity.** S3: an edge case (a clock set back by eight days or more) with a workaround (set the clock
right; the seven older dumps stay). A Mac keeps its time by network, so the case needs a wrong clock. The
candidate's own grade was S4; the night's backup is lost while the log says it was made, which is beyond
wording.
