"""Data outlives a VM, and only the listed data (OF-BLD-014 §1.3, E.10).

Real git, offline: a bare repository stands for GitHub and two clones for two
machines, each carrying the real scripts/data-sync.sh. The first pushes and
the second pulls, and the files compare equal; fetched full text never leaves
the first; a path outside the list is refused by name.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "data-sync.sh"
BRANCH = "openferment-data"
LISTED = [
    "core/data/candidates",
    "core/data/artifacts",
    "core/data/rageval",
    "core/data/index/config.json",
    "core/data/live",
    "core/data/thread-p-proposed.tsv",
]

needs_git = pytest.mark.skipif(
    shutil.which("git") is None or shutil.which("bash") is None, reason="needs git and bash"
)


def git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=check)


def sync(where: Path, *args: str) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if not k.startswith("OPENFERMENT_")}
    return subprocess.run(
        ["bash", str(where / "scripts" / "data-sync.sh"), *args],
        cwd=where, env=env, capture_output=True, text=True,
    )


def put(where: Path, rel: str, text: str) -> None:
    path = where / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def files(root: Path, rel: str) -> dict[str, bytes]:
    base = root / rel
    if base.is_file():
        return {rel: base.read_bytes()}
    return {str(p.relative_to(root)): p.read_bytes() for p in sorted(base.rglob("*")) if p.is_file()}


@pytest.fixture
def machines(tmp_path):
    """A remote whose code branch carries the real script, and two clones of it."""
    seed = tmp_path / "seed"
    git(tmp_path, "init", "-q", "-b", "main", str(seed))
    for cfg in (("user.email", "t@example.org"), ("user.name", "t")):
        git(seed, "config", *cfg)
    (seed / "scripts").mkdir()
    shutil.copy2(SCRIPT, seed / "scripts" / "data-sync.sh")
    shutil.copy2(SCRIPT.parents[1] / ".gitignore", seed / ".gitignore")  # the real ignore rules
    git(seed, "add", "-A")
    git(seed, "commit", "-qm", "seed")
    remote = tmp_path / "remote.git"
    git(tmp_path, "clone", "-q", "--bare", str(seed), str(remote))
    clones = []
    for name in ("first", "second"):
        git(tmp_path, "clone", "-q", str(remote), name)
        for cfg in (("user.email", "t@example.org"), ("user.name", "t")):
            git(tmp_path / name, "config", *cfg)
        clones.append(tmp_path / name)
    return remote, *clones


def fill(where: Path) -> None:
    """One file under every listed path, and the things that must stay."""
    put(where, "core/data/candidates/P1.json", '{"paperId": "P1"}\n')
    put(where, "core/data/candidates/P2.json", '{"paperId": "P2"}\n')
    put(where, "core/data/artifacts/0a1b2c3d4e5f6a7b.json", '{"tool": "test"}\n')
    put(where, "core/data/rageval/scores.json", "{}\n")
    put(where, "core/data/index/config.json", '{"lane": "bm25"}\n')
    put(where, "core/data/live/2026-10-14.json", "{}\n")
    put(where, "core/data/thread-p-proposed.tsv", "verdict\tid\nPROPOSE\tPMC1\n")
    # What never leaves the machine that made it.
    put(where, "core/data/fulltext/P1.json", '{"paperId": "P1", "sections": []}\n')
    put(where, "core/data/index/passages.jsonl", "{}\n")
    put(where, "core/data/spend.json", "{}\n")
    put(where, "core/data/guild.json", "{}\n")
    put(where, "core/.env", "ANTHROPIC_API_KEY=placeholder\n")


@needs_git
def test_what_one_machine_pushes_another_pulls(machines):
    remote, first, second = machines
    fill(first)
    pushed = sync(first, "push")
    assert pushed.returncode == 0, pushed.stderr + pushed.stdout
    pulled = sync(second, "pull")
    assert pulled.returncode == 0, pulled.stderr + pulled.stdout
    for rel in LISTED:
        assert files(second, rel) == files(first, rel), rel
    assert "pulled 7 file(s)" in pulled.stdout


@needs_git
def test_full_text_and_the_other_local_files_never_leave(machines):
    remote, first, second = machines
    fill(first)
    assert sync(first, "push").returncode == 0
    assert sync(second, "pull").returncode == 0
    for rel in ("core/data/fulltext", "core/data/index/passages.jsonl", "core/data/spend.json",
                "core/data/guild.json", "core/.env"):
        assert not (second / rel).exists(), rel
    on_branch = git(remote, "ls-tree", "-r", "--name-only", BRANCH).stdout.split()
    assert on_branch and all(f == "README.md" or any(f == p or f.startswith(p + "/") for p in LISTED)
                             for f in on_branch), on_branch


@needs_git
def test_a_path_outside_the_list_is_refused_by_name(machines):
    remote, first, _ = machines
    fill(first)
    for path in ("core/data/fulltext/", "core/data/fulltext/P1.json", "core/.env",
                 "core/data/candidates/../fulltext", "/etc", "core/data/index/passages.jsonl"):
        r = sync(first, "push", path)
        assert r.returncode != 0, path
        assert f"{path} is outside the list data-sync.sh carries" in r.stderr, r.stderr
    assert git(remote, "branch", "--list", BRANCH).stdout.strip() == "", "nothing was pushed"


@needs_git
def test_a_listed_path_alone_travels_alone(machines):
    remote, first, second = machines
    fill(first)
    r = sync(first, "push", "core/data/candidates/P1.json")
    assert r.returncode == 0, r.stderr
    on_branch = git(remote, "ls-tree", "-r", "--name-only", BRANCH).stdout.split()
    assert sorted(on_branch) == ["README.md", "core/data/candidates/P1.json"]


@needs_git
def test_pull_before_any_push_says_so_and_succeeds(machines):
    _, _, second = machines
    r = sync(second, "pull")
    assert r.returncode == 0 and f"no {BRANCH} branch on origin yet" in r.stdout


@needs_git
def test_the_data_branch_shares_no_history_with_the_code(machines):
    remote, first, _ = machines
    fill(first)
    assert sync(first, "push").returncode == 0
    assert git(remote, "merge-base", "main", BRANCH, check=False).returncode == 1, "an orphan branch"


@needs_git
def test_pushes_from_two_machines_add_up(machines):
    remote, first, second = machines
    put(first, "core/data/candidates/P1.json", '{"paperId": "P1"}\n')
    assert sync(first, "push").returncode == 0
    assert sync(second, "pull").returncode == 0
    put(second, "core/data/candidates/P2.json", '{"paperId": "P2"}\n')
    assert sync(second, "push").returncode == 0
    assert sync(first, "pull").returncode == 0
    assert sorted(files(first, "core/data/candidates")) == [
        "core/data/candidates/P1.json", "core/data/candidates/P2.json"]


@needs_git
def test_a_second_push_of_the_same_files_commits_nothing(machines):
    remote, first, _ = machines
    fill(first)
    assert sync(first, "push").returncode == 0
    before = git(remote, "rev-parse", BRANCH).stdout
    again = sync(first, "push")
    assert again.returncode == 0 and "nothing new to push" in again.stdout
    assert git(remote, "rev-parse", BRANCH).stdout == before


@needs_git
def test_the_throwaway_checkout_is_gone_afterwards(machines):
    _, first, _ = machines
    fill(first)
    assert sync(first, "push").returncode == 0
    assert not (first / ".data-sync" / BRANCH).exists()


# ── pnpm decisions:push: biorepo.json alone, on the branch this checkout is on ──

DECISIONS = Path(__file__).resolve().parents[2] / "scripts" / "decisions-push.sh"


def decisions_push(where: Path) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if not k.startswith("OPENFERMENT_")}
    return subprocess.run(["bash", str(where / "scripts" / "decisions-push.sh")],
                          cwd=where, env=env, capture_output=True, text=True)


@pytest.fixture
def work_branch(machines):
    remote, first, _ = machines
    shutil.copy2(DECISIONS, first / "scripts" / "decisions-push.sh")
    git(first, "checkout", "-q", "-b", "work")
    put(first, "core/data/biorepo.json", '{"version": 1, "decisions": {}, "records": []}\n')
    git(first, "add", "scripts/decisions-push.sh", "core/data/biorepo.json")
    git(first, "commit", "-qm", "the work branch")
    git(first, "push", "-q", "-u", "origin", "work")
    return remote, first


@needs_git
def test_decisions_push_commits_biorepo_alone_and_pushes(work_branch):
    remote, first = work_branch
    put(first, "core/data/biorepo.json", '{"version": 1, "decisions": {"r-1": {}}, "records": []}\n')
    put(first, "notes.txt", "an unstaged change that must stay behind\n")
    r = decisions_push(first)
    assert r.returncode == 0, r.stderr + r.stdout
    subject = git(remote, "log", "-1", "--format=%s", "work").stdout.strip()
    assert subject.startswith("Guild decisions 20")
    changed = git(remote, "show", "--name-only", "--format=", "work").stdout.split()
    assert changed == ["core/data/biorepo.json"]
    assert (first / "notes.txt").exists() and "notes.txt" in git(first, "status", "--short").stdout


@needs_git
def test_decisions_push_refuses_while_another_file_is_staged(work_branch):
    remote, first = work_branch
    before = git(remote, "rev-parse", "work").stdout
    put(first, "core/data/biorepo.json", '{"version": 1, "decisions": {"r-2": {}}, "records": []}\n')
    put(first, "notes.txt", "staged by accident\n")
    git(first, "add", "notes.txt")
    r = decisions_push(first)
    assert r.returncode != 0 and "other files are staged: notes.txt" in r.stderr, r.stderr
    assert git(remote, "rev-parse", "work").stdout == before, "nothing was pushed"
    assert git(first, "log", "-1", "--format=%s").stdout.strip() == "the work branch", "nothing was committed"
