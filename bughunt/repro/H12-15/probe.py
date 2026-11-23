"""H12-15 probe: what refused_class answers for IPv4-mapped IPv6 addresses on
the Python running it, one line an address, from the openferment_core on
PYTHONPATH (a worktree of 2047f5a, kept or with M57 applied).

Usage: python probe.py OUT_FILE
The first line says the Python, the module's file and, for each IPv6Address
property refused_class reads, whether the standard library defers it to
ipv4_mapped on this Python."""
from __future__ import annotations

import inspect
import ipaddress
import random
import sys

from openferment_core.literature import collectors

out = sys.argv[1]
props = [name for name, _ in collectors._REFUSED] + ["is_global"]
defers = {p: "ipv4_mapped" in inspect.getsource(getattr(ipaddress.IPv6Address, p).fget) for p in props}

# Every /16's first and last IPv4 address, and 100,000 more from a fixed seed,
# each written as its IPv4-mapped IPv6 address.
ints = set()
for hi in range(65536):
    ints.add(hi << 16)
    ints.add((hi << 16) | 0xFFFF)
rng = random.Random(0)
while len(ints) < 131072 + 100000:
    ints.add(rng.getrandbits(32))

with open(out, "w", encoding="utf-8") as f:
    for n in sorted(ints):
        mapped = ipaddress.IPv6Address((0xFFFF << 32) | n)
        f.write(f"::ffff:{ipaddress.IPv4Address(n)}\t{collectors.refused_class(mapped)}\n")

print(f"python {sys.version.split()[0]}; module {collectors.__file__}; {len(ints)} mapped addresses; "
      "IPv6Address property defers to ipv4_mapped: " + ", ".join(f"{p}={'yes' if d else 'no'}"
                                                              for p, d in defers.items()))
