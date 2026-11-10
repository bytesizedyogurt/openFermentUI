"""Print collectors.refused_class for a set of addresses on this Python (run it on 3.12 and 3.13, diff)."""
import ipaddress, sys
from openferment_core.literature.collectors import refused_class
ADDRS = ["192.0.0.8", "192.0.0.9", "192.0.0.10", "192.0.0.170", "100.64.0.1", "2002::1", "2002:7f00:1::",
         "64:ff9b:1::7f00:1", "64:ff9b::7f00:1", "2001::1", "2001:1::1", "2001:2::1", "2001:3::1", "2001:4:112::1",
         "2001:20::1", "2001:db8::1", "::ffff:127.0.0.1", "::ffff:10.0.0.1", "fec0::1", "fc00::1", "198.18.0.1",
         "240.0.0.1", "255.255.255.255", "0.0.0.0", "100::1", "::", "::1", "8.8.8.8", "2606:4700::1111",
         "192.88.99.1", "198.51.100.1", "203.0.113.1", "192.0.2.1", "169.254.1.1", "224.0.0.1", "2001:10::1"]
print(sys.version.split()[0])
for a in ADDRS:
    print(f"{a:22} {refused_class(ipaddress.ip_address(a))}")
