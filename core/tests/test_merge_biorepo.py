"""biorepo.json merges by record, never as text (OF-BLD-012 §B.8).

The unit tests call the merge directly. The git tests rebuild what an
independent review reproduced against the first version of deploy.sh: a
decision pushed from one machine while another holds its own, uncommitted.
With the driver registered, `git pull --rebase` keeps both and the file
stays valid JSON; where only a person can settle it, git stops and the file
the service reads is left as this machine had it.
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from openferment_core.models import BioRepo

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "host" / "merge_biorepo.py"
_spec = importlib.util.spec_from_file_location("merge_biorepo", SCRIPT)
mb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mb)


def d(record_id: str, status: str = "verified", at: str = "2026-10-07T12:00:00Z") -> dict:
    return {"status": status, "provenance": "curated", "reviewer": "sean", "recordId": record_id, "at": at}


def repo(*decisions: dict, records: list[dict] | None = None) -> dict:
    return {"version": 1, "decisions": {x["recordId"]: x for x in decisions}, "records": records or []}


# ── the merge ──────────────────────────────────────────────────────────


def test_decisions_on_different_records_are_both_kept():
    merged, settled, conflicts = mb.merge(repo(), repo(d("r-A")), repo(d("r-B")))
    assert not conflicts and not settled
    assert set(merged["decisions"]) == {"r-A", "r-B"}


def test_the_same_decision_on_both_sides_is_one():
    merged, _, conflicts = mb.merge(repo(), repo(d("r-A")), repo(d("r-A")))
    assert not conflicts and list(merged["decisions"]) == ["r-A"]


def test_a_withdrawal_on_one_side_stands_when_the_other_left_it_alone():
    merged, _, conflicts = mb.merge(repo(d("r-A")), repo(), repo(d("r-A")))
    assert not conflicts and merged["decisions"] == {}


def test_two_decisions_on_one_record_keep_the_later():
    early, late = d("r-A", "verified", "2026-10-07T09:00:00Z"), d("r-A", "rejected", "2026-10-07T18:00:00Z")
    rec_early, rec_late = {"id": "r-A", "v": 1}, {"id": "r-A", "v": 2}
    merged, settled, conflicts = mb.merge(
        repo(), repo(early, records=[rec_early]), repo(late, records=[rec_late])
    )
    assert not conflicts and settled == ["r-A"]
    assert merged["decisions"]["r-A"]["status"] == "rejected"
    assert merged["records"] == [rec_late], "the candidate copy follows the decision that stood"


def test_a_withdrawal_against_a_change_is_left_for_a_person():
    _, _, conflicts = mb.merge(repo(d("r-A")), repo(), repo(d("r-A", "rejected", "2026-10-08T00:00:00Z")))
    assert conflicts == ["decision r-A"]


def test_two_decisions_at_the_same_instant_are_left_for_a_person():
    _, _, conflicts = mb.merge(repo(), repo(d("r-A", "verified")), repo(d("r-A", "rejected")))
    assert conflicts == ["decision r-A"]


def test_records_merge_by_id():
    merged, _, conflicts = mb.merge(repo(), repo(records=[{"id": "c1"}]), repo(records=[{"id": "c2"}]))
    assert not conflicts and [r["id"] for r in merged["records"]] == ["c1", "c2"]


def test_different_versions_are_not_merged():
    _, _, conflicts = mb.merge(repo(), repo(), {**repo(), "version": 2})
    assert conflicts and conflicts[0].startswith("version")


# ── the driver ─────────────────────────────────────────────────────────


def write(path: Path, data: dict | str) -> Path:
    path.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")
    return path


def test_writes_a_valid_file_in_the_models_format(tmp_path):
    base = write(tmp_path / "base", "")  # git's BASE when the file is new on both sides
    ours = write(tmp_path / "ours", repo(d("r-A")))
    theirs = write(tmp_path / "theirs", repo(d("r-B")))
    assert mb.main([str(base), str(ours), str(theirs)]) == 0
    text = ours.read_text(encoding="utf-8")
    model = BioRepo.model_validate_json(text)
    assert set(model.decisions) == {"r-A", "r-B"}
    assert text == model.model_dump_json(indent=2, exclude_none=True) + "\n"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["base", "ours", "theirs"]


def test_a_conflict_leaves_ours_exactly_as_it_was(tmp_path):
    base = write(tmp_path / "base", repo(d("r-A")))
    ours = write(tmp_path / "ours", repo())
    theirs = write(tmp_path / "theirs", repo(d("r-A", "rejected", "2026-10-08T00:00:00Z")))
    before = ours.read_bytes()
    assert mb.main([str(base), str(ours), str(theirs)]) == 1
    assert ours.read_bytes() == before


def test_unparseable_input_leaves_ours_as_it_was(tmp_path):
    base = write(tmp_path / "base", repo())
    ours = write(tmp_path / "ours", repo(d("r-A")))
    theirs = write(tmp_path / "theirs", "<<<<<<< HEAD")
    before = ours.read_bytes()
    assert mb.main([str(base), str(ours), str(theirs)]) == 1
    assert ours.read_bytes() == before


# ── through git, the way deploy.sh --keep-decisions runs it ────────────

needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="no git on this machine")
FILE = Path("core/data/biorepo.json")


def git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=check)


def machine(remote: Path, where: Path) -> Path:
    git(where.parent, "clone", "-q", str(remote), where.name)
    git(where, "config", "user.email", "t@example.org")
    git(where, "config", "user.name", "t")
    git(where, "config", "merge.biorepo.driver", f'"{sys.executable}" "{SCRIPT}" %O %A %B')
    return where


def decide(where: Path, data: dict, message: str, push: bool) -> None:
    write(where / FILE, BioRepo.model_validate(data).model_dump_json(indent=2, exclude_none=True) + "\n")
    git(where, "commit", "-qam", message)
    if push:
        git(where, "push", "-q", "origin", "HEAD:main")


@pytest.fixture
def two_machines(tmp_path):
    seed = tmp_path / "seed"
    seed.mkdir()
    git(seed, "init", "-q", "-b", "main")
    git(seed, "config", "user.email", "t@example.org")
    git(seed, "config", "user.name", "t")
    (seed / FILE).parent.mkdir(parents=True)
    write(seed / FILE, repo(d("r-0")))
    write(seed / ".gitattributes", "core/data/biorepo.json merge=biorepo\n")
    git(seed, "add", "-A")
    git(seed, "commit", "-qm", "seed")
    remote = tmp_path / "remote.git"
    git(tmp_path, "clone", "-q", "--bare", str(seed), str(remote))
    return machine(remote, tmp_path / "laptop"), machine(remote, tmp_path / "mini")


@needs_git
def test_decisions_from_two_machines_both_survive_a_rebase(two_machines):
    laptop, mini = two_machines
    decide(laptop, repo(d("r-0"), d("r-laptop")), "laptop decides", push=True)
    decide(mini, repo(d("r-0"), d("r-mini")), "mini decides", push=False)
    r = git(mini, "pull", "--rebase", check=False)
    assert r.returncode == 0, r.stderr
    model = BioRepo.model_validate_json((mini / FILE).read_text(encoding="utf-8"))
    assert set(model.decisions) == {"r-0", "r-laptop", "r-mini"}
    assert git(mini, "push", "-q", "origin", "HEAD:main", check=False).returncode == 0


@needs_git
def test_what_only_a_person_can_settle_stops_git_and_leaves_valid_json(two_machines):
    laptop, mini = two_machines
    decide(laptop, repo(), "laptop withdraws r-0", push=True)
    decide(mini, repo(d("r-0", "rejected", "2026-10-08T00:00:00Z")), "mini changes r-0", push=False)
    assert git(mini, "pull", "--rebase", check=False).returncode != 0
    git(mini, "rebase", "--abort")
    model = BioRepo.model_validate_json((mini / FILE).read_text(encoding="utf-8"))
    assert model.decisions["r-0"].status == "rejected", "this machine's decision is what the service reads"
    assert "<<<<<<<" not in (mini / FILE).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("ours_at", "theirs_at", "kept"),
    [
        ("2026-10-07T12:00:00+02:00", "2026-10-07T11:00:00Z", "theirs"),  # 10:00Z against 11:00Z
        ("2026-10-07T11:00:00.500Z", "2026-10-07T11:00:00Z", "ours"),
        ("2026-10-07T11:00:00.000Z", "2026-10-07T11:00:00Z", None),  # the same instant
        ("2026-10-07T11:00:00", "2026-10-07T10:00:00Z", None),  # no zone: cannot be told
        ("yesterday", "2026-10-07T10:00:00Z", None),
    ],
)
def test_later_means_later_in_time(ours_at, theirs_at, kept):
    o, t = d("r-A", "verified", ours_at), d("r-A", "rejected", theirs_at)
    merged, settled, conflicts = mb.merge(repo(), repo(o), repo(t))
    if kept is None:
        assert conflicts == ["decision r-A"]
    else:
        assert settled == ["r-A"]
        assert merged["decisions"]["r-A"]["status"] == ("verified" if kept == "ours" else "rejected")


# ── sync_decisions.sh, the script deploy.sh --keep-decisions runs ──────

HOST_DIR = SCRIPT.parent


def run_sync(where: Path) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if not k.startswith("OPENFERMENT_")}
    return subprocess.run(
        ["bash", str(where / "scripts" / "host" / "sync_decisions.sh")],
        cwd=where, env=env, capture_output=True, text=True,
    )


def put(where: Path, *decisions: dict) -> None:
    write(where / FILE, BioRepo.model_validate(repo(*decisions)).model_dump_json(indent=2, exclude_none=True) + "\n")


def on_github(remote: Path) -> BioRepo:
    text = git(remote, "show", f"main:{FILE.as_posix()}").stdout
    return BioRepo.model_validate_json(text)


@pytest.fixture
def scripted(tmp_path):
    """Two clones of a remote whose tree carries the real host scripts."""
    seed = tmp_path / "seed"
    (seed / FILE).parent.mkdir(parents=True)
    git(tmp_path, "init", "-q", "-b", "main", str(seed))
    for cfg in (("user.email", "t@example.org"), ("user.name", "t")):
        git(seed, "config", *cfg)
    (seed / "scripts" / "host").mkdir(parents=True)
    for name in ("lib.sh", "sync_decisions.sh", "merge_biorepo.py", "merge-biorepo"):
        shutil.copy2(HOST_DIR / name, seed / "scripts" / "host" / name)
    shutil.copy2(HOST_DIR.parents[1] / ".gitattributes", seed / ".gitattributes")
    put(seed, d("r-0"))
    git(seed, "add", "-A")
    git(seed, "commit", "-qm", "seed")
    remote = tmp_path / "remote.git"
    git(tmp_path, "clone", "-q", "--bare", str(seed), str(remote))
    clones = []
    for name in ("laptop", "mini"):
        git(tmp_path, "clone", "-q", str(remote), name)
        for cfg in (("user.email", "t@example.org"), ("user.name", "t")):
            git(tmp_path / name, "config", *cfg)
        clones.append(tmp_path / name)
    return remote, *clones


@needs_git
def test_sync_backs_up_decisions_from_two_machines(scripted):
    remote, laptop, mini = scripted
    put(laptop, d("r-0"), d("r-laptop"))
    assert run_sync(laptop).returncode == 0
    put(mini, d("r-0"), d("r-mini"))
    r = run_sync(mini)
    assert r.returncode == 0, r.stdout + r.stderr
    assert set(on_github(remote).decisions) == {"r-0", "r-laptop", "r-mini"}
    assert "Nothing new" in run_sync(mini).stdout


@needs_git
def test_sync_recovers_once_the_machines_agree(scripted):
    """The dead end the re-check found: an unpushed commit that disagreed
    once used to fail again on every later run."""
    remote, laptop, mini = scripted
    put(laptop)  # the laptop withdraws r-0
    assert run_sync(laptop).returncode == 0

    put(mini, d("r-0", "rejected", "2026-10-08T00:00:00Z"))  # the Mini changes it
    first = run_sync(mini)
    assert first.returncode == 1
    model = BioRepo.model_validate_json((mini / FILE).read_text(encoding="utf-8"))
    assert model.decisions["r-0"].status == "rejected", "the service reads this machine's decision"
    assert not (mini / ".git" / "rebase-merge").exists()

    put(mini, d("r-new"))  # the Mini withdraws r-0 too, so the machines agree, and decides r-new
    second = run_sync(mini)
    assert second.returncode == 0, second.stdout + second.stderr
    assert set(on_github(remote).decisions) == {"r-new"}


@needs_git
@pytest.mark.skipif(shutil.which("node") is None, reason="no node on this machine")
def test_pnpm_install_registers_the_driver_on_any_clone(tmp_path):
    """`prepare` runs on every `pnpm install`, so the laptop gets the driver
    as well as the Mini; without it the attribute falls back to a text merge."""
    git(tmp_path, "init", "-q")
    subprocess.run(["node", str(HOST_DIR.parent / "register-merge-driver.mjs")], cwd=tmp_path, check=True)
    driver = git(tmp_path, "config", "--get", "merge.biorepo.driver").stdout.strip()
    assert driver == "sh scripts/host/merge-biorepo %O %A %B"
    registered_by_lib = (HOST_DIR / "lib.sh").read_text(encoding="utf-8")
    assert f'merge.biorepo.driver "{driver}"' in registered_by_lib, "install and deploy register the same driver"
