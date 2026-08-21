# `fermos_mcp` — fermOS over MCP

The server-side half of `ProcessAdapter` (`src/adapters/types.ts`): scenarios,
designs, and the tier cascade over a configuration. Two tools answer from the
real corpus; the evaluation pair is declared and refuses.

## Tools

| Tool | Status | Mirrors |
|---|---|---|
| `health` | implemented | — |
| `list_scenarios` | implemented | `ProcessAdapter.listScenarios` |
| `get_scenario` | implemented | `ProcessAdapter.getScenario` |
| `submit_evaluation` | **declared, refuses** | `ProcessAdapter.submitEvaluation` |
| `get_evaluation` | **declared, refuses** | `ProcessAdapter.getEvaluation` |

### Why the handle-based shape is fixed now

`submitEvaluation` returns a handle and `getEvaluation` collects it, and that
is true here before there is anything to collect. T2 (a reactor model) and T3
(a Monte Carlo cash flow) will both exceed any request/response timeout, so the
result has to be collected by handle — and that has to be true from the first
call site, because retrofitting it means touching all of them.

Both refuse rather than issue a handle. Issuing one would promise a result no
code here can produce, and fabricating a `DesignRecord` is forbidden outright.
`submit_evaluation` validates the request shape first, through a Pydantic model
that inherits the same wire convention every entity uses, so the refusal is
about the missing evaluator and not about a malformed request.

## Running it

```
cd servers/process
uv sync
.venv/bin/python scripts/smoke_client.py
```

## PROVEN vs written

**PROVEN** — watched running, output below is the transcript that command
actually produced:

- The server starts, completes the MCP handshake and serves over real stdio.
- All five tools are registered and listed.
- `health` reports a snapshot id derived from `scenarios.json` — the same id
  `proforma_mcp` reports, because both read exactly that one file.
- `list_scenarios` returns all three scenarios whole, validated through the
  canonical `Scenario` model and serialised back through it, so the wire shape
  is the same camelCase the generated TypeScript reads.
- `get_scenario` answers a hit and a miss; the miss names the ids that exist.
- Both stubs refuse, each naming what is missing.

**WRITTEN BUT UNPROVEN**:

- The `Dockerfile`. Docker cannot run in the environment this was authored in.
  The image is written to build from the repo root (it needs `packages/core`
  and `data/corpus`, both outside this directory) and to set `OF_CORPUS_DIR`,
  which is not optional in the image: `default_corpus_dir()` walks up from the
  package file to the repo root and that walk does not resolve inside the
  container.
- Everything the two refusals say they WILL return once an evaluator exists —
  a `JobId`, and an `EvaluationStatus` whose `position` is REPORTED by the
  runner rather than derived by the caller.

## Transcript

```
{
  "serverInfo": {
    "name": "fermos_mcp",
    "version": "0.1.0"
  },
  "protocolVersion": "2025-11-25"
}

=== tools/list ===
- health: Liveness plus identity: { ok, serverVersion, corpusSnapshotId }.
- list_scenarios: All cost scenarios from data/corpus/scenarios.json.
- get_scenario: One scenario by id, or null with a notice naming the miss.
- submit_evaluation: STUB. Validates the request shape, then refuses: no evaluator is wired up.
- get_evaluation: STUB. Refuses: no evaluator is wired up.

=== health ===
{
  "ok": true,
  "serverVersion": "fermos-mcp/0.1.0",
  "corpusSnapshotId": "sha256:a942d5c30fed7fba",
  "corpusFiles": [
    "data/corpus/scenarios.json"
  ]
}

=== get_scenario sc-s9 (miss) ===
{
  "data": null,
  "serverVersion": "fermos-mcp/0.1.0",
  "corpusSnapshotId": "sha256:a942d5c30fed7fba",
  "notice": "No scenario 'sc-s9' in corpus snapshot sha256:a942d5c30fed7fba. Ids present: sc-s1, sc-s2, sc-s3."
}

=== submit_evaluation (stub, must refuse) ===
Error executing tool submit_evaluation: ProcessAdapter.submitEvaluation: no evaluator is wired up. This is where T2 (reactor model) and T3 (BioSTEAM cash flow) go; the request for scenario 'sc-s1' parsed cleanly and was discarded. No handle was issued.

=== get_evaluation (stub, must refuse) ===
Error executing tool get_evaluation: ProcessAdapter.getEvaluation: no evaluator is wired up. This backend has never issued a handle, so 'job-000' cannot be one of its own. Submit via submit_evaluation once an evaluator exists.
```

Abridged: `list_scenarios` and `get_scenario sc-s2` return the three scenarios
in full (some 600 lines) and are omitted here for length.
