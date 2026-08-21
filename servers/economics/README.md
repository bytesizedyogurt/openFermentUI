# `proforma_mcp` — Proforma over MCP

The server-side half of `EconomicsAdapter` (`src/adapters/types.ts`): the cost
model, and the plant behind the price. Two tools answer for real; three are
declared and refuse — and here the refusals are most of the surface, which is
the honest state of this subsystem rather than an oversight.

## Tools

| Tool | Status | Mirrors |
|---|---|---|
| `health` | implemented | — |
| `list_cost_models` | implemented | `EconomicsAdapter.listCostModels` |
| `get_cost_model` | implemented | `EconomicsAdapter.getCostModel` |
| `evaluate_point` | **declared, refuses** | `EconomicsAdapter.evaluatePoint` |
| `solve_plant` | **declared, refuses** | `EconomicsAdapter.solvePlant` |
| `get_sensitivity` | **declared, refuses** | `EconomicsAdapter.getSensitivity` |

### What is real, and where it comes from

`CostModelSummary` is `CostModel` minus its `evaluate`: `{ modelId, dims,
referencePoint }`. All three are already in `data/corpus/scenarios.json` —
`modelId` verbatim, `dims` as the sweep axes, `referencePoint` as the
scenario's `point` — so this server DERIVES the summaries rather than carrying
a copy of them. `pnpm check:servers` replays that derivation against the
TypeScript `COST_MODELS` and fails if the two stop agreeing; without that gate
it would be a hand-maintained twin.

`ScenarioDim` carries two fields a `CostModel` dim does not — `paperId` and
`sourceRecordId` — and they are dropped rather than passed along. They are the
provenance of the AXIS (which paper the range came from), which belongs to the
scenario a reader is looking at, not to the cost model a solver steps through.

Neither `CostModel.evaluate` nor `ResultGrid` ever crosses the wire and neither
can: one is a function and the other holds `Float64Array`s, and
`src/data/types.ts` records both as unable to round-trip through JSON Schema —
which makes them exactly the two things that must not appear on this interface.

### Why all three solves refuse

`solve_plant` — CLAUDE.md routes cost-model authoring to BioSTEAM in Python.
This repository has a TypeScript port of the bioSTEAM costing primitives and
the TEA, and that port is exactly the second implementation the migration
exists to retire. Answering here from a Python reimplementation would make
three. Producing a minimum selling price from anything less would put a number
with a currency sign on it into a trace, which is the single most quotable
thing this system emits.

`evaluate_point` — the interpolation it would do is over a grid built by
solving the plant at every node. Interpolation is the cheap half; the solve is
the half that does not exist here. CLAUDE.md keeps grid interpolation in
TypeScript deliberately, as a UI convenience over a grid the client already
holds; moving it server-side without the solve would move the convenience and
leave the substance behind.

`get_sensitivity` — two plant solves per parameter, and there are no solves.

### Deliberate absence

No tool authors, edits or adds a cost model. A cost model's dims and reference
point are the frame every MSP in the system is quoted in; an agent that could
widen an axis could move a headline number without touching a single datum, and
the change would look like arithmetic rather than like an edit.

## Running it

```
cd servers/economics
uv sync
.venv/bin/python scripts/smoke_client.py
```

## PROVEN vs written

**PROVEN** — watched running, output below is the transcript that command
actually produced:

- The server starts, completes the MCP handshake and serves over real stdio.
- All six tools are registered and listed.
- `health` reports a snapshot id derived from `scenarios.json` — and it is the
  same id `fermos_mcp` reports, because both read exactly that one file. That
  agreement is the property the shared snapshot framing exists for.
- `get_cost_model` answers a hit and a miss, both carrying a notice.
- All three solve tools refuse, each naming what is missing.

Separately proven by `pnpm check:servers`: the derivation from
`scenarios.json` equals `COST_MODELS` in `src/data/scenarios.ts` exactly.

**WRITTEN BUT UNPROVEN**:

- The `Dockerfile`. Docker cannot run in the environment this was authored in.
  The image is written to build from the repo root (it needs `packages/core`
  and `data/corpus`, both outside this directory) and to set `OF_CORPUS_DIR`,
  which is not optional in the image: `default_corpus_dir()` walks up from the
  package file to the repo root and that walk does not resolve inside the
  container.
- Everything the three refusals say they WILL return once BioSTEAM exists.

## Transcript

```
{
  "serverInfo": {
    "name": "proforma_mcp",
    "version": "0.1.0"
  },
  "protocolVersion": "2025-11-25"
}

=== tools/list ===
- health: Liveness plus identity: { ok, serverVersion, corpusSnapshotId, corpusFiles }.
- list_cost_models: Every cost model, as { modelId, dims, referencePoint }.
- get_cost_model: One cost model summary by id, or null with a notice naming the miss.
- evaluate_point: DECLARED, REFUSES. The grid it would read off does not exist here.
- solve_plant: DECLARED, REFUSES. BioSTEAM is not wired up.
- get_sensitivity: DECLARED, REFUSES. Two plant solves per parameter, and there are no solves.

=== health ===
{
  "ok": true,
  "serverVersion": "proforma-mcp/0.1.0",
  "corpusSnapshotId": "sha256:a942d5c30fed7fba",
  "corpusFiles": [
    "data/corpus/scenarios.json"
  ]
}

=== get_cost_model S3 (hit) ===
{
  "data": {
    "modelId": "S3",
    "dims": [
      {
        "key": "milkPrice",
        "label": "Raw milk price",
        "unit": "USD L⁻¹",
        "values": [
          0.3,
          0.4,
          0.5,
          0.6,
          0.75
        ]
      },
      {
        "key": "recovery",
        "label": "β-casein recovery",
        "unit": "fraction",
        "values": [
          0.3,
          0.45,
          0.6,
          0.75,
          0.9
        ]
      }
    ],
    "referencePoint": {
      "milkPrice": 0.45,
      "recovery": 0.6
    }
  },
  "serverVersion": "proforma-mcp/0.1.0",
  "corpusSnapshotId": "sha256:a942d5c30fed7fba",
  "notice": "Cost model summaries are derived from the scenario definitions in the corpus — the axes and the reference point, nothing that evaluates them. No minimum selling price is available from this server: solving the plant is BioSTEAM's work and it is not wired up."
}

=== get_cost_model S9 (miss) ===
{
  "data": null,
  "serverVersion": "proforma-mcp/0.1.0",
  "corpusSnapshotId": "sha256:a942d5c30fed7fba",
  "notice": "No cost model 'S9' in corpus snapshot sha256:a942d5c30fed7fba. Ids present: S1, S2, S3."
}

=== evaluate_point (declared, must refuse) ===
Error executing tool evaluate_point: EconomicsAdapter.evaluatePoint: no cost grid exists on this server. The request (model 'S1', 1 axis/axes) parsed cleanly and was discarded. A grid is built by solving the plant at every node; the solve is BioSTEAM's and is not wired up.

=== solve_plant (declared, must refuse) ===
Error executing tool solve_plant: EconomicsAdapter.solvePlant: BioSTEAM is not wired up. The request (model 'S1', 1 axis/axes) parsed cleanly and was discarded. No minimum selling price is available from this server.

=== get_sensitivity (declared, must refuse) ===
Error executing tool get_sensitivity: EconomicsAdapter.getSensitivity: a sensitivity bar is two plant solves per parameter, and solve_plant refuses. The request (model 'S1', 1 axis/axes) parsed cleanly and was discarded.
```

Abridged: `list_cost_models` (all three models) is in the full transcript and
is omitted here for length.
