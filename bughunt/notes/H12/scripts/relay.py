"""A byte relay, so tests in a network namespace of their own reach the PostgreSQL server on the host's loopback
and nothing else: outside, `relay.py out SOCKET` listens on a unix socket and forwards to 127.0.0.1:5432; inside,
`relay.py in SOCKET` listens on 127.0.0.1:5432 and forwards to that socket."""
import asyncio
import os
import sys


async def pipe(r: asyncio.StreamReader, w: asyncio.StreamWriter) -> None:
    try:
        while data := await r.read(65536):
            w.write(data)
            await w.drain()
    except (ConnectionError, OSError):
        pass
    finally:
        try:
            w.close()
        except Exception:
            pass


async def main(mode: str, path: str) -> None:
    async def serve(r, w):
        if mode == "out":
            r2, w2 = await asyncio.open_connection("127.0.0.1", 5432)
        else:
            r2, w2 = await asyncio.open_unix_connection(path)
        await asyncio.gather(pipe(r, w2), pipe(r2, w))

    if mode == "out":
        server = await asyncio.start_unix_server(serve, path)
    else:
        server = await asyncio.start_server(serve, "127.0.0.1", 5432)
    async with server:
        await server.serve_forever()


# A unix socket's path is held to 108 bytes: bind and connect by its name, from its directory.
os.chdir(os.path.dirname(os.path.abspath(sys.argv[2])))
asyncio.run(main(sys.argv[1], os.path.basename(sys.argv[2])))
