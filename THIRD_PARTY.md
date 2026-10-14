# Third-party software

Every package openFerment installs, with its version, the licence its own metadata
states, and the part of openFerment that uses it. `pnpm check:licences`
(`scripts/check-licences.py`, OF-BLD-014 §1.2) writes this file from what is installed
and fails while the committed copy is stale. The accepted licence strings, and every
package a person accepted, are in `core/licences.toml`.

## The service and its tests (`core/`)

| Package | Version | Licence | Used by | Passes as |
|---|---|---|---|---|
| annotated-doc | 0.0.5 | MIT | service, through fastapi | allowed |
| annotated-types | 0.8.0 | MIT | service, through anthropic, fastapi, pydantic | allowed |
| anthropic | 1.0.0 | MIT | service | allowed |
| anyio | 4.14.2 | MIT | service, through anthropic, fastapi, httpx, uvicorn | allowed |
| certifi | 2026.7.22 | MPL-2.0 | service, through httpx | accepted by Sean Creighton on 2026-10-14 |
| click | 8.4.2 | BSD-3-Clause | service, through uvicorn | allowed |
| docstring_parser | 0.18.0 | MIT | service, through anthropic | allowed |
| fastapi | 0.141.1 | MIT | service | allowed |
| h11 | 0.16.0 | MIT | service, through anthropic, httpx, uvicorn | allowed |
| httpcore | 1.0.9 | BSD-3-Clause | service, through httpx | allowed |
| httpcore2 | 2.12.0 | BSD-3-Clause | service, through anthropic | allowed |
| httptools | 0.8.0 | MIT | service, through uvicorn | allowed |
| httpx | 0.28.1 | BSD-3-Clause | service | allowed |
| httpx2 | 2.12.0 | BSD-3-Clause | service, through anthropic | allowed |
| idna | 3.19 | BSD-3-Clause | service, through anthropic, fastapi, httpx, uvicorn | allowed |
| iniconfig | 2.3.0 | MIT | tests, through pytest | allowed |
| jiter | 0.16.0 | MIT | service, through anthropic | allowed |
| numpy | 2.5.2 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | service, through rank-bm25 | allowed |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause | tests, through pytest | allowed |
| pluggy | 1.6.0 | MIT | tests, through pytest | allowed |
| pydantic | 2.13.4 | MIT | service | allowed |
| pydantic_core | 2.46.4 | MIT | service, through anthropic, fastapi, pydantic | allowed |
| Pygments | 2.21.0 | BSD-2-Clause | tests, through pytest | allowed |
| pytest | 9.1.1 | MIT | tests | allowed |
| python-dotenv | 1.2.3 | BSD-3-Clause | service | allowed |
| PyYAML | 6.0.3 | MIT | service, through uvicorn | allowed |
| rank-bm25 | 0.2.2 | Apache2.0 | service | allowed |
| sniffio | 1.3.1 | MIT OR Apache-2.0 | service, through anthropic | allowed |
| starlette | 1.6.0 | BSD-3-Clause | service, through fastapi | allowed |
| truststore | 0.10.4 | MIT | service, through anthropic | allowed |
| typing_extensions | 4.16.0 | PSF-2.0 | service, through anthropic, fastapi, httpx, pydantic, uvicorn | allowed |
| typing-inspection | 0.4.4 | MIT | service, through anthropic, fastapi, pydantic | allowed |
| uvicorn | 0.52.4 | BSD-3-Clause | service | allowed |
| uvloop | 0.22.1 | MIT License | service, through uvicorn | allowed |
| watchfiles | 1.2.0 | MIT | service, through uvicorn | allowed |
| websockets | 17.0.1 | BSD-3-Clause | service, through uvicorn | allowed |

`openferment-core`, the project itself, is skipped by name: the repository declares no licence yet.

## The browser app (JavaScript production dependencies)

| Package | Version | Licence | Used by | Passes as |
|---|---|---|---|---|
| @babel/runtime | 7.29.7 | MIT | browser app, through recharts | allowed |
| @fontsource/ibm-plex-mono | 5.3.0 | OFL-1.1 | browser app | allowed |
| @fontsource/ibm-plex-sans | 5.3.0 | OFL-1.1 | browser app | allowed |
| @fontsource/spectral | 5.3.0 | OFL-1.1 | browser app | allowed |
| @remix-run/router | 1.23.3 | MIT | through react-router-dom, which no file under src/ imports | allowed |
| @types/d3-array | 3.2.2 | MIT | browser app, through recharts | allowed |
| @types/d3-color | 3.1.3 | MIT | browser app, through recharts | allowed |
| @types/d3-ease | 3.0.2 | MIT | browser app, through recharts | allowed |
| @types/d3-interpolate | 3.0.4 | MIT | browser app, through recharts | allowed |
| @types/d3-path | 3.1.1 | MIT | browser app, through recharts | allowed |
| @types/d3-scale | 4.0.9 | MIT | browser app, through recharts | allowed |
| @types/d3-shape | 3.1.8 | MIT | browser app, through recharts | allowed |
| @types/d3-time | 3.0.4 | MIT | browser app, through recharts | allowed |
| @types/d3-timer | 3.0.2 | MIT | browser app, through recharts | allowed |
| @types/prop-types | 15.7.15 | MIT | browser app, through zustand | allowed |
| @types/react | 18.3.31 | MIT | browser app, through zustand | allowed |
| clsx | 2.1.1 | MIT | browser app, through recharts | allowed |
| csstype | 3.2.3 | MIT | browser app, through recharts, zustand | allowed |
| d3-array | 3.2.4 | ISC | browser app, through recharts | allowed |
| d3-color | 3.1.0 | ISC | browser app, through recharts | allowed |
| d3-ease | 3.0.1 | BSD-3-Clause | browser app, through recharts | allowed |
| d3-format | 3.1.2 | ISC | browser app, through recharts | allowed |
| d3-interpolate | 3.0.1 | ISC | browser app, through recharts | allowed |
| d3-path | 3.1.0 | ISC | browser app, through recharts | allowed |
| d3-scale | 4.0.2 | ISC | browser app, through recharts | allowed |
| d3-shape | 3.2.0 | ISC | browser app, through recharts | allowed |
| d3-time | 3.1.0 | ISC | browser app, through recharts | allowed |
| d3-time-format | 4.1.0 | ISC | browser app, through recharts | allowed |
| d3-timer | 3.0.1 | ISC | browser app, through recharts | allowed |
| decimal.js-light | 2.5.1 | MIT | browser app, through recharts | allowed |
| dom-helpers | 5.2.1 | MIT | browser app, through recharts | allowed |
| eventemitter3 | 4.0.7 | MIT | browser app, through recharts | allowed |
| fast-equals | 5.4.1 | MIT | browser app, through recharts | allowed |
| internmap | 2.0.3 | ISC | browser app, through recharts | allowed |
| js-tokens | 4.0.0 | MIT | browser app, through lucide-react | allowed |
| lodash | 4.18.1 | MIT | browser app, through recharts | allowed |
| loose-envify | 1.4.0 | MIT | browser app, through lucide-react, react-dom, recharts | allowed |
| lucide-react | 0.462.0 | ISC | browser app | allowed |
| object-assign | 4.1.1 | MIT | browser app, through recharts | allowed |
| prop-types | 15.8.1 | MIT | browser app, through recharts | allowed |
| react | 18.3.1 | MIT | browser app | allowed |
| react-dom | 18.3.1 | MIT | browser app | allowed |
| react-is | 16.13.1 | MIT | browser app, through recharts | allowed |
| react-is | 18.3.1 | MIT | browser app, through recharts | allowed |
| react-router | 6.30.4 | MIT | through react-router-dom, which no file under src/ imports | allowed |
| react-router-dom | 6.30.4 | MIT | listed in package.json; no file under src/ imports it | allowed |
| react-smooth | 4.0.4 | MIT | browser app, through recharts | allowed |
| react-transition-group | 4.4.5 | BSD-3-Clause | browser app, through recharts | allowed |
| recharts | 2.15.4 | MIT | browser app | allowed |
| recharts-scale | 0.4.5 | MIT | browser app, through recharts | allowed |
| scheduler | 0.23.2 | MIT | browser app, through react-dom | allowed |
| tiny-invariant | 1.3.3 | MIT | browser app, through recharts | allowed |
| victory-vendor | 36.9.2 | MIT AND ISC | browser app, through recharts | allowed |
| zustand | 5.0.14 | MIT | browser app | allowed |

## Accepted by a person

| Package | Licence | Accepted by | Date | Why |
|---|---|---|---|---|
| certifi | MPL-2.0 | Sean Creighton | 2026-10-14 | Mozilla's bundle of trusted HTTPS certificates, read unmodified by httpx and httpcore when Intake calls Europe PMC and Crossref; MPL-2.0 binds only the files it covers. |
