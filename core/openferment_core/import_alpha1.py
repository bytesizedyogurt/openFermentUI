"""Carry an alpha 1.0 data directory into a new project (stage 2; ADR-001).

Before alpha 2.0 a live instance kept its records as files under core/data/:
`biorepo.json`, `guild.json`, `checks.json`, `practice.json`,
`proposals.json`, `audit.jsonl`, `artifacts/`, `candidates/` (with `hand/`)
and `pureos-trains.json`. This command makes a new project and writes those
records into its rows as they stand, in the shape each store writes them, so
nothing a person decided, signed or recorded is left behind when the
instance moves to PostgreSQL:

    python -m openferment_core.import_alpha1 --name "Alpha 1.0 records" --by "Sean Creighton" [--data core/data]

(`pnpm db:import-alpha1 --name … --by …`.) Every file is read and checked
before anything is written, and everything is written in one transaction: an
import lands whole or not at all. The stores' rules are not run again on old
records (the seed several of them cite is gone); each ran when its record was
written. The files are left where they are, to be moved aside by a person.
The day's spend (`spend.json`) is not carried: the cap starts again the day
the instance moves.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError
from sqlalchemy import insert, update

from . import db, projects
from .db import models as t
from .db import rows
from .models import (
    Artifact,
    AuditEntry,
    BioRepo,
    Checks,
    ExtractResponse,
    Guild,
    KeptTrains,
    Practice,
    ProjectCreate,
    Proposals,
)

CORE = Path(__file__).parent.parent


class ImportRefused(ValueError):
    """A data directory that cannot be carried whole, in words."""


@dataclass
class Found:
    """What a data directory holds, read and checked, nothing written yet."""

    repo: BioRepo = field(default_factory=BioRepo)
    guild: Guild | None = None
    checks: Checks = field(default_factory=Checks)
    practice: Practice = field(default_factory=Practice)
    proposals: Proposals = field(default_factory=Proposals)
    audit: list[AuditEntry] = field(default_factory=list)
    artifacts: list[Artifact] = field(default_factory=list)
    extracted: list[ExtractResponse] = field(default_factory=list)
    hand: list[ExtractResponse] = field(default_factory=list)
    kept: KeptTrains = field(default_factory=KeptTrains)

    def counts(self) -> dict[str, int]:
        return {
            "decisions": len(self.repo.decisions),
            "people": len(self.guild.people) if self.guild else 0,
            "entries": len(self.guild.evidence) if self.guild else 0,
            "checks": len(self.checks.checks),
            "practice scenarios": len(self.practice.scenarios),
            "practice sessions": len(self.practice.sessions),
            "proposals": len(self.proposals.proposals),
            "audit rows": len(self.audit),
            "artifacts": len(self.artifacts),
            "extractions": len(self.extracted),
            "hand-written candidate files": len(self.hand),
            "kept trains": len(self.kept.trains),
        }


def _model(path: Path, model: type[BaseModel]) -> Any:
    try:
        return model.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError, ValueError) as e:
        raise ImportRefused(f"{path} cannot be read as {model.__name__}: {str(e).splitlines()[0]}") from None


def read(data: Path) -> Found:
    """Read and check every alpha 1.0 store under `data`; refuse the whole
    directory, naming the file, when one cannot be read."""
    if not data.is_dir():
        raise ImportRefused(f"{data} is not a directory")
    found = Found()
    if (data / "biorepo.json").is_file():
        found.repo = _model(data / "biorepo.json", BioRepo)
    if (data / "guild.json").is_file():
        found.guild = _model(data / "guild.json", Guild)
    if (data / "checks.json").is_file():
        found.checks = _model(data / "checks.json", Checks)
    if (data / "practice.json").is_file():
        found.practice = _model(data / "practice.json", Practice)
    if (data / "proposals.json").is_file():
        found.proposals = _model(data / "proposals.json", Proposals)
    if (data / "pureos-trains.json").is_file():
        found.kept = _model(data / "pureos-trains.json", KeptTrains)
    if (data / "audit.jsonl").is_file():
        for n, line in enumerate((data / "audit.jsonl").read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                found.audit.append(AuditEntry.model_validate(json.loads(line)))
            except (ValidationError, ValueError) as e:
                raise ImportRefused(f"{data / 'audit.jsonl'} line {n} cannot be read: {str(e).splitlines()[0]}") from None
    found.artifacts = [_model(p, Artifact) for p in sorted((data / "artifacts").glob("*.json"))]
    found.extracted = [_model(p, ExtractResponse) for p in sorted((data / "candidates").glob("*.json"))]
    found.hand = [_model(p, ExtractResponse) for p in sorted((data / "candidates" / "hand").glob("*.json"))]
    return found


async def _write(found: Found, asked: ProjectCreate) -> str:
    async with db.session() as s:
        made = await projects._create(asked)
        pid = made.id
        records = {c.id: c for c in found.repo.records}
        for record_id, decision in found.repo.decisions.items():
            copy = records.get(record_id)
            await s.execute(insert(t.decisions).values(
                project_id=pid, record_id=record_id, body=decision.model_dump(mode="json", exclude_none=True),
                record=copy.model_dump(mode="json", exclude_none=True) if copy is not None else None,
                created_by=(decision.reviewer or "").strip() or "alpha 1.0",
            ))
        if found.guild is not None:
            for person in found.guild.people:
                await rows.put(s, t.guild_people, pid, person.id, person.model_dump(mode="json", exclude_none=True),
                               by=person.addedBy or "system")
            for entry in found.guild.evidence:
                await rows.put(s, t.guild_evidence, pid, entry.id, entry.model_dump(mode="json", exclude_none=True),
                               by=entry.observerId or entry.personId, person_id=entry.personId, skill_id=entry.skillId)
            policy = found.guild.policy.model_dump(mode="json", exclude_none=True)
            await s.execute(update(t.projects).where(t.projects.c.id == pid).values(settings={"guildPolicy": policy}))
        for c in found.checks.checks:
            await rows.put(s, t.guild_checks, pid, c.id, c.model_dump(mode="json", exclude_none=True),
                           by=c.proposedBy or "system", state=c.state)
        for sc in found.practice.scenarios:
            await rows.put(s, t.practice_scenarios, pid, sc.id, sc.model_dump(mode="json", exclude_none=True), by=sc.model)
        for held in found.practice.sessions:
            await rows.put(s, t.practice_sessions, pid, held.id, held.model_dump(mode="json", exclude_none=True),
                           by=held.personId or "system")
        for p in found.proposals.proposals:
            await rows.put(s, t.proposals, pid, p.id, p.model_dump(mode="json"), by=p.by, state=p.state)
        for entry in found.audit:
            await s.execute(insert(t.audit).values(
                project_id=pid, agent=entry.agent, who=entry.who, module=entry.module, action=entry.action,
                state=entry.state, target=entry.target, body=entry.model_dump(mode="json"),
            ))
        for a in found.artifacts:
            await rows.put(s, t.artifacts, pid, a.id, a.model_dump(mode="json"), by="system",
                           tool=a.tool, version=a.toolVersion, output_hash=a.outputHash)
        for source, responses in (("model", found.extracted), ("hand", found.hand)):
            for r in responses:
                await s.execute(insert(t.candidates).values(project_id=pid, document_id=r.paperId, source=source,
                                                            body=r.model_dump(mode="json"), created_by="alpha 1.0"))
        for k in found.kept.trains:
            await rows.put(s, t.trains, pid, k.spec.id, k.model_dump(mode="json"), by=k.madeBy, kind="kept")
        # The import itself is on the record, under the project it made.
        await s.execute(insert(t.audit).values(
            project_id=pid, agent="person", who=asked.by, module="home", action="import_alpha1", state="imported",
            target=pid, body=AuditEntry(at=made.createdAt, agent="person", who=asked.by, module="home",
                                        action="import_alpha1", state="imported", target=pid,
                                        detail={"counts": found.counts()}).model_dump(mode="json"),
        ))
        return pid


def carry(data: Path, name: str, by: str) -> tuple[str, dict[str, int]]:
    """Make a project named `name` in `by`'s name and carry `data` into it,
    whole or not at all; the project's id and what was carried."""
    found = read(data)
    pid = db.run(_write(found, ProjectCreate(name=name, by=by, description=f"Carried from {data} (alpha 1.0).")))
    return pid, found.counts()


def main(argv: list[str]) -> int:
    load_dotenv(CORE / ".env", override=False)
    parser = argparse.ArgumentParser(prog="python -m openferment_core.import_alpha1", description=__doc__.split("\n\n")[0])
    parser.add_argument("--name", required=True, help="the new project's name")
    parser.add_argument("--by", required=True, help="the person carrying the records across")
    parser.add_argument("--data", default=str(CORE / "data"), help="the alpha 1.0 data directory (default core/data)")
    args = parser.parse_args(argv)
    try:
        pid, counts = carry(Path(args.data), args.name, args.by)
    except (ImportRefused, projects.ProjectRefused, db.DatabaseUnavailable) as e:
        print(f"refused: {e}", file=sys.stderr)
        return 2
    print(f"carried {args.data} into project {pid}:")
    for what, n in counts.items():
        print(f"  {n:>6}  {what}")
    print(f"The files under {args.data} are left as they were; move them aside once the project reads right.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
