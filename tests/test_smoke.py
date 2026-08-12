from __future__ import annotations

import pytest

from beta_engine.api.routers.health import health


@pytest.mark.smoke
def test_health_endpoint() -> None:
    assert health().model_dump() == {"status": "ok"}
