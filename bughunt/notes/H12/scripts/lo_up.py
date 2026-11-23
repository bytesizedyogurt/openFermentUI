"""Bring the loopback interface up in a fresh network namespace (no `ip` on this machine)."""
import fcntl
import socket
import struct

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
flags = struct.unpack("16sh", fcntl.ioctl(s, 0x8913, struct.pack("16sh", b"lo", 0)))[1]
fcntl.ioctl(s, 0x8914, struct.pack("16sh", b"lo", flags | 0x1))
