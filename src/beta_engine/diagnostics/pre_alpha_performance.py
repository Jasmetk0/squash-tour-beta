"""Non-authoritative runtime profiling helpers for pre-alpha release gates."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import platform
import sys
from typing import Iterable


PROFILE_SCHEMA = "pre_alpha_performance_profile.v1"


@dataclass(frozen=True)
class PreAlphaPerformanceProfile:
    schema: str
    label: str
    created_at_utc: str
    python_version: str
    platform: str
    pytest_exit_code: int
    elapsed_seconds: float
    python_heap_current_bytes: int
    python_heap_peak_bytes: int
    nodeids: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return self.pytest_exit_code == 0

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["passed"] = self.passed
        return payload


def build_profile(
    *,
    label: str,
    pytest_exit_code: int,
    elapsed_seconds: float,
    python_heap_current_bytes: int,
    python_heap_peak_bytes: int,
    nodeids: Iterable[str],
) -> PreAlphaPerformanceProfile:
    """Build one reproducible measurement record without defining a pass/fail target."""

    if not label.strip():
        raise ValueError("profile label must be non-empty")
    if elapsed_seconds < 0:
        raise ValueError("elapsed_seconds must be non-negative")
    if python_heap_current_bytes < 0 or python_heap_peak_bytes < 0:
        raise ValueError("heap byte measurements must be non-negative")
    if python_heap_current_bytes > python_heap_peak_bytes:
        raise ValueError("current heap bytes cannot exceed peak heap bytes")

    normalized_nodeids = tuple(nodeid.strip() for nodeid in nodeids if nodeid.strip())
    if not normalized_nodeids:
        raise ValueError("at least one pytest nodeid is required")

    return PreAlphaPerformanceProfile(
        schema=PROFILE_SCHEMA,
        label=label.strip(),
        created_at_utc=datetime.now(timezone.utc).isoformat(),
        python_version=sys.version.split()[0],
        platform=platform.platform(),
        pytest_exit_code=int(pytest_exit_code),
        elapsed_seconds=round(float(elapsed_seconds), 6),
        python_heap_current_bytes=int(python_heap_current_bytes),
        python_heap_peak_bytes=int(python_heap_peak_bytes),
        nodeids=normalized_nodeids,
    )
