# Documents this repository cites

Seven documents are cited about 237 times across `src/`, `scripts/` and the
markdown. **One of them is in this directory.** The other six are external and a
reader cannot open them.

That is worth an index rather than a cleanup. The citations carry section
numbers — `OF-DES-001 §7.3`, `OF-DEMO-002 §4.1` — and that precision is the
only surviving pointer to *why* a component is shaped the way it is. Stripping
them is irreversible: you cannot recover "§7.3" from a comment that no longer
has one. So they stay, and this table says what each document governs and, in
the last column, what **in this repository** actually holds the rule.

The pattern is borrowed from `src/data/demo/upstream.ts`, whose whole argument
is that naming a thing without stating its status is how a slide comes to say
"powered by AlphaFold" about software that has never called AlphaFold. The same
applies to a spec reference: a citation with no status reads as a document you
could go and read.

| Document | Status | What it governs | Where the surviving decision lives |
|---|---|---|---|
| `OF-COR-001` | **in repo** — [`OF-COR-001.md`](./OF-COR-001.md) | The β-casein corpus: 15 threads, the parameter ontology, the gold-set plan, §9 the patent landscape | The file itself |
| `OF-DES-001` | external | Front-end design and the working simulation. §6 tokens, §7 components, §8 screens, §11 the eight conditions, §13.2 the router, §20 the honesty policy | `BUILD-SPEC.md`; the §-numbered docstrings in `src/components/ui.tsx`, `src/styles.css` and each screen |
| `OF-FE-003` | external | The part rename (Trawl/Ledger/Assay → Intake/Ledger/Audit), §6 the rail, §6.1 permanent aliases, §7 the contradiction rail, §8.x screens, §8.12 the Run Mode takeover | `src/App.tsx` — the `RAIL`, the `ALIAS` table and `canonicalize()`; `src/data/demo/upstream.ts` for the part names; `MIGRATION.md` |
| `OF-FE-004` | external | Designs, scope, and executable-layer coverage | `src/engine/designs.ts`, `src/screens/DesignDetail.tsx` |
| `OF-DEMO-001` | external | The demo suite: the object pool, the six archetypes, §2.2 the seed disclaimer, §2.5 non-resolution, §2.6 a disclosure candidate per archetype, §8 the two pools stay apart | `scripts/check-demo-seed.ts` — the gate that actually enforces it; `MIGRATION.md` |
| `OF-DEMO-002` | external | §1 the part list, §2 routes, §4.x the components, §4.1 the source-type axis, §5 the demo palette | `src/data/demo/upstream.ts`; the demo-suite block in `src/styles.css`; `src/components/demo/` |
| `OF-DEMO-003` | external | The seeded contradictions and how each is adjudicated; §2 the pre-verbal reading of patent density | `scripts/check-demo-seed.ts`; `src/components/demo/ProblemTree.tsx` |

**"External" means the document is not in this repository and you cannot open
it.** It is not shorthand for "ask someone" — the rightmost column is the
answer. Where a rule matters, it is enforced by a gate in `pnpm verify` or
written into a docstring beside the code it governs, and that is the artefact
to trust. Where the two disagree, the repository is right and the citation is
stale.

## Adding a citation

Cite a section only if you can also name what holds the rule here. If nothing
does, the honest comment says what the code does and why, without a reference
that a reader cannot follow.
