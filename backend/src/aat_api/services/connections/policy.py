"""Connection probe results and shared exact host/DNS policy."""
from dataclasses import dataclass,field
from typing import Literal
from aat_metadata.network import ConnectionPolicyError,validate_host,resolve_host


@dataclass(frozen=True)
class ProbeResult:
    status: Literal['SUCCESS', 'FAILED']
    latency_ms: int
    code: str | None = None
    server_fingerprint: str | None = None
    capabilities: dict[str, object] = field(default_factory=dict)
