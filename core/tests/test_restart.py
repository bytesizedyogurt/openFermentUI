"""A restart keeps everything (execution prompt §10, stage 2 gate).

A real service process, on a database of its own whose rows are committed,
makes a project and keeps rows of several stores through the API; it stops,
a second process starts on the same database, and every row reads back as it
was. Nothing here is rolled back: the database is made for this test and
dropped after it.
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx

from openferment_core.db import migrate

CORE = Path(__file__).parent.parent
TRAIN = {"train": {"id": "tr-restart", "units": []}, "savedAt": "2026-10-30T07:00:00Z", "by": "Ada Moreno"}
LEAD = {"id": "p-ada", "name": "Ada Moreno", "role": "lead", "joinedAt": "2026-10-01", "addedAt": "2026-10-01T00:00:00Z"}
READS = ("/api/projects", "/api/state", "/api/guild", "/api/audit", "/api/proposals")


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _serve(address: str, port: int, data: Path) -> subprocess.Popen:
    env = {**os.environ, "OPENFERMENT_DATABASE_URL": address, "OPENFERMENT_DATA_DIR": str(data),
           "OPENFERMENT_DIST_DIR": str(data / "no-build")}
    env.pop("OPENFERMENT_PROJECT", None)
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "openferment_core.api:app", "--host", "127.0.0.1", "--port", str(port),
         "--log-level", "warning"],
        cwd=CORE, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise AssertionError(f"the service exited: {process.stdout.read() if process.stdout else ''}")
        try:
            if httpx.get(f"http://127.0.0.1:{port}/api/health", timeout=1).status_code == 200:
                return process
        except httpx.HTTPError:
            pass
        time.sleep(0.2)
    process.kill()
    raise AssertionError("the service did not answer within 90 s")


def _stop(process: subprocess.Popen) -> None:
    process.terminate()
    try:
        process.wait(15)
    except subprocess.TimeoutExpired:
        process.kill()


def test_what_a_service_kept_before_it_stopped_it_serves_after_it_starts_again(test_database, tmp_path):
    test_database.open()
    name = f"{test_database.name}_restart"
    url = migrate.create(name, test_database.server)
    try:
        migrate.upgrade(url)
        address = url.render_as_string(hide_password=False)
        port = _free_port()
        base = f"http://127.0.0.1:{port}"

        first = _serve(address, port, tmp_path)
        try:
            project = httpx.post(f"{base}/api/projects", json={"name": "Restart", "by": "Ada Moreno"}).json()
            named = {"X-OpenFerment-Project": project["id"]}
            assert httpx.put(f"{base}/api/state/trains/tr-restart", json={"by": "Ada Moreno", "value": TRAIN},
                             headers=named).status_code == 200
            assert httpx.put(f"{base}/api/state/runbookLocks/rb-1",
                             json={"by": "Ada Moreno", "value": {"lockedAt": "2026-10-30T07:00:00Z", "lockHash": "abc"}},
                             headers=named).status_code == 200
            assert httpx.post(f"{base}/api/guild/people", json=LEAD, headers=named).status_code == 200
            before = {path: httpx.get(base + path, headers=named).json() for path in READS}
        finally:
            _stop(first)

        second = _serve(address, port, tmp_path)
        try:
            after = {path: httpx.get(base + path, headers=named).json() for path in READS}
        finally:
            _stop(second)

        assert after == before
        assert after["/api/state"]["trains"] == {"tr-restart": TRAIN}
        assert after["/api/state"]["runbookLocks"] == {"rb-1": {"lockedAt": "2026-10-30T07:00:00Z", "lockHash": "abc"}}
        assert [p["id"] for p in after["/api/guild"]["people"]] == ["p-ada"]
        assert [p["id"] for p in after["/api/projects"]] == [project["id"]]
        assert [a["action"] for a in after["/api/audit"]] == ["create_project", "keep_trains", "lock"]
    finally:
        migrate.drop(name, test_database.server)
