# fermos_mcp — fermOS process server over MCP stdio.
#
# BUILD FROM THE REPO ROOT: the image needs packages/core (the canonical
# schema, a path dependency) and data/corpus (what the server serves), both of
# which live outside this directory.
#
#   docker build -f servers/process/Dockerfile -t fermos-mcp .
#   docker run -i fermos-mcp        # stdio transport: -i, no ports
#
# NOTE: docker cannot run in the environment this server was authored in, so
# this file is written-but-unproven; the stdio server itself was proven
# directly (see README, "PROVEN vs written").

FROM python:3.11-slim

WORKDIR /app

# The canonical schema first — it changes least.
COPY packages/core /app/packages/core
COPY servers/process/pyproject.toml servers/process/README.md /app/servers/process/
COPY servers/process/fermos_mcp /app/servers/process/fermos_mcp

RUN pip install --no-cache-dir /app/packages/core /app/servers/process

# The corpus the server attests to. OF_CORPUS_DIR points the loader at it.
COPY data/corpus /app/data/corpus
ENV OF_CORPUS_DIR=/app/data/corpus

ENTRYPOINT ["fermos-mcp"]
