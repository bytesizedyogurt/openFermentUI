# `openferment-guild` — the Guild over MCP

The server-side half of `GuildAdapter` (`src/adapters/types.ts`): chapters,
deposits, seals. Today that means answered honestly, which means answered
mostly empty.

## The one TypeScript server here, and why

Every other server in this directory is Python, because every entity it serves
has a canonical Pydantic model and a server must validate what it serves
through the same model the exporter wrote it with.

This one has nothing to validate. `GuildChapter` and `Seal` have **no Pydantic
model**, deliberately — no chapter registry exists and nothing issues a seal —
so the canonical shapes live in the adapter seam until a server produces one.
Redeclaring them here would be the hand-maintained twin CLAUDE.md's one rule
forbids, so `server.ts` imports `GuildChapter` type-only and the one collection
it reads is served as a thin projection rather than as a vouched-for entity.

That exception costs something and it is worth naming: this server cannot
detect a corpus file the schema would reject. Its `guild_health` returns
`ok: false` on an unreadable file rather than refusing to start, because saying
the read failed is the strongest honest thing a server with no schema can do.

## Tools

| Tool | Status | Mirrors |
|---|---|---|
| `guild_health` | implemented | — |
| `list_sealable_protocols` | implemented | — |
| `list_chapters` | implemented, permanently empty | `GuildAdapter.listChapters` |

`list_chapters` returns the ABSENCE of a registry, with a notice saying so,
rather than an invented institution. When a real registry exists (ORCID for
who, in-toto for what was attested), the tool's shape does not change — only
its contents do.

`list_sealable_protocols` is protocols a chapter could be ASKED to seal, not
protocols any chapter has sealed. It exists so this server serves the file it
digests: `corpusSnapshotId` is a digest over `data/corpus/protocols.json`, and
a digest over a file the server never opens would attest to data it cannot
vouch for. `currentVersion` is included because a `SealSubject` of kind
`protocol-version` carries a version, and a seal that does not commit to a
specific one attests to nothing.

## Deliberate absences

**No tool publishes anything, and there must not be one.** Disclosure drafting
(a future `prepare_disclosure`) is reversible; publication is initiated by a
human outside the agent loop. An MCP tool that triggers irreversible public
disclosure is exactly the tool not to hand an agent.

**No tool mints a seal.** A seal is an attestation that a chapter checked
something. There is no chapter and no check, so the fixture's `requestSeal`
refuses and this server declares no equivalent — refusing a tool is a weaker
statement than not offering it, and here the stronger one is correct.

## Running it

```
cd servers/guild
npm install
npx tsx scripts/client.ts
```

## PROVEN vs written

**PROVEN** — watched running, output below is the transcript that command
actually produced:

- The server starts, completes the MCP handshake and serves over real stdio.
- All three tools are registered and listed.
- `guild_health` reports a snapshot id derived from the file it read.
- `list_sealable_protocols` returns the nine protocols with their current
  versions, carrying a notice that none of them is sealed.
- `list_chapters` returns the honest empty shape with its notice.

Separately proven by `pnpm check:servers`: this server's snapshot framing
produces identical ids to `openferment_core.snapshot` on identical inputs,
including a pair that collides under any framing without a length prefix.

**WRITTEN BUT UNPROVEN**:

- The `Dockerfile`. Docker cannot run in the environment this was authored in.
- ORCID and in-toto. Named as what this server will wrap; neither is wired up
  and nothing here talks to either.

## Transcript

```
== tools/list ==
- guild_health
- list_sealable_protocols
- list_chapters

== tools/call guild_health ==
{
  "ok": true,
  "serverVersion": "guild-0.1.0",
  "corpusSnapshotId": "sha256:529b7ca51222b265"
}

== tools/call list_sealable_protocols ==
{
  "data": [
    {
      "id": "PR-TAP-01",
      "title": "TAP medium preparation (1 L base)",
      "bsl": 1,
      "currentVersion": "1.1"
    },
    {
      "id": "PR-SEED-01",
      "title": "cw15 seed train: plate to 50 mL to 400 mL",
      "bsl": 1,
      "currentVersion": "1.0"
    }
  ],
  "serverVersion": "guild-0.1.0",
  "corpusSnapshotId": "sha256:529b7ca51222b265",
  "notice": "These are protocols a chapter could be asked to seal, not protocols any chapter has sealed. No seal exists — see requestSeal, which refuses."
}

== tools/call list_chapters ==
{
  "data": [],
  "serverVersion": "guild-0.1.0",
  "corpusSnapshotId": "sha256:529b7ca51222b265",
  "notice": "No chapter registry exists. The empty list is the absence of a registry, not a guild with no chapters in it, and inventing an institution to populate it would be inventing an affiliation."
}
```

Abridged: `list_sealable_protocols` returns nine protocols; two are shown.
