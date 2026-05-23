from __future__ import annotations

import asyncio

from beta_engine.main import create_app


def test_create_app_does_not_build_runtime_during_construction(monkeypatch) -> None:
    build_calls: list[str | None] = []

    def fake_build_runtime(*, database_url: str | None = None):
        build_calls.append(database_url)
        raise AssertionError("build_runtime must not be called during create_app construction")

    monkeypatch.setattr("beta_engine.main.build_runtime", fake_build_runtime)

    app = create_app(database_url="sqlite:///construction-test.db")

    assert build_calls == []
    assert not hasattr(app.state, "runtime")


def test_create_app_builds_runtime_on_startup_with_passed_database_url(monkeypatch) -> None:
    build_calls: list[str | None] = []
    sentinel_runtime = object()

    def fake_build_runtime(*, database_url: str | None = None):
        build_calls.append(database_url)
        return sentinel_runtime

    monkeypatch.setattr("beta_engine.main.build_runtime", fake_build_runtime)

    app = create_app(database_url="sqlite:///custom.db")

    assert not hasattr(app.state, "runtime")

    async def _run_lifespan_startup() -> None:
        async with app.router.lifespan_context(app):
            assert app.state.runtime is sentinel_runtime

    asyncio.run(_run_lifespan_startup())

    assert build_calls == ["sqlite:///custom.db"]
