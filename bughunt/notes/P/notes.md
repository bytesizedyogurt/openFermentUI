# Hunt P: the paid debts tested again

Each row of the Known debts' Paid table was tried again on the tree at 2047f5a (code unchanged at the branch
head), keyless, on a service of the hunt's own (127.0.0.1:8950 over `bh_p_main`, fixture collectors on), one
more over a stub model endpoint (8951, 8952 over `bh_p_key`), and Chromium for the screens. Every service, the
stub and both databases are stopped and dropped. Nothing under core/, src/, scripts/ or examples/ changed.
Scripts are in `scripts/`; the verdict a row is in `candidates.json` under `held`.

## The project the probes stand on

`seed_demo.py` took the kit's demo corpus (CC0) into project `pa` through Intake's upload, wrote a stand-in
extraction for each document's first sentence naming days, extracted three candidates and accepted one. Project
`pb` holds one placeholder document. Runbooks, a deposition and scenarios were kept through `PUT /api/state`, a
kinetics run and a cornstover library run through `POST /api/engines/{name}/run`.

## What failed

- P-01 (row 2): a route of local models alone fails with no Anthropic key. `llm._call` builds the Anthropic
  client before it reads the route's provider. With a placeholder key the same call reaches the local stub at no
  charge. The test passes a `client_factory` and never reaches `_default_client`.
- P-02 (row 36): `biorepo._is_gold` reads the decision's label, so a verified decision with no gold value is
  kept gold when its label says gold. The browser's `provenanceOf` reads the same decision as verified: in
  Chromium the Intake table showed Verified and "0 in the gold set" for a record that the records table, BioRepo
  and Postdoc's evidence pool hold as gold. `import_alpha1` computes provenance by the same function.
- P-03 (row 31): Guild's review strip still names the retired PMCID, DOI or PMID rule. A comment in review.ts
  does too.

## What held, and how it was tried

- The key override (row 2's first half) held at the wire. A stub answered the Messages API on loopback, and the
  service reached it through `ANTHROPIC_BASE_URL` with every proxy pointed at a dead port. The named needle
  reached the stub as `x-api-key` on `/api/ask` and `/api/ask/stream`. It was found in no log line at debug
  level, no response, no SSE event and no row of either schema. The audit row said `{override: true}`.
- Project scoping held wherever it was tried: the audit, catalogues, protocols, runbooks_read, the state, the
  graph tools over stdio, runs, pureOS trains, selling_price, stream_table, Proforma bind with a reading and the
  engines' configurations.
- The append-only deposition held. A write that drops a kept reading, or changes one, was refused in words.
- A hollow-test probe on row 19: a pytest plugin dropped `depositions` from the train engine's `rests_on`, and
  the completeness test failed, as the row says it does.
- Fixture parity on row 6: `export-competence-fixtures.ts` was run into scratch, and both fixtures came out byte
  for byte.
- These checks are green: check:state, check:guild, gen-api --check, gen-tools --check and tsc --noEmit. Every
  targeted pytest selection run passed (agent interface; literature report and graph; catalogues, protocols and
  competence; tools, module tools, project state, route models and measurements; workers and Proforma).

## Open and Left by decision

No row was found worse than it says. Each was read against the tree. `duration_h` reaches no route or schema.
`units.json` maps `wt%` and `% (w/w)` to `% CDW`. A deposition write that drops readings is refused in words. A
reading's `by` is its deposition's maker, as studies.md says. One nuance on the last Left row:
`import_alpha1` reads `core/data/biorepo.json` by default when it runs.

## Left and suspected

- `pnpm smoke` and the walk were not run, since they choose ports and database names outside the hunt's.
- The kept-reference sim replays were not run (test:sim).
- At this session's start both MCP servers timed out after 30 s. Warm, each connects in about 2.3 s by
  `.mcp.json`'s exact command.
- One mishap: the first audit probe's `curl` wrapper let the shell expand `*`, and a few requests went to the
  proxy under file names taken as host names. They carried nothing from the repository and no key. The script
  was fixed before it ran again.
