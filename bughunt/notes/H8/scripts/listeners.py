"""Listen on loopback ports and log every connection that reaches them.

Usage: python listeners.py LOG PORT [PORT ...]
Each port is bound on 127.0.0.1 (and on ::1 when the machine has it). A connection is
logged with the first bytes it sends, then answered with a plain HTTP 200 carrying a tiny
SFF-shaped JSON (so a fetch that got through would have something to keep).
"""
from __future__ import annotations

import socket
import sys
import threading
import time

log_path = sys.argv[1]
ports = [int(p) for p in sys.argv[2:]]
lock = threading.Lock()
BODY = b'{"units": [], "streams": [], "metadata": {"process_title": "reached a loopback listener"}}'
REPLY = (b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: %d\r\nConnection: close\r\n\r\n"
         % len(BODY)) + BODY


def log(line: str) -> None:
    with lock, open(log_path, "a") as f:
        f.write(f"{time.strftime('%H:%M:%S')} {line}\n")


def serve(sock: socket.socket, where: str) -> None:
    while True:
        conn, peer = sock.accept()
        conn.settimeout(3)
        try:
            first = conn.recv(400)
        except OSError:
            first = b""
        log(f"CONNECTION on {where} from {peer}: {first[:200]!r}")
        try:
            conn.sendall(REPLY)
        except OSError:
            pass
        conn.close()


for port in ports:
    for fam, host in ((socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")):
        try:
            s = socket.socket(fam, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, port))
            s.listen(16)
        except OSError as e:
            log(f"could not bind {host}:{port}: {e}")
            continue
        log(f"listening on {host}:{port}")
        threading.Thread(target=serve, args=(s, f"{host}:{port}"), daemon=True).start()

while True:
    time.sleep(3600)
