# H4-05: a batch with μmax zero is refused as one whose sugar never runs out

**Statement.** Asked to run until the sugar runs out, a `batch_v1` simulation with μmax 0 is refused because "the
sugar never runs out". With β 0.1 g g⁻¹ h⁻¹ (or maintenance 0.1 g g⁻¹ h⁻¹), X0 2 g/L, Yp/s 0.5 and S0 20 g/L the
sugar falls at a constant 0.4 g/L/h (0.2 g/L/h) and runs out at 49.95 h (99.9 h), the hours the same family reports
when a run length is named.

**Contract.**
- `core/openferment_core/kinetics.py:59-61`: "\"Until the sugar runs out\" integrates over horizons doubling from
  1/μmax, at most HORIZON_DOUBLINGS times, and a run whose sugar stops falling (growth stopped at Pmax, or by the
  second nutrient) is refused in words."
- `core/openferment_core/kinetics.py:597-599`, the run length's note: "Until the sugar runs out (Appendix 2 §A): the
  first hour the sugar falls to a thousandth of its start (kinetics.RUN_OUT_SHARE). A run whose sugar stops falling
  is refused in words, and then a person names the length."

The refusal the contract names is for a sugar that stops falling. Here the sugar falls in a straight line to zero.

**Command** (from the repository root): `bash bughunt/repro/H4-05/run.sh`

It makes a fresh database `bh_r_h4_05_svc`, starts a keyless service on 127.0.0.1:9410, makes project `h405`, and
`check.py` posts five requests to `POST /api/fermos/simulate`: two draining cases (β 0.1; maintenance 0.1) each with
no run length and with a run length past the hand's run-out hour, and a control with β 0 and m 0. Then the service
stops, the database is dropped and the service's data copy is removed.

By hand, with μ 0 and kd 0 the cells hold at X0, so dS/dt = −(β/Yps + m)·X0 and the run-out hour is
(1 − 10⁻³)·S0 / ((β/Yps + m)·X0): 19.98 / 0.4 = 49.95 h for β 0.1, and 19.98 / 0.2 = 99.9 h for m 0.1.

**Expected.** Asked until the sugar runs out, each draining case ends at its run-out hour (49.95 h, 99.9 h), or is
refused only for a sugar that stops falling. The control, whose sugar never falls, may be refused.

**Observed** (run1.log, run2.log, the same both times).
- β 0.1, until the sugar runs out: HTTP 422 "μmax is zero, so the cells never grow and the sugar never runs out:
  name a run length". With a run length of 60 h: HTTP 200, `sugarRunsOutH` 49.95000000025453, end S 0.
- maintenance 0.1, until the sugar runs out: the same 422. With 120 h: HTTP 200, `sugarRunsOutH` 99.9, end S 0.
- control (β 0, m 0): the same 422, which is right for that case.

`RESULT: DEFECT` in both runs.

**Likely cause.** `core/openferment_core/kinetics.py:1209-1211`: `_integrate` refuses every until-run-out run with
`not v["mu_max"] > 0` before integrating, because the first horizon is `1.0 / v["mu_max"]`. The check looks at μmax
alone; β·X/Yps and m·X drain the sugar whatever the growth. A first horizon taken from the sugar's starting drain
(for example S0 / ((β·fP/Yps + m)·X0) when μmax is 0), with the refusal kept for a drain of zero, would let the
doubling loop and its "stopped falling" refusal at `kinetics.py:1235-1239` decide the case as the contract says.

**Severity.** S3: an edge case (a non-growing culture making product or burning sugar for maintenance), and naming a
run length is the workaround. The refusal's words state something false about the run.
