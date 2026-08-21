# `servers/` — the MCP skeletons

Five MCP servers, one per subsystem of OF-DES-001. Each is the server-side half
of one interface in `src/adapters/types.ts`, and each is deliberately a
skeleton: enough to start, answer from the real corpus, and be wired into an
agent host, with everything it cannot honestly do declared and refusing.

| Directory | Subsystem | Adapter | Language | Corpus it reads |
|---|---|---|---|---|
| `corpus/` | BioRepo | `CorpusAdapter` | Python | `papers.json`, `records.json` |
| `cell/` | geneOS | `CellAdapter` | Python | `papers.json`, `records.json`, `strains.json` |
| `process/` | fermOS | `ProcessAdapter` | Python | `scenarios.json` |
| `economics/` | Proforma | `EconomicsAdapter` | Python | `scenarios.json` |
| `guild/` | Guild | `GuildAdapter` | TypeScript | `protocols.json` |

## Why four Python and one TypeScript

Every server that serves an ENTITY is Python, because every entity has a
canonical Pydantic model in `packages/core` and a server must validate what it
serves through the same model the exporter wrote it with. A TypeScript server
would need either a hand-maintained validator or none at all, and CLAUDE.md's
one rule is about exactly that.

The Guild is the exception because it has nothing to validate: `GuildChapter`
and `Seal` have no Pydantic model, deliberately, because no chapter registry
exists and nothing issues a seal. It therefore serves only a thin projection of
the one corpus file it reads, and it says so in its manifest.

## What is the same across all five

**The response envelope.** `{ data, serverVersion, corpusSnapshotId, notice? }`
— `AdapterResponse<T>` from the seam. `modelVersion` is absent from everything
these servers return, and the absence means NO MODEL RAN rather than "version
unknown". The first tool that computes something must stamp what computed it.

**`corpusSnapshotId` is derived, never a constant.** It is a SHA-256 over the
raw bytes of exactly the corpus files that process read, framed by
`openferment_core.snapshot.corpus_snapshot_id`. `health` returns `corpusFiles`
alongside it so a reader holding the repo can recompute the id instead of
trusting it.

Two servers reading the same files report the same id — `process` and
`economics` both read only `scenarios.json` and both answer
`sha256:a942d5c30fed7fba`. That property is the whole point, and it did not
hold when this directory was first written: the two servers written first each
grew their own framing (`name:bytes` with a `sha256:` prefix against
`name\0bytes` with a `corpus-` prefix), so two servers reading the same file
reported different ids while one of them carried a docstring promising the
opposite. The framing now lives in one place and
`scripts/check-servers.mjs` feeds the TypeScript and Python halves the same
inputs — including a pair that collides under any framing without a length
prefix — and fails if they disagree.

**Refusals are first-class.** A tool that cannot answer honestly is declared,
raises with a message naming what is missing, and states what it will return
when the real subsystem is wired up. The shape is fixed now so that filling it
in later touches no caller.

Every manifest gives each tool one of exactly three statuses, and
`check:servers` rejects a fourth:

| Status | Means |
|---|---|
| `implemented` | Answers for real, from the corpus. |
| `implemented-empty` | Answers, and the answer is permanently empty because the thing it would list does not exist. The tool works; the emptiness is the finding. |
| `declared-refuses` | The shape is fixed and the tool raises, naming what is missing. |

The vocabulary is closed because it had already drifted — `process` said `stub`
where the other four said `declared-refuses` for identical behaviour.

## Deliberate absences

Not oversights. Each is a tool that was considered and left out:

- **No tool publishes anything** (Guild). Disclosure drafting is reversible;
  publication is initiated by a human outside the agent loop. An MCP tool that
  triggers irreversible public disclosure is exactly the tool not to hand an
  agent.
- **No tool mints a seal** (Guild). A seal attests that a chapter checked
  something. There is no chapter and no check.
- **No tool writes an extraction record** (BioRepo). What it would write is a
  claim about a real publication into the store the Ledger, the gold set and
  every aggregate read from. The way to keep an agent from fabricating data is
  to not hand it the pen.
- **No tool authors or edits a cost model** (Proforma). A cost model's axes are
  the frame every MSP is quoted in; widening one would move a headline number
  without touching a datum, and the change would look like arithmetic.
- **No tool registers a strain** (geneOS). It would create a chassis nobody
  built and let a BSL be asserted rather than assessed.

## Running one

Python servers:

```
cd servers/<name>
uv sync
.venv/bin/python scripts/smoke_client.py     # drives the whole surface over real stdio
.venv/bin/python -m <pkg>.server             # or run it as an MCP host would
```

The Guild server:

```
cd servers/guild
npm install
npx tsx scripts/client.ts
```

Every `README.md` in this directory carries the transcript that script actually
produced, and a **PROVEN vs written** section saying which claims were watched
and which were not.

## What the gate checks

`pnpm check:servers` (part of `pnpm verify`) watches five things:

1. **Manifest ↔ server.** Every tool a manifest declares is registered, and
   every registered tool is declared. An undeclared tool is one nobody
   reviewed.
2. **Snapshot parity.** TypeScript and Python produce identical ids for
   identical inputs, and the ids are distinct across inputs — two halves that
   both returned a constant would agree perfectly and prove nothing.
3. **Cost model derivation.** What `proforma_mcp` derives from
   `scenarios.json` still equals the TypeScript `COST_MODELS`.
4. **Attribution parity.** "Which records count for a strain" agrees between
   `openferment_core` and `src/adapters/fixture/cell.ts`, for every strain.
5. **Status vocabulary.** Every tool's status is one of the three above.

It does NOT check that the servers start. That needs five virtualenvs and a
node install per server, which is a CI job rather than a `pnpm verify` stage.
