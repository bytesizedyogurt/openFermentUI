# openferment-guild — MCP server over stdio.
#
# Build context is the REPO ROOT, because the server reads data/corpus/ and
# type-imports the canonical adapter seam from src/:
#
#   docker build -f servers/guild/Dockerfile -t openferment-guild .
#   docker run -i openferment-guild        # -i: stdio is the transport
#
# NOTE (honesty): docker is not runnable in the environment this skeleton was
# built in, so this file is written to be minimal and plausible but has NEVER
# been built. What HAS been run is the same entrypoint outside docker —
# `npm run start` / `npm run smoke` — see README.md for the transcript.

FROM node:22-slim

WORKDIR /repo

# The corpus the server digests and (eventually) serves.
COPY data/corpus/ data/corpus/

# Type-only sources the server compiles against (erased at runtime, needed
# for `npm run typecheck` inside the image).
COPY src/adapters/types.ts src/adapters/types.ts
COPY src/data/types.ts src/data/types.ts
COPY src/data/types.generated.ts src/data/types.generated.ts

COPY servers/guild/package.json servers/guild/package-lock.json servers/guild/
RUN cd servers/guild && npm ci

COPY servers/guild/tsconfig.json servers/guild/
COPY servers/guild/src/ servers/guild/src/
COPY servers/guild/manifest.json servers/guild/

WORKDIR /repo/servers/guild
ENTRYPOINT ["npx", "tsx", "src/server.ts"]
