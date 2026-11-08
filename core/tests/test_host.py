"""The Mac Mini's launchd jobs and host scripts (OF-BLD-012 §B.5–B.8).

The plists are rendered by scripts/host/launchd.py and parsed back here with
plistlib, so their shape is checked on any operating system; the shell
scripts are checked for syntax, and lib.sh's reading of core/.env, its
database step and the night's dump run against stand-ins for Homebrew and the
PostgreSQL tools.
Running them for real needs macOS.
"""
from __future__ import annotations

import importlib.util
import os
import plistlib
import re
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
    assert launchd.poll_host(host) == poll, "launchd.poll_host and lib.sh's poll_host disagree"
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


@pytest.mark.skipif(shutil.which("bash") is None, reason="no bash on this machine")
@pytest.mark.parametrize(("asked", "expected"), [(None, "127.0.0.1"), ("0.0.0.0", "0.0.0.0")])
def test_a_reinstall_never_keeps_a_wide_host_unasked(tmp_path, asked, expected):
    render(tmp_path, "--host", "0.0.0.0", "--port", "8123")
    env = {k: v for k, v in os.environ.items() if not k.startswith("OPENFERMENT_")}
    env["OPENFERMENT_LAUNCHD_DIR"] = str(tmp_path / "out")
    if asked:
        env["OPENFERMENT_HOST"] = asked
    script = f'source "{HOST_DIR / "lib.sh"}"; install_address; echo "= $HOST $PORT"'
    out = subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True, check=True).stdout
    assert out.splitlines()[-1].split() == ["=", expected, "8123"]
    assert ("will now listen on 127.0.0.1" in out) is (asked is None)


# ── core/.env's settings and the database, against stand-ins (alpha 2.2 G) ──


def _lib(tmp_path: Path, body: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    """`body` run under `set -euo pipefail` after lib.sh is sourced, with REPO
    and HOME in `tmp_path`, no OPENFERMENT_ setting in the environment beyond
    `env`, and no installed job."""
    base = {k: v for k, v in os.environ.items() if not k.startswith("OPENFERMENT_")}
    base |= {"OPENFERMENT_LAUNCHD_DIR": str(tmp_path / "daemons"), "HOME": str(tmp_path / "home"), **(env or {})}
    (tmp_path / "core").mkdir(exist_ok=True)
    (tmp_path / "home").mkdir(exist_ok=True)
    script = f'set -euo pipefail; source "{HOST_DIR / "lib.sh"}"; REPO="{tmp_path}"; {body}'
    return subprocess.run(["bash", "-c", script], env=base, capture_output=True, text=True)


@pytest.mark.skipif(shutil.which("bash") is None, reason="no bash on this machine")
@pytest.mark.parametrize("lines", [
    "OPENFERMENT_PROJECT=ethanol\n",
    'OPENFERMENT_PROJECT="ethanol"\n',
    "OPENFERMENT_PROJECT='ethanol'\n",
    "OPENFERMENT_PROJECT=ethanol # the live one\n",
    "OPENFERMENT_PROJECT=ethanol   \n",
    "export OPENFERMENT_PROJECT=ethanol\n",
    "OPENFERMENT_PROJECT = ethanol\n",
    'OPENFERMENT_PROJECT="a b" # two words\n',
    "OPENFERMENT_PROJECT=ethanol\r\n",
    "OPENFERMENT_PROJECT=first\nOPENFERMENT_PROJECT=second\n",
    "OPENFERMENT_OTHER=ethanol\n",
])
def test_a_setting_is_read_from_core_env_as_python_dotenv_reads_it(tmp_path, lines):
    from dotenv import dotenv_values

    (tmp_path / "core").mkdir()
    (tmp_path / "core" / ".env").write_bytes(lines.encode())
    done = _lib(tmp_path, 'printf "[%s]" "$(env_setting OPENFERMENT_PROJECT)"')
    assert done.returncode == 0, done.stderr
    expected = dotenv_values(tmp_path / "core" / ".env").get("OPENFERMENT_PROJECT") or ""
    assert done.stdout == f"[{expected}]"


@pytest.mark.skipif(shutil.which("bash") is None, reason="no bash on this machine")
def test_the_environment_names_a_setting_as_it_stands(tmp_path):
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / ".env").write_text("OPENFERMENT_PROJECT=from-the-file\n")
    done = _lib(tmp_path, 'printf "[%s]" "$(env_setting OPENFERMENT_PROJECT)"', {"OPENFERMENT_PROJECT": '"quoted"'})
    assert done.stdout == '["quoted"]'


def _postgres_stand_ins(tmp_path: Path, *, vector: str = "1") -> Path:
    """Homebrew with postgresql@17 keg-only: brew answers the keg's prefix,
    and the keg holds pg_isready (answering), psql (answering `vector` for
    pgvector and no row for the database) and createdb; each call is written
    to `calls`. The PATH to run with."""
    stand_ins, keg = tmp_path / "bin", tmp_path / "keg" / "bin"
    stand_ins.mkdir()
    keg.mkdir(parents=True)
    calls = tmp_path / "calls"
    tools = {
        stand_ins / "brew": f'[ "$*" = "--prefix --installed postgresql@17" ] && echo "{keg.parent}" && exit 0\nexit 1',
        keg / "pg_isready": "exit 0",
        keg / "psql": f'case "$*" in *pg_available_extensions*) echo "{vector}" ;; esac',
        keg / "createdb": "",
    }
    for path, body in tools.items():
        path.write_text(f'#!/bin/bash\necho "{path.name} $*" >> "{calls}"\n{body}\n')
        path.chmod(0o755)
    return stand_ins


@pytest.mark.skipif(shutil.which("bash") is None, reason="no bash on this machine")
def test_the_database_is_made_from_the_keg_and_named_once_on_a_line_of_its_own(tmp_path):
    path = f"{_postgres_stand_ins(tmp_path)}:/usr/bin:/bin"
    env_file = tmp_path / "core" / ".env"
    (tmp_path / "core").mkdir()
    env_file.write_text("# a placeholder\nANTHROPIC_API_KEY=sk-ant-...")  # no newline at the end
    done = _lib(tmp_path, "ensure_database", {"PATH": path})
    assert done.returncode == 0, done.stderr
    calls = (tmp_path / "calls").read_text().splitlines()
    assert calls[:2] == ["brew --prefix --installed postgresql@17", "pg_isready -q -h 127.0.0.1"], \
        "the keg's tools go first on the path"
    assert "createdb -h 127.0.0.1 openferment" in calls
    assert all(c.startswith("psql -X ") for c in calls if c.startswith("psql")), "psql reads no ~/.psqlrc"
    user = subprocess.run(["id", "-un"], capture_output=True, text=True, check=True).stdout.strip()
    lines = env_file.read_text().splitlines()
    assert lines[1] == "ANTHROPIC_API_KEY=sk-ant-..." and lines[-1] == (
        f"OPENFERMENT_DATABASE_URL=postgresql://{user}@127.0.0.1:5432/openferment")
    assert oct(env_file.stat().st_mode & 0o777) == "0o600"
    again = _lib(tmp_path, "ensure_database", {"PATH": path})
    assert again.returncode == 0 and "OPENFERMENT_DATABASE_URL names the database." in again.stdout
    assert env_file.read_text().count("OPENFERMENT_DATABASE_URL=") == 1


@pytest.mark.skipif(shutil.which("bash") is None, reason="no bash on this machine")
@pytest.mark.parametrize("line", [
    "OPENFERMENT_DATABASE_URL=postgresql://openferment:openferment@127.0.0.1:5432/openferment_dev",
    'OPENFERMENT_DATABASE_URL="postgresql://someone@127.0.0.1:5432/openferment_dev" # dev',
    "OPENFERMENT_DATABASE_URL=postgresql://openferment:openferment@127.0.0.1:5432/openferment",
])
def test_the_developers_database_of_the_example_is_refused_in_words(tmp_path, line):
    path = f"{_postgres_stand_ins(tmp_path)}:/usr/bin:/bin"
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / ".env").write_text(f"{line}\n")
    done = _lib(tmp_path, "ensure_database", {"PATH": path})
    assert done.returncode == 1 and "the developer's database of core/.env.example" in done.stderr
    assert "createdb" not in (tmp_path / "calls").read_text()


@pytest.mark.skipif(shutil.which("bash") is None, reason="no bash on this machine")
def test_a_missing_pgvector_and_a_login_started_postgresql_are_said(tmp_path):
    path = f"{_postgres_stand_ins(tmp_path, vector='')}:/usr/bin:/bin"
    agents = tmp_path / "home" / "Library" / "LaunchAgents"
    agents.mkdir(parents=True)
    (agents / "homebrew.mxcl.postgresql@17.plist").write_text("")
    done = _lib(tmp_path, "ensure_database", {"PATH": path})
    assert done.returncode == 1 and "pgvector is not installed for this PostgreSQL" in done.stderr
    assert "starts at your login" in done.stdout and "sudo brew services start --sudo-service-user=" in done.stdout
    assert "createdb" not in (tmp_path / "calls").read_text()


# ── the night's dump, against stand-ins (the alpha 2.2 prompt §3) ──────────

# Eight dumps of days long past, and a file of the owner's own in the folder.
PAST_DAYS = [f"2000-01-0{d}" for d in range(1, 9)]


def _dump_stand_ins(tmp_path: Path, *, fails: bool = False) -> tuple[str, Path]:
    """The keg of `_postgres_stand_ins` with a pg_dump that writes its own
    arguments into the file `--file=` names, or writes half of one and fails;
    the backups folder holding PAST_DAYS's dumps and a note. The PATH to run
    with, and the folder."""
    stand_ins = _postgres_stand_ins(tmp_path)
    tool = tmp_path / "keg" / "bin" / "pg_dump"
    tool.write_text(
        f'#!/bin/bash\necho "pg_dump $*" >> "{tmp_path / "calls"}"\n'
        'for a in "$@"; do case "$a" in --file=*) out="${a#--file=}" ;; esac; done\n'
        + ('printf half > "$out"\nexit 1\n' if fails else 'printf "%s\\n" "$*" > "$out"\n'))
    tool.chmod(0o755)
    backups = tmp_path / "home" / "openferment-backups"
    backups.mkdir(parents=True)
    for day in PAST_DAYS:
        (backups / f"openferment-{day}.dump").write_text(day)
    (backups / "notes.txt").write_text("the owner's own")
    return f"{stand_ins}:/usr/bin:/bin", backups


@pytest.mark.skipif(shutil.which("bash") is None, reason="no bash on this machine")
def test_the_night_dumps_openferment_with_the_kegs_pg_dump_and_keeps_the_newest_seven(tmp_path):
    path, backups = _dump_stand_ins(tmp_path)
    done = _lib(tmp_path, "backup_database", {"PATH": path})
    assert done.returncode == 0, done.stderr
    today = subprocess.run(["date", "+%F"], capture_output=True, text=True, check=True).stdout.strip()
    dump = backups / f"openferment-{today}.dump"
    assert dump.read_text().split() == ["-h", "127.0.0.1", "--format=custom", f"--file={dump}.part", "openferment"]
    assert [c for c in (tmp_path / "calls").read_text().splitlines() if c.startswith("pg_dump")] == [
        f"pg_dump -h 127.0.0.1 --format=custom --file={dump}.part openferment"], "the keg's pg_dump, once"
    kept = sorted(p.name for p in backups.glob("openferment-*.dump"))
    assert kept == sorted([dump.name] + [f"openferment-{d}.dump" for d in PAST_DAYS[-6:]])
    assert (backups / "notes.txt").read_text() == "the owner's own", "a file of another name is the owner's"
    assert not list(backups.glob("*.part"))
    assert oct(backups.stat().st_mode & 0o777) == "0o700" and oct(dump.stat().st_mode & 0o777) == "0o600"
    assert "openferment-2000-01-02.dump removed: the newest 7 are kept" in done.stdout
    again = _lib(tmp_path, "backup_database", {"PATH": path})
    assert again.returncode == 0 and len(list(backups.glob("openferment-*.dump"))) == 7, "one file a day"


@pytest.mark.skipif(shutil.which("bash") is None, reason="no bash on this machine")
def test_a_failed_dump_keeps_the_kept_dumps_as_they_were(tmp_path):
    path, backups = _dump_stand_ins(tmp_path, fails=True)
    before = sorted(p.name for p in backups.iterdir())
    done = _lib(tmp_path, "backup_database || echo status=$?", {"PATH": path})
    assert "status=1" in done.stdout and "pg_dump openferment failed" in done.stderr
    assert sorted(p.name for p in backups.iterdir()) == before, "no half file, and nothing rotated away"


def test_the_nightly_dumps_before_the_nights_work_and_counts_a_failed_dump():
    text = (HOST_DIR / "nightly.sh").read_text()
    assert "backup_database || status=$?" in text
    assert text.index("backup_database ||") < text.index("openferment_core.extract")


# ── the engines a machine keeps beside core/uv.lock (alpha 2.2 D0.11) ────

SCRIPTS = HOST_DIR.parent
CORE = SCRIPTS.parent / "core"


# What the stand-in's `uv export` answers: the lock's versions, a placeholder pin.
PINS = "placeholder-pin==1.0"


def _uv_stand_in(tmp_path: Path, *, export_fails: bool = False) -> tuple[Path, Path]:
    """A stand-in for uv that writes where it was run and what it was asked,
    answers `export` with PINS (or fails it), writes the constraints file an
    install names beside the install, and fails for a directory named
    `fails`; the file it writes to."""
    asked = tmp_path / "asked"
    stub = tmp_path / "uv"
    export = "exit 1" if export_fails else f'echo "{PINS}"; exit 0'
    stub.write_text(f'#!/bin/bash\nprintf "%s\\n" "$PWD $*" >> "{asked}"\n'
                    f'if [ "$1" = export ]; then {export}; fi\n'
                    f'[ "$5" = -c ] && printf "constraints: %s\\n" "$(cat "$6")" >> "{asked}"\n'
                    f'[ "$(basename "${{@: -1}}")" != fails ]\n')
    stub.chmod(0o755)
    return stub, asked


EXPORT = "export --frozen --all-extras --no-hashes --no-emit-project --quiet"


def _installs(asked: Path) -> list[str]:
    """The installs the stand-in was asked for, each constraints file named
    `<c>`, after the one export they follow; each install's constraints the
    export's pins."""
    lines = asked.read_text().splitlines()
    assert lines[0] == f"{CORE} {EXPORT}", lines
    installs = [re.sub(r" -c \S+ ", " -c <c> ", line) for line in lines[1:] if not line.startswith("constraints: ")]
    assert [line for line in lines[1:] if line.startswith("constraints: ")] == [f"constraints: {PINS}"] * len(installs)
    return installs


def _engines_local(listed: Path, stub: Path) -> subprocess.CompletedProcess:
    env = {**os.environ, "OPENFERMENT_ENGINES_LOCAL": str(listed), "OPENFERMENT_UV": str(stub)}
    return subprocess.run(["bash", str(SCRIPTS / "engines-local.sh")], env=env, capture_output=True, text=True)


@pytest.mark.skipif(shutil.which("bash") is None, reason="no bash on this machine")
def test_each_engine_core_engines_local_names_is_installed_again_into_cores_environment(tmp_path):
    assert os.access(SCRIPTS / "engines-local.sh", os.X_OK), "chmod +x scripts/engines-local.sh"
    subprocess.run(["bash", "-n", str(SCRIPTS / "engines-local.sh")], check=True)
    stub, asked = _uv_stand_in(tmp_path)
    engine = tmp_path / "an-engine"
    engine.mkdir()
    listed = tmp_path / "engines.local"
    listed.write_text(f"# the engines this machine keeps beside the lock\n\n   {engine}   \n  # another note\ntests/fixtures\n")
    done = _engines_local(listed, stub)
    assert done.returncode == 0, done.stdout + done.stderr
    install = "pip install --python .venv/bin/python -c <c> -e"
    assert _installs(asked) == [f"{CORE} {install} {engine}", f"{CORE} {install} {CORE}/tests/fixtures"], \
        "each install held to the lock's versions"
    assert done.stdout.splitlines() == [f"installed {engine} into core's environment, beside core/uv.lock",
                                        "installed tests/fixtures into core's environment, beside core/uv.lock"]


@pytest.mark.skipif(shutil.which("bash") is None, reason="no bash on this machine")
def test_a_line_naming_no_directory_or_one_that_fails_to_install_is_said_and_the_rest_installed(tmp_path):
    stub, asked = _uv_stand_in(tmp_path)
    fails, engine = tmp_path / "fails", tmp_path / "an-engine"
    fails.mkdir()
    engine.mkdir()
    listed = tmp_path / "engines.local"
    listed.write_text(f"{tmp_path}/nowhere\n{fails}\n{engine}")
    done = _engines_local(listed, stub)
    assert done.returncode == 1
    assert done.stdout.splitlines() == [
        f"✗ core/engines.local names {tmp_path}/nowhere, and no directory is there",
        f"✗ {fails} did not install (uv pip install -e, each package core/uv.lock pins held at its locked version); "
        "the lines above say why",
        f"installed {engine} into core's environment, beside core/uv.lock"]
    assert len(_installs(asked)) == 2, "the missing directory asks uv nothing"
    assert _engines_local(tmp_path / "absent.local", stub).stdout.strip() == (
        "no core/engines.local, so no engine is installed beside core/uv.lock")


@pytest.mark.skipif(shutil.which("bash") is None, reason="no bash on this machine")
def test_a_lock_that_cannot_be_read_as_the_constraints_installs_nothing_and_says_so(tmp_path):
    stub, asked = _uv_stand_in(tmp_path, export_fails=True)
    engine = tmp_path / "an-engine"
    engine.mkdir()
    listed = tmp_path / "engines.local"
    listed.write_text(f"{engine}\n")
    done = _engines_local(listed, stub)
    assert done.returncode == 1
    assert done.stdout.strip() == ("✗ core/uv.lock could not be read as the installs' constraints (uv export --frozen), "
                                   "so no engine was installed")
    assert asked.read_text().splitlines() == [f"{CORE} {EXPORT}"], "nothing installed unheld"


def test_a_session_and_a_deploy_install_the_engines_again_after_their_sync_and_git_ignores_the_list():
    for script, sync, call in (
            (SCRIPTS / "session-start.sh", "(cd core && uv sync --all-extras)", "\nbash scripts/engines-local.sh"),
            (HOST_DIR / "deploy.sh", "(cd core && uv sync --frozen --all-extras)", '\n"$REPO/scripts/engines-local.sh"')):
        text = script.read_text(encoding="utf-8")
        assert text.count(call) == 1 and text.index(sync) < text.index(call), script.name
    ignored = subprocess.run(["git", "check-ignore", "-q", "core/engines.local"], cwd=SCRIPTS.parent)
    assert ignored.returncode == 0, "core/engines.local is ignored by git"
