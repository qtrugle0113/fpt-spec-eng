"""Exact host allowlist and a single bounded resolution before numeric connection."""
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import dataclass, field
import ipaddress
import os
import re
import socket
from typing import Literal

_resolver = ThreadPoolExecutor(max_workers=4, thread_name_prefix='aat-db-dns')


class ConnectionPolicyError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__('Database host is unavailable or not allowed.')


@dataclass(frozen=True)
class ProbeResult:
    status: Literal['SUCCESS', 'FAILED']
    latency_ms: int
    code: str | None = None
    server_fingerprint: str | None = None
    capabilities: dict[str, object] = field(default_factory=dict)


def _safe_address(address: str) -> bool:
    ip = ipaddress.ip_address(address)
    if getattr(ip, 'ipv4_mapped', None) is not None:
        ip = ip.ipv4_mapped
    return not (ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_unspecified or ip.is_reserved)


def validate_host(host: str) -> str:
    if not isinstance(host, str):
        raise ConnectionPolicyError('HOST_NOT_ALLOWED')
    host = host.strip().lower()
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        if not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?', host) or '..' in host:
            raise ConnectionPolicyError('HOST_NOT_ALLOWED') from None
    else:
        if not _safe_address(str(address)):
            raise ConnectionPolicyError('HOST_NOT_ALLOWED')
    allowed = {name.strip().lower() for name in os.environ.get('AAT_DB_ALLOWED_HOSTS', 'postgres,mysql').split(',') if name.strip()}
    if host not in allowed:
        raise ConnectionPolicyError('HOST_NOT_ALLOWED')
    return host


def resolve_host(host: str, port: int) -> list[str]:
    host = validate_host(host)
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise ConnectionPolicyError('INVALID_PORT')
    future = _resolver.submit(socket.getaddrinfo, host, port, 0, socket.SOCK_STREAM)
    try:
        records = future.result(timeout=3)
    except FutureTimeout:
        future.cancel()
        raise ConnectionPolicyError('TIMEOUT') from None
    except OSError:
        raise ConnectionPolicyError('HOST_UNREACHABLE') from None
    addresses = list(dict.fromkeys(record[4][0] for record in records))
    if not addresses or any(not _safe_address(address) for address in addresses):
        raise ConnectionPolicyError('HOST_NOT_ALLOWED')
    return addresses
