from __future__ import annotations

from types import SimpleNamespace

import pytest

from beta_engine.application.pre_alpha_fax_acceptance_profile import (
    FAX_ACCEPTANCE_MIN_INITIAL_PLAYERS,
    FAX_ACCEPTANCE_WORLD_TOUR_EDITIONS,
    PreAlphaFaxAcceptanceProfileService,
)


class _Session:
    def __init__(self, run, branch):
        self.run = run
        self.branch = branch

    def get(self, model, key):
        name = model.__name__
        if name == "RunContainerModel":
            return self.run if key == self.run.run_id else None
        if name == "RunBranchModel":
            return self.branch if key == self.branch.branch_id else None
        raise AssertionError(name)


class _SessionContext:
    def __init__(self, session):
        self.session = session

    def __enter__(self):
        return self.session

    def __exit__(self, exc_type, exc, tb):
        return None


def _service():
    run = SimpleNamespace(
        run_id="run",
        read_only=False,
        timeline_start_season=2000,
        timeline_end_season=2049,
    )
    branch = SimpleNamespace(branch_id="branch", run_id="run", status="active")
    return PreAlphaFaxAcceptanceProfileService(
        lambda: _SessionContext(_Session(run, branch))
    )


def _calendar(world_count: int, lower_count: int = 0):
    events = [
        SimpleNamespace(tour_level="WORLD_TOUR")
        for _ in range(world_count)
    ] + [
        SimpleNamespace(tour_level="ELITE_TOUR")
        for _ in range(lower_count)
    ]
    return SimpleNamespace(
        run_package_state_fingerprint="a" * 64,
        content_fingerprint="b" * 64,
        calendar=SimpleNamespace(events=events),
    )


def test_fax_acceptance_profile_passes_decided_master_v72_scale(monkeypatch) -> None:
    import beta_engine.application.pre_alpha_fax_acceptance_profile as module

    world = SimpleNamespace(
        players=tuple(object() for _ in range(FAX_ACCEPTANCE_MIN_INITIAL_PLAYERS)),
        fingerprint="c" * 64,
        world_package_id="official_fax_world",
    )
    monkeypatch.setattr(module, "get_initial_world", lambda *args, **kwargs: world)
    monkeypatch.setattr(module, "get_run_package_state", lambda *args, **kwargs: object())
    monkeypatch.setattr(
        module.CalendarPackageRunAdapter,
        "project_calendar",
        staticmethod(
            lambda *args, **kwargs: _calendar(
                FAX_ACCEPTANCE_WORLD_TOUR_EDITIONS,
                lower_count=12,
            )
        ),
    )

    profile = _service().inspect(run_id="run", branch_id="branch")

    assert profile.ready_for_long_acceptance is True
    assert profile.timeline_season_count == 50
    assert profile.initial_player_count == 1000
    assert profile.world_tour_edition_count == 80
    assert profile.lower_tour_edition_count == 12
    assert [
        issue.code for issue in profile.issues if issue.severity == "error"
    ] == []
    assert len(profile.profile_fingerprint) == 64


def test_fax_acceptance_profile_reports_all_scale_blockers(monkeypatch) -> None:
    import beta_engine.application.pre_alpha_fax_acceptance_profile as module

    world = SimpleNamespace(
        players=tuple(object() for _ in range(999)),
        fingerprint="d" * 64,
        world_package_id="official_fax_world",
    )
    monkeypatch.setattr(module, "get_initial_world", lambda *args, **kwargs: world)
    monkeypatch.setattr(module, "get_run_package_state", lambda *args, **kwargs: object())
    monkeypatch.setattr(
        module.CalendarPackageRunAdapter,
        "project_calendar",
        staticmethod(lambda *args, **kwargs: _calendar(79)),
    )

    profile = _service().inspect(run_id="run", branch_id="branch")

    assert profile.ready_for_long_acceptance is False
    assert {
        issue.code for issue in profile.issues if issue.severity == "error"
    } == {
        "FAX_ACCEPTANCE_INITIAL_PLAYER_COUNT_LOW",
        "FAX_ACCEPTANCE_WORLD_TOUR_EDITION_COUNT",
    }


def test_fax_acceptance_profile_requires_run_owned_calendar(monkeypatch) -> None:
    import beta_engine.application.pre_alpha_fax_acceptance_profile as module

    monkeypatch.setattr(module, "get_initial_world", lambda *args, **kwargs: None)
    monkeypatch.setattr(module, "get_run_package_state", lambda *args, **kwargs: None)

    profile = _service().inspect(run_id="run", branch_id="branch")

    assert profile.ready_for_long_acceptance is False
    assert {
        issue.code for issue in profile.issues if issue.severity == "error"
    } == {
        "FAX_ACCEPTANCE_INITIAL_WORLD_MISSING",
        "FAX_ACCEPTANCE_CALENDAR_PACKAGE_MISSING",
    }
