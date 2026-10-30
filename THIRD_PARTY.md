# Third-party software

Every package openFerment's service and browser app run on: each Python distribution
`core/uv.lock` installs, its extras included, and every JavaScript production
dependency, with its version, the licence its own metadata states, and the part of
openFerment that uses it. The JavaScript build and test tools (`devDependencies`) are
left out. `pnpm check:licences` (`scripts/check-licences.py`, OF-BLD-014 §1.2) writes
this file from what is installed and fails while the committed copy is stale. The
accepted licence strings, and every package a person accepted, are in
`core/licences.toml`.

## The service and its tests (`core/`)

| Package | Version | Licence | Used by | Passes as |
|---|---|---|---|---|
| alembic | 1.20.1 | MIT | service | allowed |
| annotated-doc | 0.0.5 | MIT | service, through fastapi | allowed |
| annotated-types | 0.8.0 | MIT | service, through anthropic, fastapi, pydantic | allowed |
| ansicolors | 1.1.8 | ISC | the geneOS worker, through biorefineries, biosteam | allowed |
| anthropic | 1.0.0 | MIT | service | allowed |
| anyio | 4.14.2 | MIT | service, through anthropic, fastapi, httpx, uvicorn | allowed |
| appdirs | 1.4.4 | MIT | the geneOS worker, through cobra | allowed |
| asttokens | 3.0.2 | Apache 2.0 | the geneOS worker, through biorefineries, biosteam | allowed |
| asyncpg | 0.32.0 | Apache-2.0 | service | allowed |
| attrs | 26.1.0 | MIT | extra agent, through mcp | allowed |
| biopython | 1.88 | LicenseRef-Biopython-License-Agreement | service | allowed |
| biorefineries | 2.35.1 | MIT | the geneOS worker | allowed |
| biosteam | 2.54.0 | MIT | the geneOS worker | allowed |
| certifi | 2026.7.22 | MPL-2.0 | service, through httpx | accepted by Sean Creighton on 2026-10-14 |
| cffi | 2.1.1 | MIT-0 | extra agent, through mcp | allowed |
| chaospy | 4.3.21 | MIT license | the geneOS worker, through biorefineries, biosteam | allowed |
| charset-normalizer | 3.5.2 | MIT | extra rag, through fastembed | allowed |
| chemicals | 1.5.2 | MIT | the geneOS worker, through biorefineries, biosteam | allowed |
| click | 8.4.2 | BSD-3-Clause | service, through uvicorn | allowed |
| cloudpickle | 3.1.2 | BSD-3-Clause | the geneOS worker, through biorefineries | allowed |
| cobra | 0.32.1 | LGPL-2.0-or-later OR GPL-2.0-or-later | the geneOS worker | accepted by Sean Creighton on 2026-10-15 |
| colorama | 0.4.6 | License :: OSI Approved :: BSD License | service, through uvicorn | allowed |
| colorpalette | 0.3.3 | MIT | the geneOS worker, through biorefineries, biosteam | allowed |
| contourpy | 1.4.0 | BSD-3-Clause | the geneOS worker, through biorefineries, biosteam | allowed |
| CoolProp | 8.0.0 | MIT | the geneOS worker, through biorefineries, biosteam | allowed |
| cryptography | 50.0.2 | Apache-2.0 OR BSD-3-Clause | extra agent, through mcp | allowed |
| cycler | 0.12.1 | License :: OSI Approved :: BSD License | the geneOS worker, through biorefineries, biosteam | allowed |
| depinfo | 2.2.0 | Apache-2.0 | the geneOS worker, through cobra | allowed |
| dill | 0.4.1 | BSD-3-Clause | the geneOS worker, through biorefineries | allowed |
| docstring_parser | 0.18.0 | MIT | service, through anthropic | allowed |
| et_xmlfile | 2.0.0 | MIT | the geneOS worker, through biorefineries, biosteam | allowed |
| executing | 2.3.0 | MIT | the geneOS worker, through biorefineries, biosteam | allowed |
| fastapi | 0.141.1 | MIT | service | allowed |
| fastembed | 0.9.0 | Apache-2.0 | extra rag | allowed |
| filelock | 4.2.0 | MIT | extra rag, through fastembed | allowed |
| flatbuffers | 25.12.19 | Apache 2.0 | extra rag, through fastembed | allowed |
| flexcache | 0.3 | License :: OSI Approved :: BSD License | the geneOS worker, through biorefineries, biosteam | allowed |
| flexparser | 0.4 | BSD-3-Clause | the geneOS worker, through biorefineries, biosteam | allowed |
| flexsolve | 0.5.10 | MIT | the geneOS worker, through biorefineries, biosteam | allowed |
| fluids | 1.3.1 | MIT | the geneOS worker, through biorefineries, biosteam | allowed |
| fonttools | 4.67.0 | MIT | the geneOS worker, through biorefineries, biosteam | allowed |
| fsspec | 2026.9.0 | BSD-3-Clause | extra rag, through fastembed | allowed |
| future | 1.0.0 | MIT | the geneOS worker, through cobra | allowed |
| graphviz | 0.21 | MIT | the geneOS worker, through biorefineries, biosteam | allowed |
| greenlet | 3.5.6 | MIT AND PSF-2.0 | service, through sqlalchemy | allowed |
| h11 | 0.16.0 | MIT | service, through anthropic, httpx, uvicorn | allowed |
| hensmith | 0.1.2 | MIT | the geneOS worker, through biorefineries, biosteam | allowed |
| hf-xet | 1.7.0 | Apache-2.0 | extra rag, through fastembed | allowed |
| httpcore | 1.0.9 | BSD-3-Clause | service, through httpx | allowed |
| httpcore2 | 2.12.0 | BSD-3-Clause | service, through anthropic | allowed |
| httptools | 0.8.0 | MIT | service, through uvicorn | allowed |
| httpx | 0.28.1 | BSD-3-Clause | service | allowed |
| httpx2 | 2.12.0 | BSD-3-Clause | service, through anthropic | allowed |
| huggingface_hub | 1.33.0 | Apache-2.0 | extra rag, through fastembed | allowed |
| idna | 3.19 | BSD-3-Clause | service, through anthropic, fastapi, httpx, uvicorn | allowed |
| ImageIO | 2.38.1 | BSD-2-Clause | the geneOS worker, through biorefineries, biosteam | allowed |
| importlib_metadata | 9.0.1 | Apache-2.0 | the geneOS worker, through biorefineries, biosteam | allowed |
| iniconfig | 2.3.0 | MIT | tests, through pytest | allowed |
| ipython | 9.17.1 | BSD-3-Clause | the geneOS worker, through biorefineries, biosteam | allowed |
| ipython_pygments_lexers | 1.1.1 | License :: OSI Approved :: BSD License | the geneOS worker, through biorefineries, biosteam | allowed |
| jedi | 0.20.1 | MIT | the geneOS worker, through biorefineries, biosteam | allowed |
| jiter | 0.16.0 | MIT | service, through anthropic | allowed |
| joblib | 1.6.0 | BSD-3-Clause | the geneOS worker, through biorefineries | allowed |
| jsonschema | 4.26.0 | MIT | extra agent, through mcp | allowed |
| jsonschema-specifications | 2025.9.1 | MIT | extra agent, through mcp | allowed |
| kiwisolver | 1.5.1 | License :: OSI Approved :: BSD License | the geneOS worker, through biorefineries, biosteam | allowed |
| llvmlite | 0.50.0 | BSD-2-Clause AND Apache-2.0 WITH LLVM-exception | the geneOS worker, through biorefineries, biosteam | allowed |
| loguru | 0.7.3 | License :: OSI Approved :: MIT License | extra rag, through fastembed | allowed |
| Mako | 1.4.3 | MIT | service, through alembic | allowed |
| markdown-it-py | 4.2.0 | License :: OSI Approved :: MIT License | the geneOS worker, through cobra | allowed |
| MarkupSafe | 3.0.4 | BSD-3-Clause | service, through alembic | allowed |
| matplotlib | 3.11.2 | License :: OSI Approved :: Python Software Foundation License | the geneOS worker, through biorefineries, biosteam | allowed |
| matplotlib-inline | 0.2.2 | BSD-3-Clause | the geneOS worker, through biorefineries, biosteam | allowed |
| mcp | 2.3.0 | MIT | extra agent | allowed |
| mcp-types | 2.3.0 | MIT | extra agent, through mcp | allowed |
| mdurl | 0.1.2 | License :: OSI Approved :: MIT License | the geneOS worker, through cobra | allowed |
| mmh3 | 5.3.1 | License :: OSI Approved :: MIT License | extra rag, through fastembed | allowed |
| mpmath | 1.3.0 | License :: OSI Approved :: BSD License | the geneOS worker, through cobra | allowed |
| multiprocess | 0.70.19 | BSD-3-Clause | the geneOS worker, through biorefineries | allowed |
| narwhals | 2.27.1 | MIT | the geneOS worker, through biorefineries | allowed |
| numba | 0.68.0 | License :: OSI Approved :: BSD License | the geneOS worker, through biorefineries, biosteam | allowed |
| numpoly | 1.3.9 | BSD-2-Clause | the geneOS worker, through biorefineries, biosteam | allowed |
| numpy | 2.5.2 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | service, through biopython, rank-bm25 | allowed |
| onnxruntime | 1.31.0 | MIT License | extra rag, through fastembed | allowed |
| openpyxl | 3.1.5 | MIT | the geneOS worker, through biorefineries, biosteam | allowed |
| opentelemetry-api | 1.45.1 | Apache-2.0 | extra agent, through mcp | allowed |
| optlang | 1.9.1 | Apache-2.0 | the geneOS worker, through cobra | allowed |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause | tests, through pytest; extra rag, through fastembed; the geneOS worker, through biorefineries, biosteam | allowed |
| pandas | 2.3.3 | License :: OSI Approved :: BSD License | the geneOS worker, through biorefineries, biosteam, cobra | allowed |
| parso | 0.8.7 | MIT | the geneOS worker, through biorefineries, biosteam | allowed |
| pexpect | 4.9.0 | ISC license | the geneOS worker, through biorefineries, biosteam | allowed |
| pillow | 12.3.0 | MIT-CMU | extra rag, through fastembed; the geneOS worker, through biorefineries, biosteam | allowed |
| Pint | 0.26.1 | License :: OSI Approved :: BSD License | the geneOS worker, through biorefineries, biosteam | allowed |
| platformdirs | 4.13.0 | MIT | the geneOS worker, through biorefineries, biosteam | allowed |
| pluggy | 1.6.0 | MIT | tests, through pytest | allowed |
| prompt_toolkit | 3.0.53 | License :: OSI Approved :: BSD License | the geneOS worker, through biorefineries, biosteam | allowed |
| protobuf | 7.36.2 | 3-Clause BSD License | extra rag, through fastembed | allowed |
| psutil | 7.2.2 | BSD-3-Clause | the geneOS worker, through biorefineries, biosteam | allowed |
| ptyprocess | 0.7.0 | License :: OSI Approved :: ISC License (ISCL) | the geneOS worker, through biorefineries, biosteam | allowed |
| pure_eval | 0.2.4 | MIT | the geneOS worker, through biorefineries, biosteam | allowed |
| py_rust_stemmers | 0.1.8 | no licence metadata | extra rag, through fastembed | accepted by Sean Creighton on 2026-10-15 |
| pycparser | 3.11 | BSD-3-Clause | extra agent, through mcp | allowed |
| pydantic | 2.13.4 | MIT | service | allowed |
| pydantic_core | 2.46.4 | MIT | service, through anthropic, fastapi, pydantic | allowed |
| pydot | 4.0.1 | MIT | the geneOS worker, through biorefineries, biosteam | allowed |
| pyglet | 2.1.19 | no licence metadata | the geneOS worker, through biorefineries, biosteam | accepted by Sean Creighton on 2026-10-15 |
| Pygments | 2.21.0 | BSD-2-Clause | tests, through pytest; the geneOS worker, through biorefineries, biosteam, cobra | allowed |
| PyJWT | 2.15.1 | MIT | extra agent, through mcp | allowed |
| pyparsing | 3.3.3 | MIT | the geneOS worker, through biorefineries, biosteam | allowed |
| pypdf | 6.21.1 | BSD-3-Clause | service | allowed |
| pytest | 9.1.1 | MIT | tests | allowed |
| python-dateutil | 2.9.0.post0 | License :: OSI Approved :: BSD License | the geneOS worker, through biorefineries, biosteam, cobra | allowed |
| python-dotenv | 1.2.3 | BSD-3-Clause | service | allowed |
| python-libsbml | 5.21.2 | LGPL | the geneOS worker, through cobra | accepted by Sean Creighton on 2026-10-15 |
| python-multipart | 0.0.32 | Apache-2.0 | extra agent, through mcp | allowed |
| pytz | 2026.5 | MIT | the geneOS worker, through biorefineries, biosteam, cobra | allowed |
| PyYAML | 6.0.3 | MIT | service | allowed |
| rank-bm25 | 0.2.2 | Apache2.0 | service | allowed |
| referencing | 0.37.0 | MIT | extra agent, through mcp | allowed |
| requests | 2.34.2 | Apache-2.0 | extra rag, through fastembed | allowed |
| rich | 15.0.0 | MIT | the geneOS worker, through cobra | allowed |
| rpds-py | 2026.9.1 | MIT | extra agent, through mcp | allowed |
| ruamel.yaml | 0.19.1 | MIT | the geneOS worker, through cobra | allowed |
| SALib | 1.6.0 | MIT | the geneOS worker, through biorefineries | allowed |
| scikit-learn | 1.9.1 | BSD-3-Clause | the geneOS worker, through biorefineries | allowed |
| scipy | 1.18.1 | License :: OSI Approved :: BSD License | the geneOS worker | allowed |
| seaborn | 0.13.2 | License :: OSI Approved :: BSD License | the geneOS worker, through biorefineries | allowed |
| setuptools | 84.0.0 | MIT | the geneOS worker, through biorefineries, biosteam | allowed |
| six | 1.17.0 | MIT | the geneOS worker, through biorefineries, biosteam, cobra | allowed |
| sniffio | 1.3.1 | MIT OR Apache-2.0 | service, through anthropic | allowed |
| SQLAlchemy | 2.1.6 | MIT | service | allowed |
| sse-starlette | 3.5.0 | BSD-3-Clause | extra agent, through mcp | allowed |
| stack-data | 0.6.3 | MIT | the geneOS worker, through biorefineries, biosteam | allowed |
| starlette | 1.6.0 | BSD-3-Clause | service, through fastapi | allowed |
| swiglpk | 5.0.13 | GPL v3 | the geneOS worker, through cobra | accepted by Sean Creighton on 2026-10-15 |
| sympy | 1.14.0 | License :: OSI Approved :: BSD License | the geneOS worker, through cobra | allowed |
| thermo | 0.6.1 | MIT | the geneOS worker, through biorefineries, biosteam | allowed |
| thermosteam | 0.54.2 | MIT | the geneOS worker, through biorefineries, biosteam | allowed |
| threadpoolctl | 3.7.0 | BSD-3-Clause | the geneOS worker, through biorefineries | allowed |
| tokenizers | 0.23.3 | License :: OSI Approved :: Apache Software License | extra rag, through fastembed | allowed |
| tqdm | 4.70.1 | MPL-2.0 AND MIT | extra rag, through fastembed | accepted by Sean Creighton on 2026-10-15 |
| traitlets | 5.16.1 | License :: OSI Approved :: BSD License | the geneOS worker, through biorefineries, biosteam | allowed |
| truststore | 0.10.4 | MIT | service, through anthropic | allowed |
| typing_extensions | 4.16.0 | PSF-2.0 | service, through alembic, anthropic, fastapi, httpx, pydantic, sqlalchemy, uvicorn | allowed |
| typing-inspection | 0.4.4 | MIT | service, through anthropic, fastapi, pydantic | allowed |
| tzdata | 2026.5 | Apache-2.0 | the geneOS worker, through biorefineries, biosteam, cobra | allowed |
| urllib3 | 2.8.0 | MIT | extra rag, through fastembed | allowed |
| uvicorn | 0.52.4 | BSD-3-Clause | service | allowed |
| uvloop | 0.22.1 | MIT License | service, through uvicorn | allowed |
| watchfiles | 1.2.0 | MIT | service, through uvicorn | allowed |
| wcwidth | 0.9.2 | License :: OSI Approved :: MIT License | the geneOS worker, through biorefineries, biosteam | allowed |
| websockets | 17.0.1 | BSD-3-Clause | service, through uvicorn | allowed |
| xlrd | 2.0.2 | License :: OSI Approved :: BSD License | the geneOS worker, through biorefineries, biosteam | allowed |
| zipp | 4.1.1 | MIT | the geneOS worker, through biorefineries, biosteam | allowed |

`openferment-core`, the project itself, is skipped by name: the repository declares no licence yet.

## The browser app (JavaScript production dependencies)

| Package | Version | Licence | Used by | Passes as |
|---|---|---|---|---|
| @fontsource/ibm-plex-mono | 5.3.0 | OFL-1.1 | browser app | allowed |
| @fontsource/ibm-plex-sans | 5.3.0 | OFL-1.1 | browser app | allowed |
| @fontsource/spectral | 5.3.0 | OFL-1.1 | browser app | allowed |
| @types/prop-types | 15.7.15 | MIT | browser app, through zustand | allowed |
| @types/react | 18.3.31 | MIT | browser app, through zustand | allowed |
| csstype | 3.2.3 | MIT | browser app, through zustand | allowed |
| js-tokens | 4.0.0 | MIT | browser app, through lucide-react | allowed |
| loose-envify | 1.4.0 | MIT | browser app, through lucide-react, react-dom | allowed |
| lucide-react | 0.462.0 | ISC | browser app | allowed |
| react | 18.3.1 | MIT | browser app | allowed |
| react-dom | 18.3.1 | MIT | browser app | allowed |
| scheduler | 0.23.2 | MIT | browser app, through react-dom | allowed |
| zustand | 5.0.14 | MIT | browser app | allowed |

## Accepted by a person

| Package | Licence | Accepted by | Date | Why |
|---|---|---|---|---|
| certifi | MPL-2.0 | Sean Creighton | 2026-10-14 | Mozilla's bundle of trusted HTTPS certificates, read unmodified by httpx and httpcore when Intake calls Europe PMC and Crossref; MPL-2.0 binds only the files it covers. |
| cobra | LGPL-2.0-or-later OR GPL-2.0-or-later | Sean Creighton | 2026-10-15 | Flux balance analysis for geneOS's yield ceilings, imported in the geneOS worker process alone; accepted under D4 for this research prototype, to revisit before hosted or commercial use. |
| py-rust-stemmers | no licence metadata | Sean Creighton | 2026-10-15 | fastembed's word stemmer for its sparse models, used unmodified in the rag extra; its metadata states no licence, and its repository (github.com/qdrant/py-rust-stemmers) carries an MIT LICENSE, read 2026-10-15. |
| pyglet | no licence metadata | Sean Creighton | 2026-10-15 | thermosteam's dependency, pulled in by BioSTEAM in the sim extra and loaded in the Proforma worker; its metadata states no licence, and its repository (github.com/pyglet/pyglet) carries a BSD 3-clause LICENSE, read 2026-10-15. |
| python-libsbml | LGPL | Sean Creighton | 2026-10-15 | Reads SBML model files for cobra in the geneOS worker process alone; accepted under D4 for this research prototype, to revisit before hosted or commercial use. |
| swiglpk | GPL v3 | Sean Creighton | 2026-10-15 | GLPK, cobra's default linear-programming solver, loaded in the geneOS worker process alone; accepted under D4 for this research prototype, to revisit before hosted or commercial use. |
| tqdm | MPL-2.0 AND MIT | Sean Creighton | 2026-10-15 | The progress bar fastembed and huggingface_hub show while a model file downloads, used unmodified in the rag extra; MPL-2.0 binds only the files it covers. |

## Model files read as data

Downloaded into `core/data/models/`, which git ignores, or shipped inside a package; read by the
geneOS worker alone (OF-BLD-014 E.9).

| File | Licence | Source | Revision | sha256 | Accepted by | Date | Why |
|---|---|---|---|---|---|---|---|
| Yeast9 | CC-BY-4.0 | github.com/SysBioChalmers/yeast-GEM, model/yeast-GEM.xml (release v9.1.1) | 2d594ae1c4a2d550ccef120d96a58c7bbf586255 | 30842b15eefb0ef7e36cbdea86a9efddfacf69a871c8b054165faa9af9f6c8eb | Sean Creighton | 2026-10-20 | Yeast9, the consensus genome-scale reconstruction of Saccharomyces cerevisiae (Zhang et al., Molecular Systems Biology 2024, doi:10.1038/s44320-024-00060-7), fetched by pnpm geneos:fetch into core/data/models/ and read as data by the geneOS worker for an ethanol ceiling. Sean named it in his instruction of 2026-10-20 for the yeast-ethanol demo. The repository's LICENSE.md is CC-BY-4.0, read 2026-10-20: a use credits Zhang et al. and the yeast-GEM community, which the shelf's notes and every result's basis do. |
| iMM904 | BiGG Models terms: educational, research and non-profit use; commercial use by agreement with UC San Diego | bigg.ucsd.edu/static/models/iMM904.xml (BiGG Models; Mo, Palsson and Herrgård, BMC Systems Biology 2009, PMID 19321003) | ETag "017c86841952cc365f20a8b466292b31", Last-Modified 2019-11-01 | a4bcff4f8f2228a5b1553264c3bcb1e8a8093907754446007f3f3b529d29d3e1 | Sean Creighton | 2026-10-20 | The genome-scale reconstruction of Saccharomyces cerevisiae S288C as BiGG Models serves it, fetched by pnpm geneos:fetch into core/data/models/ and read as data by the geneOS worker for an ethanol ceiling. Sean named it in his instruction of 2026-10-20 for the yeast-ethanol demo. BiGG's terms (bigg.ucsd.edu/license, read 2026-10-20) permit educational, research and non-profit use without fee, require the copyright notice and the paragraphs after it to travel with every copy, and leave commercial use to an agreement with UC San Diego's Technology Transfer and Intellectual Property Services. Not a permissive licence: the file is not committed, and data-sync carries no model file, so no copy leaves the machine that fetched it. Commercial use is a question for Sean before any such use. |
