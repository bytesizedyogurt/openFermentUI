# H12-15: the IPv4-mapped rule of the import-url check under Python 3.13

**Statement (the candidate's).** Dropping the IPv4-mapped reading (`seen = _v4(address)`) from
`refused_class` passes `test_sff_url.py` and `test_collectors.py` on Python 3.13.17, where
`ipaddress` reads `::ffff:127.0.0.1` as loopback itself, and fails four tests on Python 3.12.3, so
the container's gate holds less than CI's.

**Verdict: NO-DEFECT, twice.** The test counts reproduce exactly. On 3.13.17 the mutant is an
equivalent mutant: across 231,072 IPv4-mapped addresses `refused_class` gives the same words with the
line and without it, because every `IPv6Address` property it reads there defers to `ipv4_mapped`
(`is_site_local` is the one exception, and no mapped address holds it in either form). So on 3.13.17
the line changes nothing a test could see. It does its work only on 3.12.3, where the four tests
catch it, and 3.12.3 is the Python CI runs.

## Contract the candidate names

- `core/openferment_core/literature/collectors.py:284-286` (at 2047f5a), the `refused_class`
  docstring: "Why a fetch by address does not connect to `address`, in words, or None for a public
  address. An IPv4-mapped IPv6 address is read as its IPv4 address."
- `CLAUDE.md:20`: "this container runs Python 3.13.17, and CI the Python its runner holds
  (`setup-uv` names none; 3.12.3 at the close)."

Both are met. The docstring's rule holds on 3.13.17 with the line dropped, because the standard
library reads a mapped address as its IPv4 address on every property that matters. `CLAUDE.md:20`
says which Python each place runs. It makes no promise that the container's gate sees every break
CI sees.

## Command

```
bash bughunt/repro/H12-15/run.sh
```

From the repository root. It makes the test database prefix `bh_r_h12_15_gate` fresh, adds a
detached worktree of 2047f5a under `$BH_WORK/H12-15/`, and then:

1. runs the four IPv4-mapped cases of `test_sff_url.py` (`-k ffff`) on the kept tree under 3.12.3
   and 3.13.17, and runs `probe.py` on each Python, which writes `refused_class`'s answer for 231,072
   mapped addresses (each /16's first and last address and 100,000 more from seed 0) and says which
   `IPv6Address` properties defer to `ipv4_mapped` on that Python;
2. applies `M57.patch` (collectors.py:287 `seen = _v4(address)` becomes `seen = address`);
3. runs `test_sff_url.py` and `test_collectors.py` under both Pythons, and the probe again;
4. counts the failures and the answers that moved, prints EXPECTED, OBSERVED and RESULT, then
   removes the worktree and drops every `bh_r_h12_15_*` database.

RESULT is DEFECT when the mutant passes on 3.13.17 while it changes some answer there (a real break
the container's gate misses), or when it passes on 3.12.3 while it changes answers there. Each run
takes about 40 s.

## Expected (the candidate's claim)

With M57 applied, the tests fail on 3.12.3 and pass on 3.13.17, while `refused_class` answers some
mapped address in other words on 3.13.17.

## Observed (run1.log and run2.log agree)

- Kept tree: the four mapped cases pass on both Pythons.
- M57 on 3.12.3: `4 failed, 126 passed`, the `::ffff:127.0.0.1` and `::ffff:10.0.0.5` rows of both
  parametrized tests (by digits and by name). The mutant answers 216,708 of the 231,072 mapped
  addresses in other words, for example `::ffff:127.0.0.0` "a reserved address" where the kept code
  says "a loopback address". None is let through.
- M57 on 3.13.17: `130 passed`, and 0 of the 231,072 answers move.
- The probe's property line: on 3.13.17 `is_unspecified`, `is_loopback`, `is_link_local`,
  `is_multicast`, `is_reserved`, `is_private` and `is_global` all defer to `ipv4_mapped`; on 3.12.3
  only `is_private` and `is_global` do.

## Likely cause of what the candidate saw

`core/openferment_core/literature/collectors.py:287` exists for Pythons before 3.13, whose
`ipaddress` reads a mapped address's loopback, link-local, multicast, reserved and unspecified classes
on the IPv6 form. Python 3.13 (`/usr/lib/python3.13/ipaddress.py`, `IPv6Address.is_loopback` and its
neighbours) defers each of them to `ipv4_mapped`. So the line is dead code on 3.13.17, and the tests
that hold it run where it lives: CI's 3.12.3 run (`.github/workflows/verify.yml:63`, `setup-uv` with no
Python named). The gap between the two gates is one line's worth of version-dependent code, and
the first CI run after its removal would say so.
