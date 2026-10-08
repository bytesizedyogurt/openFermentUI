"""The Mac Mini's launchd jobs and host scripts (OF-BLD-012 §B.5–B.8).

The plists are rendered by scripts/host/launchd.py and parsed back here with
plistlib, so their shape is checked on any operating system; the shell
scripts are checked for syntax. Running them for real needs macOS.
"""
from __future__ import annotations

import importlib.util
import os
import plistlib
import shutil
import subprocess
from pathlib import Path

import pytest

HOST_DIR = Path(__file__).resolve().parents[2] / "scripts" / "host"
_spec = importlib.util.spec_from_file_location("of_launchd", HOST_DIR / "launchd.py")
launchd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(launchd)

REPO = Path("/Users/sean/openferment")
HOME = Path("/Users/sean")
PATH = "/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"


def render(tmp_path: Path, *extra: str) -> dict[str, dict]:
    out = tmp_path / "out"
    code = launchd.main([
        "--repo", str(REPO), "--user", "sean", "--home", str(HOME),
        "--path", PATH, "--out", str(out), *extra,
    ])
    assert code == 0
    return {p.stem: plistlib.loads(p.read_bytes()) for p in sorted(out.glob("*.plist"))}


def test_two_jobs_named_by_label(tmp_path):
    jobs = render(tmp_path)
    assert set(jobs) == {launchd.SERVER, launchd.NIGHTLY}
    for label, job in jobs.items():
        assert job["Label"] == label


def test_server_runs_as_the_owner_on_loopback(tmp_path):
    job = render(tmp_path)[launchd.SERVER]
    assert job["UserName"] == "sean"
    args = job["ProgramArguments"]
    assert args[0] == str(REPO / "core" / ".venv" / "bin" / "python")
    assert args[args.index("--host") + 1] == "127.0.0.1"
    assert args[args.index("--port") + 1] == "8000"
    assert "openferment_core.api:app" in args
    assert job["WorkingDirectory"] == str(REPO / "core")
    assert job["RunAtLoad"] is True and job["KeepAlive"] is True


def test_nightly_runs_at_three_and_not_at_load(tmp_path):
    job = render(tmp_path)[launchd.NIGHTLY]
    assert job["StartCalendarInterval"] == {"Hour": 3, "Minute": 0}
    assert job["RunAtLoad"] is False
    assert job["ProgramArguments"] == ["/bin/bash", str(REPO / "scripts" / "host" / "nightly.sh")]
    assert (HOST_DIR / "nightly.sh").is_file()


def test_both_log_to_the_owners_logs_folder(tmp_path):
    for job in render(tmp_path).values():
        for key in ("StandardOutPath", "StandardErrorPath"):
            assert Path(job[key]).parent == HOME / "Library" / "Logs" / "openferment"
        assert job["EnvironmentVariables"]["PATH"] == PATH
        assert job["EnvironmentVariables"]["HOME"] == str(HOME)


def test_host_and_port_overrides(tmp_path):
    args = render(tmp_path, "--host", "0.0.0.0", "--port", "8123")[launchd.SERVER]["ProgramArguments"]
    assert args[args.index("--host") + 1] == "0.0.0.0"
    assert args[args.index("--port") + 1] == "8123"


def test_no_key_passes_through_a_plist(tmp_path):
    render(tmp_path)
    files = list((tmp_path / "out").glob("*.plist"))
    assert len(files) == 2
    for p in files:
        text = p.read_text(encoding="utf-8")
        assert "ANTHROPIC" not in text and "sk-ant" not in text


@pytest.mark.parametrize(
    "kwargs",
    [
        {"user": "root"},
        {"user": ""},
        {"repo": Path("openferment")},
        {"home": Path("sean")},
        {"port": 0},
    ],
)
def test_refusals(kwargs):
    args = {"repo": REPO, "user": "sean", "home": HOME, "path": PATH, **kwargs}
    with pytest.raises(ValueError):
        launchd.daemons(**args)


@pytest.mark.parametrize("name", ["install.sh", "deploy.sh", "nightly.sh"])
def test_scripts_are_executable(name):
    assert os.access(HOST_DIR / name, os.X_OK), f"chmod +x scripts/host/{name}"


@pytest.mark.skipif(shutil.which("bash") is None, reason="no bash on this machine")
@pytest.mark.parametrize("name", ["install.sh", "deploy.sh", "nightly.sh", "lib.sh"])
def test_scripts_parse(name):
    subprocess.run(["bash", "-n", str(HOST_DIR / name)], check=True)


def test_reads_back_the_address_an_installed_job_was_given(tmp_path, capsys):
    render(tmp_path, "--host", "0.0.0.0", "--port", "8123")
    plist = tmp_path / "out" / f"{launchd.SERVER}.plist"
    capsys.readouterr()  # what render printed
    assert launchd.main(["--read", str(plist)]) == 0
    assert capsys.readouterr().out.split() == ["0.0.0.0", "8123"]
    assert launchd.main(["--read", str(tmp_path / "missing.plist")]) == 1


@pytest.mark.skipif(shutil.which("bash") is None, reason="no bash on this machine")
@pytest.mark.parametrize(
    ("host", "poll"),
    [("", "127.0.0.1"), ("127.0.0.1", "127.0.0.1"), ("0.0.0.0", "127.0.0.1"),
     ("192.168.1.5", "192.168.1.5"), ("::", "[::1]"), ("fd7a:115c::5", "[fd7a:115c::5]")],
)
def test_health_is_asked_where_the_server_listens(host, poll):
    env = {k: v for k, v in os.environ.items() if not k.startswith("OPENFERMENT_")}
    if host:
        env["OPENFERMENT_HOST"] = host
    out = subprocess.run(
        ["bash", "-c", f'source "{HOST_DIR / "lib.sh"}"; echo "$POLL $PORT"'],
        env=env, capture_output=True, text=True, check=True,
    ).stdout.split()
    assert out == [poll, "8000"]


@pytest.mark.skipif(shutil.which("bash") is None, reason="no bash on this machine")
def test_deploy_uses_the_address_the_job_was_installed_with(tmp_path):
    render(tmp_path, "--host", "0.0.0.0", "--port", "8123")
    env = {k: v for k, v in os.environ.items() if not k.startswith("OPENFERMENT_")}
    env["OPENFERMENT_LAUNCHD_DIR"] = str(tmp_path / "out")
    script = f'source "{HOST_DIR / "lib.sh"}"; echo "$HOST $PORT $POLL"'
    out = subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True, check=True).stdout
    assert out.split() == ["0.0.0.0", "8123", "127.0.0.1"]
    env["OPENFERMENT_PORT"] = "9000"  # the environment still wins
    out = subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True, check=True).stdout
    assert out.split() == ["0.0.0.0", "9000", "127.0.0.1"]
