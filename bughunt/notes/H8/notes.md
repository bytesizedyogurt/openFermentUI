# H8: Intake and literature

Commit 2047f5a, keyless, no model asked. Every test database was named `bh_h8_*` and dropped at
the end. The services ran on 8881 (main), 8886 (fixture mode) and 8887 (reproductions), with
listeners on 8882 to 8885. Nothing under core/, src/, scripts/, examples/ or docs/ changed
(`git status --porcelain` came back empty). The logs are in `logs/` and the scripts in `scripts/`.

## What I ran

- `scripts/make_files.py` makes the odd files: PDFs with and without a text layer, a damaged PDF,
  JATS in UTF-8, UTF-16 and Latin-1, text in UTF-16, Latin-1 and invalid UTF-8, a 51 MB text file
  and a 17 MB JSON. `scripts/intake_fuzz.py` sends them to upload, paste and collect, with
  duplicates and hostile names. The results are in `logs/intake-alpha.log` (the first pass) and
  `logs/intake-beta.log` (a second project over the same kit).
- `scripts/share_probe.py`: two projects hold one document and a third holds none. It reads the
  documents, the overlay, search and stats in each.
- `scripts/graph_probe.py` writes the rows a build would write (four entities, three edges) into
  the test database and reads them through the sci-rag server's own graph tools. A real build
  asks a model, so I ran none. `scripts/mcp_scope.py` reads get_document, get_citations,
  search_corpus and list_sources across the three projects.
- `scripts/listeners.py` and `scripts/import_url_probe.py` send about 70 address forms to
  import-url. `scripts/fetch_redirects.py` tests redirects, sizes, compression and the deadline
  under a stand-in network. `scripts/import_url_route.py` drives the route itself through
  TestClient, also over a stand-in network.
- `scripts/sff_import_fuzz.py` and `scripts/catalogue_fuzz.py` test the SFF upload door and the
  catalogue file door.
- `scripts/demo_report.py` runs `report._run` on a bh_ database (the demo of `pnpm lit:report`)
  without writing docs/. `literature_live report --project rep --configs
  interactive,vector_only,keyword_only` ran over `scripts/report_lane_setup.py`'s project, with
  its data folder in scratch and no --render.
- `scripts/repro_h8.sh <id>` reproduces each candidate from a fresh database. All twelve show
  (`logs/repro-all.log`).

## What held

- import-url refused every loopback, private, link-local, shared, reserved and multicast form
  with a reason in words, along with IPv4-mapped and IPv4-compatible IPv6, a public name
  resolving to 10/8, non-https schemes, credentials, CR/LF and over-long addresses. No request
  reached a listener. Under the stand-in network, every redirect to such an address was refused
  before connecting, the pinned connection went to the checked digits with the right Host and
  SNI, and the size caps held (declared length, streamed body, a false length, a gzip bomb), as
  did the redirect limit and the deadline. What the default allows: https on any port to an
  address that is global by Python's ipaddress, or to a name all of whose addresses are global,
  with its query kept whole, and up to five redirects that are each checked again.
- The project scope held at every door: passage search, documents, stats, the MCP document tools
  and the graph tools. Two projects sharing a document and a third holding none each saw their
  own. Graph descriptions and edges followed graph.py's rule.
- Every malformed file I tried got a refusal in words (empty, wrong encoding, no text layer,
  damaged, entity bomb, external entity, wrong suffix, past the size). The 413 limits held at 50
  MB, 16 MB and 4 MB.
- The committed retrieval report matches what the code produces: the demo part, and the Ethanol
  part rebuilt from its kept run.

## What broke

- H8-01: a case-only difference (mg against Mg) counts as "the same text". The second project's
  document reads the first project's unit.
- H8-02: a linked document carries the first project's title, licence class and licence words
  into the second project's reads. The second project's own outcome reports its own.
- H8-03: an upload name with %00 gets a 500 and leaves an orphan kit document. The cause is
  `unquote`, followed by a source_ref update after the kit's commit.
- H8-04: Latin-1 JATS is decoded with replacement characters, so µg/L becomes �g/L. The Markdown
  door refuses the same bytes.
- H8-05: a malformed redirect Location gets a 500 from import-url, because httpx.InvalidURL
  escapes the route.
- H8-06: a deep search whose graph and HyDE stages fail reports no degraded stage.
- H8-07: the report's kit rule credits a passage from another document with the same title.
- H8-08 to H8-12 are wording and small-door issues: the answer stream's error with no key, /rag
  answering without a key, catalogue rows with a repeated id or with their own source, and the
  SFF BOM.

## Left for a live model

Extraction, the graph build, the --judge lanes, answers, and the deep stages when a model answers.
