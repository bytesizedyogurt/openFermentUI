# proforma_mcp — Proforma cost-model server over MCP stdio.
#
# BUILD FROM THE REPO ROOT: the image needs packages/core (the canonical
# schema, a path dependency) and data/corpus (what the server serves), both of
# which live outside this directory.
#
#   docker build -f servers/economics/Dockerfile -t proforma-mcp .
#   docker run -i proforma-mcp        # stdio transport: -i, no ports
#
# NOTE: docker cannot run in the environment this server was authored in, so
# this file is written-but-unproven; the stdio server itself was proven
# directly (see README, "PROVEN vs written").

FROM python:3.11-slim

WORKDIR /app

# The canonical schema first — it changes least.
COPY packages/core /app/packages/core
COPY servers/economics/pyproject.toml servers/economics/README.md /app/servers/economics/
COPY servers/economics/proforma_mcp /app/servers/economics/proforma_mcp

RUN pip install --no-cache-dir /app/packages/core /app/servers/economics

# The corpus the server attests to. OF_CORPUS_DIR points the loader at it —
# inside the image packages/core does not sit three levels below the repo root,
# so the walk-up default cannot work and the override is not optional here.
COPY data/corpus /app/data/corpus
ENV OF_CORPUS_DIR=/app/data/corpus

ENTRYPOINT ["proforma-mcp"]
