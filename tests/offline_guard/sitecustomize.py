"""Process-wide socket guard for canonical offline Python subprocesses."""

from __future__ import annotations

import ipaddress
import os
import socket


class OfflineNetworkError(OSError):
    pass


def _is_local_host(host: object) -> bool:
    if host is None:
        return True
    if isinstance(host, bytes):
        host = host.decode("ascii", errors="ignore")
    value = str(host).strip().lower().strip("[]")
    if "%" in value:
        value = value.split("%", 1)[0]
    if value == "localhost" or value.endswith(".localhost"):
        return True
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False
    return address.is_loopback or address.is_unspecified


def _require_local(host: object) -> None:
    if not _is_local_host(host):
        raise OfflineNetworkError(
            f"RAPP1 offline gate blocks external network host {host!r}"
        )


_original_getaddrinfo = socket.getaddrinfo
_original_getfqdn = socket.getfqdn
_original_gethostbyaddr = socket.gethostbyaddr
_original_gethostbyname = socket.gethostbyname
_original_gethostbyname_ex = socket.gethostbyname_ex
_original_getnameinfo = socket.getnameinfo
_original_create_connection = socket.create_connection
_original_socket = socket.socket


def _guarded_getaddrinfo(host, *args, **kwargs):
    _require_local(host)
    return _original_getaddrinfo(host, *args, **kwargs)


def _guarded_getfqdn(host=""):
    _require_local(host)
    return _original_getfqdn(host)


def _guarded_gethostbyaddr(host):
    _require_local(host)
    return _original_gethostbyaddr(host)


def _guarded_gethostbyname(host):
    _require_local(host)
    return _original_gethostbyname(host)


def _guarded_gethostbyname_ex(host):
    _require_local(host)
    return _original_gethostbyname_ex(host)


def _guarded_getnameinfo(sockaddr, *args, **kwargs):
    _require_local(sockaddr[0])
    return _original_getnameinfo(sockaddr, *args, **kwargs)


class _GuardedSocket(_original_socket):
    def bind(self, address):
        if self.family == socket.AF_INET:
            host, port = address[:2]
            if str(host).strip() in {"", "0.0.0.0"}:
                address = ("127.0.0.1", port, *address[2:])
            else:
                _require_local(host)
        elif self.family == socket.AF_INET6:
            host, port = address[:2]
            if str(host).strip().lower().strip("[]") in {"", "::"}:
                address = ("::1", port, *address[2:])
            else:
                _require_local(host)
        return super().bind(address)

    def connect(self, address):
        if self.family in {socket.AF_INET, socket.AF_INET6}:
            _require_local(address[0])
        return super().connect(address)

    def connect_ex(self, address):
        if self.family in {socket.AF_INET, socket.AF_INET6}:
            _require_local(address[0])
        return super().connect_ex(address)

    def sendto(self, data, *args):
        address = args[-1]
        if self.family in {socket.AF_INET, socket.AF_INET6}:
            _require_local(address[0])
        return super().sendto(data, *args)

    if hasattr(_original_socket, "sendmsg"):
        def sendmsg(self, buffers, ancdata=(), flags=0, address=None):
            if (
                address is not None
                and self.family in {socket.AF_INET, socket.AF_INET6}
            ):
                _require_local(address[0])
            if address is None:
                return super().sendmsg(buffers, ancdata, flags)
            return super().sendmsg(buffers, ancdata, flags, address)


def _guarded_create_connection(address, *args, **kwargs):
    _require_local(address[0])
    return _original_create_connection(address, *args, **kwargs)


socket.getaddrinfo = _guarded_getaddrinfo
socket.getfqdn = _guarded_getfqdn
socket.gethostbyaddr = _guarded_gethostbyaddr
socket.gethostbyname = _guarded_gethostbyname
socket.gethostbyname_ex = _guarded_gethostbyname_ex
socket.getnameinfo = _guarded_getnameinfo
socket.socket = _GuardedSocket
socket.SocketType = _GuardedSocket
socket.create_connection = _guarded_create_connection
os.environ["RAPP1_PYTHON_NETWORK_GUARD"] = "1"
