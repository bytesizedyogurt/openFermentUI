"""Programs, as the service reads them (OF-BLD-016 §2.1, E.1′, E.2′).

A program is data: the corpus threads that are its papers, a name, and
whether it is active or archived. `src/data/programs.ts` declares three —
casein (threads A to O, archived), PHA (thread P, archived), yeast ethanol
(thread Q, active) — and `pnpm export:corpus` writes them into corpus.json
and modules.json, so this module never holds a copy of its own.

Which program an entity belongs to follows the browser's `programOf`
(src/store.ts): a paper by its thread letter, a record or a candidate by the
paper it cites, and every module row (molecule, runbook, protocol, host,
scenario, lesson) by the `program` the export wrote on it, which `programOf`
computed. None means general: it always shows.

The evidence pool, retrieval, the coverage pass and the read tools ask
`shows(...)` with the caller's `includeArchived` (OF-BLD-016 §2.3); nothing
here filters on its own.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from .corpus import DATA as CORPUS_PATH
from .models import Program

MODULES_PATH = Path(__file__).parent / "data" / "modules.json"

Kind = Literal["paper", "record", "strain", "product", "scenario", "protocol", "runbook", "lesson"]

# Where each module-row kind sits in modules.json.
_ROWS: dict[str, tuple[str, str]] = {
    "product": ("dominion", "molecules"),
    "runbook": ("runbooks", "runbooks"),
    "protocol": ("runbooks", "protocols"),
    "strain": ("geneos", "hosts"),
    "scenario": ("proforma", "scenarios"),
    "lesson": ("primer", "lessons"),
}

_PAPER_ID = re.compile(r"^([A-Z])\d")


def _read(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Generate it with `pnpm export:corpus` from the repository root — "
            "the programs live in src/data/programs.ts and this is a projection of them."
        )
    return json.loads(path.read_text())


@lru_cache(maxsize=4)
def _programs(path: str) -> tuple[Program, ...]:
    return tuple(Program.model_validate(p) for p in _read(Path(path)).get("programs") or ())


def programs(path: Path | str | None = None) -> list[Program]:
    """Every program corpus.json declares, in its order."""
    return list(_programs(str(path or CORPUS_PATH)))


def active_programs(path: Path | str | None = None) -> list[Program]:
    return [p for p in programs(path) if p.status == "active"]


def program_by_id(program_id: str | None, path: Path | str | None = None) -> Program | None:
    return next((p for p in programs(path) if p.id == program_id), None) if program_id else None


def program_of_letter(letter: str, path: Path | str | None = None) -> str | None:
    return next((p.id for p in programs(path) if letter in p.letters), None)


def program_of_paper(paper_id: str, path: Path | str | None = None) -> str | None:
    """A paper's program, by its id's thread letter ('P12' → 'pha')."""
    m = _PAPER_ID.match(paper_id or "")
    return program_of_letter(m.group(1), path) if m else None


def program_of_record(record: dict[str, Any], path: Path | str | None = None) -> str | None:
    """A record's or a candidate's program: the program of the paper it cites."""
    return program_of_paper(str(record.get("paperId") or ""), path)


def is_archived(program_id: str | None, path: Path | str | None = None) -> bool:
    """Whether a program is archived. A general entity (None) never is."""
    p = program_by_id(program_id, path)
    return p is not None and p.status == "archived"


def archived_ids(path: Path | str | None = None) -> frozenset[str]:
    return frozenset(p.id for p in programs(path) if p.status == "archived")


@lru_cache(maxsize=4)
def _row_programs(path: str) -> dict[str, dict[str, str | None]]:
    proj = _read(Path(path))
    out: dict[str, dict[str, str | None]] = {}
    for kind, (module, key) in _ROWS.items():
        out[kind] = {str(r["id"]): r.get("program") for r in (proj.get(module) or {}).get(key) or []}
    return out


def program_of(kind: Kind, entity_id: str, *, corpus_path: Path | str | None = None,
               modules_path: Path | str | None = None) -> str | None:
    """The program an entity belongs to, or None when it is general or unknown.

    `record` looks the id up in corpus.json; a candidate the extractor wrote
    is not there, and is asked about with `program_of_record(candidate)`.
    """
    if kind == "paper":
        return program_of_paper(entity_id, corpus_path)
    if kind == "record":
        from .corpus import load_corpus

        record = load_corpus(str(corpus_path) if corpus_path else None).record(entity_id)
        return program_of_record(record, corpus_path) if record else None
    return _row_programs(str(modules_path or MODULES_PATH)).get(kind, {}).get(entity_id)


def shows(kind: Kind, entity_id: str, include_archived: bool = False, **paths: Any) -> bool:
    """Whether an entity shows: it is general, its program is active, or the
    caller asked for archived programs too."""
    if include_archived:
        return True
    corpus_path = paths.get("corpus_path")
    return not is_archived(program_of(kind, entity_id, **paths), corpus_path)


def hides(program_id: str | None, include_archived: bool = False) -> bool:
    """Whether an entity of this program is left out: it belongs to an
    archived program and the caller did not ask for archived programs."""
    return not include_archived and is_archived(program_id)


# A paper id inside a record's or a candidate's id: `r-B5-3`, `cl1-P12-…`.
_PAPER_IN_ID = re.compile(r"(?:^|-)([A-Z]\d+)(?=-|$)")


def program_of_record_id(record_id: str, lookup: Any = None) -> str | None:
    """A record's program by its id: the record `lookup(id)` returns when
    there is one, else the paper id the record id carries."""
    record = lookup(record_id) if lookup is not None else None
    if record:
        return program_of_record(record)
    m = _PAPER_IN_ID.search(record_id or "")
    return program_of_paper(m.group(1)) if m else None


def program_of_model(model_id: str | None) -> str | None:
    """A geneOS shelf model's program: its host strain's."""
    from .geneos_models import SHELF

    shelf = SHELF.get(model_id or "")
    return program_of("strain", shelf.host) if shelf is not None and shelf.host else None


def program_of_artifact(artifact: Any, record_lookup: Any = None) -> str | None:
    """A computed artifact's program, from what its inputs name: a record (by
    the paper it cites), a shelf model (by its host), a product or a strain
    (by their own field). An archived program found among them wins, so a
    value computed from an archived program's records hides with them;
    anything else computed is general (a benchmark, a fit of a deposition)."""
    found: list[str] = []
    for i in getattr(artifact, "inputs", None) or []:
        src = i.source
        if src.kind == "record" and src.id:
            found.append(program_of_record_id(src.id, record_lookup) or "")
        elif src.kind == "model" and src.id:
            found.append(program_of_model(src.id) or "")
        if isinstance(i.value, str) and i.name in ("product", "productId"):
            found.append(program_of("product", i.value) or "")
        if isinstance(i.value, str) and i.name in ("strain", "strainId", "host"):
            found.append(program_of("strain", i.value) or "")
    found = [p for p in found if p]
    return next((p for p in found if is_archived(p)), found[0] if found else None)


def clear_cache() -> None:
    """Forget what was read, after `pnpm export:corpus` rewrote the projections."""
    _programs.cache_clear()
    _row_programs.cache_clear()
