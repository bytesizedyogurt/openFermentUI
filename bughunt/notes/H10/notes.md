# H10: service hardening

Keyless throughout, test databases `bh_h10_*` alone (each dropped), ports 8900-8906, every service stopped.
Nothing under core/, src/, scripts/ or examples/ changed (git status shows bughunt/notes/H10/ alone).
`scripts/repro_all.sh [02|03|04|05|all]` reproduces each candidate from a fresh database on port 8905.

## Bind address
prove.py, smoke.ts, prototype-up.sh (the service and its node server), launchd.py's plist default, lib.sh's
default and uvicorn's own default listen on 127.0.0.1; lsof showed `localhost:8900` alone. install.sh
widens the bind only when OPENFERMENT_HOST says so. Held.

## guard.py
`guard_matrix.py` sends 30 header shapes over a raw socket. Forged and duplicated Origins, Origin null,
ws:, file: and empty, a hostile Host with or without Origin, a forged X-Forwarded-Host beside a cross-site
Origin, X-Forwarded-For, the Funnel header and a missing Host were refused; PATCH, PUT and DELETE alike.
`cross_site.mjs` drives Chromium (no proxy) at `attacker/attack.html` served on 8901: a no-cors fetch, a
text/plain form POST and sendBeacon to /api/projects, no-cors POSTs to the tool door and /rag, each 403
with the page's origin in the log; JSON fetch and PUT stop at the preflight (OPTIONS 405). Writes held.
guard.py's docstring leaves `.localhost` out of the names it lists (H10-05).

## CORS
No Access-Control-Allow-Origin on any answer for any Origin; /api preflight 405, /rag preflight 400.

## /rag and its key
Key set (8902): right key in Bearer or X-API-Key 200; wrong, empty or a prefix 401; a wrong X-API-Key
beside a right Bearer 401; no project 422; unknown project 404; /rag/mcp 404; the key never in the log.
The lookup is a dict get (no compare to time). Key unset (8903, 8905): status and documents 401, but
/rag/health, /rag/v1/corpus-manifest (the project's counts), /rag/docs and /rag/openapi.json answer, and
the manifest names /v1, /mcp, /openapi.json, provider local-hash and byo_llm_key true (H10-03).

## The key override
A sentinel in X-OpenFerment-Key on health, a 422, a 404, an unknown project, a 500 and the tool door:
absent from every body and header, the log and a pg_dump; refused under a hostile Host and via Funnel.

## Paths, file names, ids
`path_sweep.py`: 17 values in every path parameter of every operation. No traversal answer and no leak
in any body. The NUL value answers 500 at nine path doors; `nul_probe.py` and `body_sweep.py` widen that
to query filters and body text, 20 /api doors and 2 /rag doors (H10-02). The four doors answering a NUL id
with a 404 in words show the inconsistency. Static dist/: 17 shapes, all 404; serve-dist.mjs with
prototype-up's decode stays inside dist/. Upload names: Path(name).name; SFF import writes no file.

## Size limits
No body or header limit (64 MB body read whole; 16 MB header accepted); a refused 64 MB body comes back
as 201 MB, the input echoed in each field error. Local callers alone reach it. Listed under suspected.

## Error bodies
4xx in words; the service's 5xx is a bare "Internal Server Error"; the kit's 500 names the exception
class. Library and engine refusals for odd plants, configurations and things: 422 in words. A websocket
upgrade outside /rag answers 500 (StaticFiles assert); no websocket route exists.

## SQL
Every text() holds constants and binds. Injection through every filter that reaches a query returned []
in milliseconds; pg_sleep never ran. Body columns are json, which CLAUDE.md and ADR-001 call JSONB (H10-04).

## GET side effects
`get_sweep.py` + `rowcounts.py`: every GET with ?project= kept no row.

## Scripts
guard_matrix.py, cross_site.mjs, attacker/attack.html, path_sweep.py, get_sweep.py, rowcounts.py,
nul_probe.py, body_sweep.py, rag_probe.sh, rebind_read.sh, serve_dist_probe.mjs, repro_all.sh,
coverage_lines.py (writes coverage.jsonl).
