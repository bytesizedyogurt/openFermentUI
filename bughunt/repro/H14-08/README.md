# H14-08: Home says pureOS has "no process model"

**Statement.** Home's pureOS destination reads "45 unit operations · no process model" while pureOS's own page says it builds a train unit by unit from BioSTEAM's units and runs it, and the service registers pureOS's `train` engine.

**Contract.**
- `src/screens/Home.tsx:235`: "What each destination actually has, right now (§7)." (the doc comment over `stateOf`, the function that writes every destination line).
- `src/screens/PureOS.tsx:409`: "pureOS builds a train unit by unit from a catalogue of BioSTEAM's units and runs it".
- `src/screens/PureOS.tsx:533`: the page's own footer, "`${UNIT_OPERATIONS.length} operations; trains built here and read from runs`".
- `CLAUDE.md:80`: "the core's `biosteam`, `kinetics` (fermOS) and `train` (pureOS)"; `core/pyproject.toml:55`: `train = "openferment_core.pureos.engine:ENGINE"`.

**Command.** `bash bughunt/repro/H14-08/run.sh` from the repository root. It makes the fresh database `bh_r_h14_08_home` and starts the service keyless on a port in 10380 to 10389 with the built app in `dist/`. It makes one project, reads `GET /api/engines`, then reads Home and `/p/h14-08/pureos` in headless Chromium (`screen.mjs`) and greps the source lines at 2047f5a. When it finishes it stops the service and drops the database.

**Expected.** Home's pureOS line says what pureOS holds now: trains built in the Builder and run on BioSTEAM through the registered `train` engine, as the pureOS page's subtitle and footer say.

**Observed.** On both runs `GET /api/engines` names `biosteam, kinetics, train`, and `train` comes from `openferment_core.pureos.engine:ENGINE` on BioSTEAM 2.54.0. Home reads "pureOS | harvest, capture, recovery | 45 unit operations · no process model". The pureOS page reads "pureOS builds a train unit by unit from a catalogue of BioSTEAM's units and runs it" and "Produced by pureOS · 45 operations; trains built here and read from runs". Both runs end `RESULT: DEFECT`. The logs are `run1.log` and `run2.log`.

**Likely cause.** `src/screens/Home.tsx:291` hardcodes `pureOS: { now: \`${UNIT_OPERATIONS.length} unit operations · no process model\`, built: true }`. That line came in with alpha 1.0 (a261f30, OF-BLD-016), and nobody updated it when alpha 2.2 C.3 (a4a739f) put pureOS on typed quantities with every train run a row and registered the train engine. In E.20, Home's fermOS line was rewritten for alpha 2.2. Its pureOS line stayed as it was.

**Severity.** S4 (Drift): wording on Home that disagrees with the tree. pureOS's own page and its numbers are right, and no stored value is wrong.
