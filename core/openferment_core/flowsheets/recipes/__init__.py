"""openFerment's flowsheets as SFF recipes (ADR-003; execution prompt §8.3).

Each directory here is a flowsheet's recipe in the SFF toolkit's
model-directory shape: `load.py` (builds and returns the system and its
TEA; the flowsheet module builds every case through it), `extended_metadata.yaml`
(what a person knows of the flowsheet that a system cannot carry) and
`environment.yaml` (a conda environment pinned to the versions this project
runs, so `pisces_sff.export_model` can rebuild the plant where conda exists;
openFerment's replay check is the verification that counts, and earning the
toolkit's `reproducible` tag is off by default).

`environment.yaml` is written from core/uv.lock, never edited:

    python -m openferment_core.flowsheets.recipes environment

and a test holds each to the lock. Nothing here imports BioSTEAM.
"""
from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

HERE = Path(__file__).parent
LOCK = HERE.parents[2] / "uv.lock"
# What a recipe's environment installs: the simulator, the package of plants,
# the property engine, and what the SFF toolkit's runner itself imports.
ROOTS = ("biosteam", "biorefineries", "thermosteam", "jsonschema", "pyyaml")


def lowest_python(lock: Path = LOCK) -> str:
    """The lowest minor version of Python core/uv.lock resolves for (its
    `requires-python`), which a recipe's environment pins and its markers are
    read for: every machine that writes the file writes the same one,
    whichever Python it runs."""
    said = tomllib.loads(lock.read_text(encoding="utf-8")).get("requires-python", "")
    found = re.match(r"\s*>=\s*(\d+)\.(\d+)", said)
    if found is None:
        raise ValueError(f"core/uv.lock's requires-python ({said!r}) names no lowest version")
    return f"{found.group(1)}.{found.group(2)}"


# The Python a recipe's environment pins (conda takes the minor version).
PYTHON = lowest_python()


def recipes() -> list[Path]:
    return sorted(p for p in HERE.iterdir() if p.is_dir() and (p / "load.py").is_file())


def _applies(marker: str | None) -> bool:
    """Whether a dependency's environment marker holds on Linux or macOS, the
    hosts a recipe's environment is built on."""
    if not marker:
        return True
    from packaging.markers import Marker

    m = Marker(marker)
    return any(m.evaluate({"sys_platform": platform, "platform_system": system, "os_name": "posix",
                           "python_version": PYTHON, "extra": ""})
               for platform, system in (("linux", "Linux"), ("darwin", "Darwin")))


def pins(lock: Path = LOCK) -> list[tuple[str, str]]:
    """The distributions ROOTS needs, with the versions core/uv.lock pins:
    each root and every dependency it reaches whose marker holds here."""
    raw = tomllib.loads(lock.read_text(encoding="utf-8"))
    by_name = {p["name"]: p for p in raw["package"]}
    seen: dict[str, str] = {}
    stack = list(ROOTS)
    while stack:
        name = stack.pop()
        if name in seen or name not in by_name:
            continue
        entry = by_name[name]
        seen[name] = entry["version"]
        for dep in entry.get("dependencies") or []:
            if _applies(dep.get("marker")):
                stack.append(dep["name"])
    return sorted(seen.items())


def environment_text(name: str, lock: Path = LOCK) -> str:
    lines = [
        f"# The pinned environment for openFerment's {name} recipe, written by",
        "# `python -m openferment_core.flowsheets.recipes environment` from core/uv.lock:",
        "# the versions this project runs. Regenerate it; do not edit it.",
        "#",
        "# `pisces_sff.export_model` builds this environment and runs load.py inside it.",
        "# Every distribution the plant imports is listed with its pin, so it can be",
        "# built with dependency resolution off, as the toolkit's own recipes advise:",
        "#",
        "#   PIP_NO_DEPS=1 conda env create -f environment.yaml",
        "#",
        "# `name` is ignored by the harness, which names the environment by its key.",
        f"name: sff-openferment-{name.replace('_', '-')}",
        "channels:",
        "  - defaults",
        "dependencies:",
        f"  - python={PYTHON}",
        "  - pip",
        "  - pip:",
    ]
    lines += [f"      - {dist}=={version}" for dist, version in pins(lock)]
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    if argv == ["environment"]:
        for recipe in recipes():
            path = recipe / "environment.yaml"
            path.write_text(environment_text(recipe.name), encoding="utf-8")
            print(f"{path.relative_to(HERE.parents[2])}: {len(pins())} distributions pinned")
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
