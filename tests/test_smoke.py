from __future__ import annotations

from beta_engine.api.routers.health import health


def test_health_endpoint() -> None:
    assert health().model_dump() == {"status": "ok"}
