"""The proof's example engines (alpha 2.2 D0.8, D0.8a; scripts/prove.py, scripts/walk.ts).

Before its service starts, `pnpm prove` installs every package directory under
examples/engines/ (one holding a pyproject.toml) into core's environment with
`uv pip install -e`, one check a package naming the engines it registers, every
package core/uv.lock pins held at its locked version (the lock's versions are
the install's constraints). A package that leads outside examples/engines/,
one whose pyproject.toml cannot be read, and one that fails to install or
outlives its time each fail the proof in words; with none there one line says
so. The walk runs one thing of each of those engines from the Runs screen.
Neither script names an engine of the examples, so a builder's package is
picked up with no change under scripts/. At its end, however it ends, the proof
leaves core's environment as it found it. The installs here go to a stand-in
for uv; the walk itself runs in `pnpm prove` step 9.
"""
from __future__ import annotations

import importlib.util
import json
import os
import signal
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO = Path(__file__).resolve().parents[2]
# What the stand-in's `uv export` answers: the lock's versions, a placeholder pin.
PINS = "placeholder-pin==1.0\n"


def _load():
    spec = importlib.util.spec_from_file_location("of_prove", REPO / "scripts" / "prove.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # its dataclasses resolve their annotations through it
    spec.loader.exec_module(module)
    return module


prove = _load()


def _package(root: Path, name: str, engines: list[str]) -> Path:
    where = root / name
    where.mkdir(parents=True)
    points = "".join(f'{e} = "placeholder_{e}.engine:ENGINE"\n' for e in engines)
    (where / "pyproject.toml").write_text(f'[project]\nname = "{name}"\nversion = "0.1.0"\n\n'
                                          f'[project.entry-points."openferment.engines"]\n{points}', encoding="utf-8")
    return where


class Uv:
    """A stand-in for uv and for core's interpreter: it answers `uv export` with PINS, says how core's environment
    holds a distribution (`held`, None when it holds none), and answers every install and uninstall as `answers`
    names by the command's last word (0 by default); each command asked is kept in `asked`."""

    def __init__(self, held: dict[str, dict | None] | None = None, answers: dict[str, object] | None = None,
                 export: int = 0) -> None:
        self.held = held or {}
        self.answers = answers or {}
        self.export = export
        self.asked: list[list[str]] = []
        self.constraints: list[str] = []

    def __call__(self, command: list[str], **kw):
        self.asked.append(command)
        assert kw["cwd"] == prove.CORE
        if command[:2] == ["uv", "export"]:
            return SimpleNamespace(returncode=self.export, stdout=PINS if not self.export else "",
                                   stderr="error: the lock is unreadable" if self.export else "")
        if command[:2] == [sys.executable, "-c"]:
            return SimpleNamespace(returncode=0, stdout=json.dumps(self.held.get(command[3])), stderr="")
        if "-c" in command:
            self.constraints.append(Path(command[command.index("-c") + 1]).read_text(encoding="utf-8"))
        answer = self.answers.get(Path(command[-1]).name, 0)
        if isinstance(answer, BaseException):
            raise answer
        return SimpleNamespace(returncode=answer, stdout="", stderr="resolving\nerror: a placeholder build failure")

    def installs(self) -> list[list[str]]:
        return [c for c in self.asked if c[:3] == ["uv", "pip", "install"]]


def _install(package: Path, held: Path) -> list[str]:
    return ["uv", "pip", "install", "--python", sys.executable, "-c", str(held), "-e", str(package)]


def test_with_no_package_under_examples_engines_one_line_says_so_and_nothing_is_installed(tmp_path, capsys):
    proof = prove.Proof(data_dir=tmp_path)
    uv = Uv()
    assert prove.install_examples(proof, root=tmp_path / "examples" / "engines", run=uv) == []
    out = capsys.readouterr().out.strip().splitlines()
    assert len(out) == 1 and out[0].endswith("so none is installed and no example engine is walked"), out
    assert uv.asked == [] and (proof.passed, proof.failed) == (0, 0) and proof.installed == []


def test_each_package_is_installed_editable_held_to_the_lock_and_its_engines_handed_on(tmp_path, capsys):
    root = tmp_path / "engines"
    one = _package(root, "openferment-engine-one", ["one"])
    two = _package(root, "openferment-engine-two", ["three", "two"])
    (root / "notes").mkdir()  # a directory holding no pyproject.toml is no package
    uv = Uv()
    proof = prove.Proof(data_dir=tmp_path)
    assert prove.install_examples(proof, root=root, run=uv) == ["one", "three", "two"]
    held = tmp_path / "constraints.txt"
    assert uv.asked[0][:2] == ["uv", "export"] and "--frozen" in uv.asked[0], "the lock's versions read first"
    assert uv.installs() == [_install(p, held) for p in (one, two)]
    assert uv.constraints == [PINS, PINS], "each install held to the lock's versions"
    assert (proof.passed, proof.failed) == (2, 0)
    assert [(i.distribution, i.engines, i.before) for i in proof.installed] == [
        ("openferment-engine-one", ["one"], None), ("openferment-engine-two", ["three", "two"], None)]
    out = capsys.readouterr().out
    assert "each package core/uv.lock pins held at its locked version), registering three, two" in out


def test_a_package_that_fails_to_install_fails_the_proof_in_words(tmp_path, capsys):
    root = tmp_path / "engines"
    _package(root, "openferment-engine-one", ["one"])
    proof = prove.Proof(data_dir=tmp_path)
    assert prove.install_examples(proof, root=root, run=Uv(answers={"openferment-engine-one": 2})) == []
    assert proof.failed == 1 and proof.installed == []
    assert ("did not install (uv pip install -e exited 2, each package core/uv.lock pins held at its locked version): "
            "error: a placeholder build failure") in capsys.readouterr().out


def test_a_package_outside_the_directory_a_pyproject_no_one_reads_and_a_hung_build_each_fail_in_words(tmp_path, capsys):
    root = tmp_path / "engines"
    root.mkdir()
    elsewhere = _package(tmp_path / "elsewhere", "openferment-engine-far", ["far"])
    (root / "openferment-engine-far").symlink_to(elsewhere, target_is_directory=True)
    broken = root / "openferment-engine-broken"
    broken.mkdir()
    (broken / "pyproject.toml").write_text("[project\nname = ", encoding="utf-8")
    nameless = root / "openferment-engine-nameless"
    nameless.mkdir()
    (nameless / "pyproject.toml").write_text('[project]\nversion = "0.1.0"\n', encoding="utf-8")
    _package(root, "openferment-engine-slow", ["slow"])
    good = _package(root, "openferment-engine-good", ["good"])
    uv = Uv(answers={"openferment-engine-slow": subprocess.TimeoutExpired(["uv"], prove.RUN_TIMEOUT_S)})
    proof = prove.Proof(data_dir=tmp_path)
    assert prove.install_examples(proof, root=root, run=uv) == ["good"]
    out = capsys.readouterr().out
    assert f"leads to {elsewhere.resolve()}, outside {root}; the proof installs from {root} alone" in out
    assert "openferment-engine-broken was not installed: TOMLDecodeError" in out
    assert "openferment-engine-nameless was not installed: ValueError: its pyproject.toml names no distribution" in out
    assert "openferment-engine-slow did not install (uv pip install -e): TimeoutExpired" in out
    assert (proof.passed, proof.failed) == (1, 4)
    assert [Path(c[-1]).name for c in uv.installs()] == ["openferment-engine-good", "openferment-engine-slow"], \
        "a package outside the directory, or one no one reads, asks uv nothing"
    assert [i.package for i in proof.installed] == [good]


def test_a_lock_that_cannot_be_read_as_the_constraints_installs_nothing(tmp_path, capsys):
    root = tmp_path / "engines"
    _package(root, "openferment-engine-one", ["one"])
    uv = Uv(export=2)
    proof = prove.Proof(data_dir=tmp_path)
    assert prove.install_examples(proof, root=root, run=uv) == []
    assert uv.installs() == [] and proof.failed == 1
    assert "core/uv.lock could not be read as the installs' constraints (uv export --frozen exited 2)" in \
        capsys.readouterr().out


def test_the_proof_leaves_cores_environment_as_it_found_it(tmp_path, capsys):
    root = tmp_path / "engines"
    new = _package(root, "openferment-engine-new", ["new"])
    same = _package(root, "openferment-engine-same", ["same"])
    moved = _package(root, "openferment-engine-moved", ["moved"])
    before = tmp_path / "another-checkout" / "openferment-engine-moved"
    before.mkdir(parents=True)

    def held(where: Path) -> dict:
        return {"version": "0.1.0", "from": {"url": where.as_uri(), "dir_info": {"editable": True}}}

    uv = Uv(held={"openferment-engine-same": held(same), "openferment-engine-moved": held(before)})
    proof = prove.Proof(data_dir=tmp_path)
    prove.install_examples(proof, root=root, run=uv)
    asked = len(uv.asked)
    prove.leave_as_found(proof, run=uv)
    after = uv.asked[asked:]
    assert after == [["uv", "pip", "install", "--python", sys.executable, "-c", str(tmp_path / "constraints.txt"),
                      "-e", str(before)],
                     ["uv", "pip", "uninstall", "--python", sys.executable, "openferment-engine-new"]], \
        "the moved one back where it was, the new one out, the same one left"
    out = capsys.readouterr().out
    assert "openferment-engine-new uninstalled, as the proof found core's environment without it" in out
    assert "openferment-engine-same stays installed from" in out and "as it was before the proof" in out
    assert f"openferment-engine-moved installed again from {before}, as it was before the proof" in out
    assert new.exists()
    kept = Uv()
    prove.leave_as_found(proof, run=kept, kept=True)
    assert kept.asked == [], "with the service kept, every one stays installed"
    assert "openferment-engine-new stays installed from" in capsys.readouterr().out


def test_a_sigterm_ends_the_proof_with_cores_environment_left_as_it_was_found(tmp_path, monkeypatch):
    left: list[tuple] = []

    def install(proof, *a, **k):
        proof.installed.append(prove.Installed(tmp_path, "openferment-engine-one", ["one"], None))
        return ["one"]

    def step(proof):
        os.kill(os.getpid(), signal.SIGTERM)

    monkeypatch.setattr(prove, "install_examples", install)
    monkeypatch.setattr(prove, "leave_as_found", lambda proof, kept: left.append((proof.installed, kept)))
    monkeypatch.setattr(prove, "migrations", lambda *a: SimpleNamespace(returncode=0, stdout="", stderr=""))
    monkeypatch.setitem(prove.RUNNERS, 1, step)
    before = signal.getsignal(signal.SIGTERM)
    with pytest.raises(SystemExit) as ended:
        prove.main(["--steps", "1"])
    assert ended.value.code == 128 + signal.SIGTERM
    ((installed, kept),) = left
    assert [i.distribution for i in installed] == ["openferment-engine-one"] and kept is False
    assert signal.getsignal(signal.SIGTERM) is before, "the proof's handler is taken down as it ends"


def test_the_distribution_and_the_engines_a_package_registers_are_read_from_its_pyproject(tmp_path):
    assert prove.example_project(REPO / "core") == ("openferment-core", ["biosteam", "kinetics", "train"]), \
        "the core's own, read the same way"
    assert prove.example_project(_package(tmp_path, "openferment-engine-none", [])) == ("openferment-engine-none", [])


def test_the_proof_and_the_walk_name_no_example_engine_and_hand_the_walk_what_was_installed():
    prove_text = (REPO / "scripts" / "prove.py").read_text(encoding="utf-8")
    walk_text = (REPO / "scripts" / "walk.ts").read_text(encoding="utf-8")
    assert '"WALK_ENGINES": ",".join(examples)' in prove_text and "process.env.WALK_ENGINES" in walk_text
    assert 'proof.made["examples"] = install_examples(proof)' in prove_text
    assert prove_text.index("install_examples(proof)\n") < prove_text.index("for n in order(asked):"), \
        "installed before the first step starts the service"
    main = prove_text[prove_text.index("def main("):]
    handled = main.index("signal.signal(signal.SIGTERM, ended)")
    assert handled < main.index("    try:\n", handled) < main.index("install_examples(proof)") < \
        main.index("    finally:\n") < main.index("leave_as_found(proof"), \
        "installed inside the try, and left as found in its finally"
    assert "refused.first().textContent()" in walk_text, "a refused run fails the walk in the service's words"
    # Each example engine reaches the proof and the walk through what was installed: neither text
    # names a distribution or a module of the engine-package form the contract page gives.
    for text in (prove_text, walk_text):
        assert "openferment-engine-" not in text and "openferment_engine_" not in text
