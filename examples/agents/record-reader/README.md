# record-reader: an example MCP client of openFerment, known to the service as `example-agent/0.1`
- `uv run examples/agents/record-reader/record_reader.py --project proof --service http://127.0.0.1:<port>` started the `openferment` server `.mcp.json` declares, with `--project proof --service <origin>` appended, so every call went to the running service.
- It connected under MCP's `clientInfo` name `example-agent`, version `0.1`, which the service writes as `example-agent/0.1`.
- It listed the project's records with `biorepo_read`, kind `record`: each row's ref, state, status, provenance and label, beside the count of every match.
- It kept one placeholder skill with `catalogue_write`, `example-agent.0.1-a-skill` ("A placeholder skill"), naming no real strain, species or product; a rerun replaces it.
- It read back who made that write: the entry by `catalogue_read` and its row at `GET /api/audit` both said `example-agent/0.1`, agent `model`, door `http`, and the entry's source read "example-agent/0.1, at the HTTP endpoint".
