# `geneos_mcp` — geneOS over MCP

The server-side half of `CellAdapter` (`src/adapters/types.ts`): hosts, and
what is known or predicted about them. Three tools answer from the real corpus;
one is declared and refuses.

## Tools

| Tool | Status | Mirrors |
|---|---|---|
| `health` | implemented | — |
| `list_strains` | implemented | `CellAdapter.listStrains` |
| `get_strain` | implemented | `CellAdapter.getStrain` |
| `get_strain_records` | implemented | `CellAdapter.getStrainRecords` |
| `predict_flux` | **declared, refuses** | `CellAdapter.predictFlux` |

### Why `predict_flux` refuses

There is no genome-scale metabolic model in this build. Flux balance is
COBRApy's, in Python, and CLAUDE.md names it among the libraries a second
implementation would have to agree with forever. A prediction is ABSENT rather
than estimated — the same fact every design in this build reports as an absent
T1, in the same words.

`null` alone would read as "no answer for this strain" when the truth is "no
model, for any strain", so the refusal says which. When COBRApy is wired up
this returns a `FluxPrediction` whose `modelId` names the SBML that was solved
— not optional, because a flux without the model that produced it is a number
with no way to check it — and the envelope gains a `modelVersion`, because
something will have computed it.

### Where the attribution rule lives

`get_strain_records` does not implement "which records count for a strain".
That rule is `openferment_core.corpus.records_attributed_to`: a record counts
when it is tagged with the strain, or — absent a tag — when its paper's
organism list names it, and an explicit tag for a different strain always wins.

It is Python because it is an attribution decision about the corpus rather than
a display choice: it decides what evidence exists for a host, which the Ledger
and any aggregate over a strain inherit. The TypeScript copy in
`src/adapters/fixture/cell.ts` says so itself and names its own retirement.
Until it retires, `pnpm check:servers` replays every strain through both and
fails if the record ids differ.

### Deliberate absence

No tool designs, edits or registers a strain. A host record is what protocols,
records and biosafety bounds are keyed to; adding one unattended would create a
chassis nobody built and let a BSL be asserted rather than assessed.

## Running it

```
cd servers/cell
uv sync
.venv/bin/python scripts/smoke_client.py
```

## PROVEN vs written

**PROVEN** — watched running, output below is the transcript that command
actually produced:

- The server starts, completes the MCP handshake and serves over real stdio.
- All five tools are registered and listed.
- `health` reports a snapshot id derived from the three files it read.
- `get_strain` answers a hit and a miss; the miss names the ids that do exist.
- `get_strain_records` attributes records, and distinguishes an UNKNOWN host
  from a known host with no evidence — two different empty lists, two different
  notices.
- `predict_flux` refuses with the same sentence the designs use.

Separately proven by `pnpm check:servers`: the attribution rule agrees with the
TypeScript fixture for all 7 strains and 99 attributed records.

**WRITTEN BUT UNPROVEN**:

- The `Dockerfile`. Docker cannot run in the environment this was authored in.
  The image is written to build from the repo root (it needs `packages/core`
  and `data/corpus`, both outside this directory) and to set `OF_CORPUS_DIR`,
  which is not optional in the image: `default_corpus_dir()` walks up from the
  package file to the repo root and that walk does not resolve inside the
  container.
- Everything the refusal says it WILL return once COBRApy exists.

## Transcript

```
{
  "serverInfo": {
    "name": "geneos_mcp",
    "version": "0.1.0"
  },
  "protocolVersion": "2025-11-25"
}

=== tools/list ===
- health: Liveness plus identity: { ok, serverVersion, corpusSnapshotId, corpusFiles }.
- list_strains: Every host in the snapshot. Mirrors CellAdapter.listStrains.
- get_strain: One host by id, or null with a notice naming the miss.
- get_strain_records: Every record attributable to a host. Mirrors CellAdapter.getStrainRecords.
- predict_flux: DECLARED, REFUSES. There is no genome-scale metabolic model in this build.

=== health ===
{
  "ok": true,
  "serverVersion": "geneos-mcp/0.1.0",
  "corpusSnapshotId": "sha256:99c452abd1a5ddf7",
  "corpusFiles": [
    "data/corpus/papers.json",
    "data/corpus/records.json",
    "data/corpus/strains.json"
  ]
}

=== get_strain nope (miss) ===
{
  "data": null,
  "serverVersion": "geneos-mcp/0.1.0",
  "corpusSnapshotId": "sha256:99c452abd1a5ddf7",
  "notice": "No strain 'nope' in corpus snapshot sha256:99c452abd1a5ddf7. Ids present: cw15, uvm4, creinhardtii-wt, gs115, treesei, ecoli, bovine."
}

=== get_strain_records nope (unknown host, notice says so) ===
{
  "data": [],
  "serverVersion": "geneos-mcp/0.1.0",
  "corpusSnapshotId": "sha256:99c452abd1a5ddf7",
  "notice": "'nope' is not a strain in corpus snapshot sha256:99c452abd1a5ddf7, so this empty list means the host is unknown, not that no evidence exists."
}

=== predict_flux (declared, must refuse) ===
Error executing tool predict_flux: CellAdapter.predictFlux: No genome-scale metabolic model in this build. Flux balance is COBRApy's, in Python, and server-side; a prediction is absent here rather than estimated, which is what T1 reports on every design for the same reason. The request (strain 'cw15', objective 'BIOMASS_Chlamy_auto') parsed cleanly and was discarded.
```

Abridged: `list_strains` (7 hosts), `get_strain cw15` and
`get_strain_records treesei` are in the full transcript and are omitted here
for length.
