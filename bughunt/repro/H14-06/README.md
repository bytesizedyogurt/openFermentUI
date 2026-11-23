# H14-06: Home's Postdoc destination says "live" while the service holds no key

**Statement.** On a keyless service, Home's destinations band tells a person Postdoc is "live through
openferment-core, on the model it is configured with" while `GET /api/health` answers `hasKey: false` and Postdoc's
own screen, one click away, says "Postdoc is running without an API key".

**Contract.**
- `src/screens/Home.tsx:235-237` (the comment over `Counted` and `stateOf`): "What each destination actually has,
  right now (§7). Counted from the store's lists where there is something to count, and stated as "nothing" where
  there is not."
- `src/screens/Home.tsx:781-782` (the destinations band): "the whole navigation, laid out once with an honest
  current state per entry."
- `src/screens/Postdoc.tsx:144-146`: on `health.ok && !health.hasKey` the screen shows the callout
  "Postdoc is running without an API key"; `src/screens/Postdoc.tsx:498-500` names the model ("The Postdoc service
  answers on ...") only when `health.hasKey` is true.
- `core/openferment_core/api.py:471-473` (the health route's docstring): "`hasKey` lets the UI tell "the service is
  down" from "the service is up but has no key"".

**Command** (from the repository root):

    bash bughunt/repro/H14-06/run.sh

It makes a fresh database `bh_r_h14_06_home`, starts the service keyless on the first free port in 10081-10089
(Chromium refuses 10080 as an unsafe port), makes one project through the API, reads `GET /api/health`, reads Home
and Postdoc of the built app (`dist/`) in headless Chromium (`screen.mjs`), prints the source lines at 2047f5a, and
cleans up (service stopped, database and data directory dropped). No model is called.

**Expected.** With `hasKey: false`, Home's Postdoc destination line says Postdoc waits for a key (for example
"waiting for a key on the service"), in step with Postdoc's own callout, and names the configured model once the
service holds one.

**Observed** (run1.log and run2.log, the same both times):

    GET /api/health -> {"ok":true,...,"model":"claude-opus-5-5","fallbackModel":"claude-sonnet-5-5","hasKey":false}
    Home's Postdoc card: Postdoc | ask, plan, answer from records | live through openferment-core, on the model it is configured with
    Postdoc's callout:   Postdoc is running without an API key
    Postdoc's answers-on line: (absent, as hasKey is false)
    RESULT: DEFECT

**Likely cause.** `src/screens/Home.tsx:285` writes fixed words for every state of the service:

    Postdoc: { now: 'live through openferment-core, on the model it is configured with', built: true },

Home reads no health answer at all (no line of `src/screens/Home.tsx` names `health` or `hasKey`), so `stateOf`
(`src/screens/Home.tsx:281`, called at `:366-368`) has nothing to word the line from. A small fix passes the health
answer Postdoc already reads into `Counted` and words the line from `hasKey`.

**Severity.** S4 (wording on Home; Postdoc's own screen gives the right state and the fix for it).
