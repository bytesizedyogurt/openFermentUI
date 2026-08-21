# `biorepo_mcp` — BioRepo over MCP

The server-side half of `CorpusAdapter` (`src/adapters/types.ts`): papers,
extraction records, patent scope, and retrieval. Three tools answer from the
real corpus; three are declared and refuse.

Everything served is validated on read through the canonical Pydantic models in
`packages/core` — the same models the exporter wrote `data/corpus/*.json` with.
A corpus file the schema cannot parse stops the process from starting, because
a server that started anyway would be attesting to a corpus it does not hold.

## Tools

| Tool | Status | Mirrors |
|---|---|---|
| `health` | implemented | — |
| `get_paper` | implemented | `CorpusAdapter.getPaper` |
| `list_papers` | implemented | — (the index, not the library) |
| `list_records` | implemented | `CorpusAdapter.getRecords` |
| `search_papers` | **declared, refuses** | `CorpusAdapter.searchPapers` |
| `get_scope` | **declared, refuses** | `CorpusAdapter.getScope` |
| `get_whitespace` | **declared, refuses** | `CorpusAdapter.getWhitespace` |

### Why three of seven refuse

`search_papers` — corpus retrieval is PaperQA2's and CLAUDE.md says do not
reimplement it. A substring filter here would be four lines, and those four
lines would be a second implementation that has to agree with the browser's
forever while wearing a server's authority. The browser's filter already states
in every trace that it is not a retrieval system; a server-side twin would be
harder to say that about.

`get_scope` and `get_whitespace` — every `Patent` in this corpus carries
`parseUncertain: true` and `bounds: []`. A scope answer computed from empty
bounds comes back as an empty hit list, which reads as "unencumbered". That is
a different sentence from "no claim was checked", and only one of them is true.

### Deliberate absence

**There is no `write_record` tool and there must not be one.** The adapter
declares `writeRecord` and the browser fixture implements it, because there a
human is looking at the screen that submitted it. An MCP tool is called by an
agent, unattended, and what it would write is a claim about a REAL PUBLICATION
into the store that the Ledger, the gold set and every aggregate read from.

**No `list_patents`.** `Patent` has a Pydantic model but no
`data/corpus/patents.json` — the exporter maps seven collection keys to seven
models and `Patent` is not among them. Declaring a tool that reads a file the
exporter does not write would be declaring a capability that cannot be met.

## Running it

```
cd servers/corpus
uv sync
.venv/bin/python scripts/smoke_client.py
```

## PROVEN vs written

**PROVEN** — watched running, output below is the transcript that command
actually produced:

- The server starts, completes the MCP handshake and serves over real stdio.
- All seven tools are registered and listed.
- `health` reports a snapshot id derived from the two files it read.
- `get_paper` answers a hit and a miss; the miss carries a notice.
- `list_records` filters, and reports unknown ids in a notice.
- All three declared tools refuse with a message naming what is missing.

**WRITTEN BUT UNPROVEN**:

- The `Dockerfile`. Docker cannot run in the environment this was authored in.
  The image is written to build from the repo root (it needs `packages/core`
  and `data/corpus`, both outside this directory) and to set `OF_CORPUS_DIR`,
  which is not optional in the image: `default_corpus_dir()` walks up from the
  package file to the repo root and that walk does not resolve inside the
  container.
- Everything the refusals say they WILL return once PaperQA2 and parsed claim
  bounds exist. Those are contracts, not behaviour.

## Transcript

```
{
  "serverInfo": {
    "name": "biorepo_mcp",
    "version": "0.1.0"
  },
  "protocolVersion": "2025-11-25"
}

=== tools/list ===
- health: Liveness plus identity: { ok, serverVersion, corpusSnapshotId, corpusFiles }.
- get_paper: One paper by id, or null with a notice naming the miss.
- list_papers: Every paper in the snapshot, as { id, title, year, venue }.
- list_records: Records, filtered. No filter returns the whole set.
- search_papers: DECLARED, REFUSES. Retrieval is PaperQA2's and is not implemented here.
- get_scope: DECLARED, REFUSES. The claims are not machine-readable yet.
- get_whitespace: DECLARED, REFUSES. Whitespace is the complement of parsed claims.

=== health ===
{
  "ok": true,
  "serverVersion": "biorepo-mcp/0.1.0",
  "corpusSnapshotId": "sha256:188b31e994f83c66",
  "corpusFiles": [
    "data/corpus/papers.json",
    "data/corpus/records.json"
  ]
}

=== get_paper ZZ9 (miss) ===
{
  "data": null,
  "serverVersion": "biorepo-mcp/0.1.0",
  "corpusSnapshotId": "sha256:188b31e994f83c66",
  "notice": "No paper 'ZZ9' in corpus snapshot sha256:188b31e994f83c66. The snapshot holds 132 papers."
}

=== list_records ids=[nope-1] (miss carries a notice) ===
{
  "data": [],
  "serverVersion": "biorepo-mcp/0.1.0",
  "corpusSnapshotId": "sha256:188b31e994f83c66",
  "notice": "1 requested id(s) are not in corpus snapshot sha256:188b31e994f83c66: nope-1."
}

=== search_papers (declared, must refuse) ===
Error executing tool search_papers: CorpusAdapter.searchPapers: retrieval is not implemented by this server. The query (35 chars, k=5) parsed cleanly and was discarded. Corpus retrieval belongs to PaperQA2 and is deliberately not reimplemented; use list_papers and get_paper for id-addressed reads.

=== get_scope (declared, must refuse) ===
Error executing tool get_scope: CorpusAdapter.getScope: patent claim bounds are unparsed (every Patent carries parseUncertain: true, bounds: []). A scope test over 1 axis/axes would return an empty hit list that reads as 'unencumbered', which this server is not entitled to say.

=== get_whitespace (declared, must refuse) ===
Error executing tool get_whitespace: CorpusAdapter.getWhitespace: whitespace is the complement of parsed claim bounds, and no claim in this corpus is parsed. The complement of nothing is everything, which is not a finding.
```

Abridged: `list_papers` (132 entries) and `list_records paper_id=M5` are in the
full transcript and are omitted here for length.
